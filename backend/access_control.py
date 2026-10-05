"""
Sisiwenyewe CBRN — access control for restricted intelligence.

Public users can ask general CBRN questions. Restricted material
(internal documents, live sensor data, internal profiles) is only
returned to authorised personnel who sign in with their service number
and PIN.

Everything is enforced here on the server. The web page only shows the
sign-in form; it never decides what a user may see.

Files (all git-ignored, live on the server only):
  auth/users.json     authorised personnel + hashed PINs
  logs/access.log     audit trail (JSON lines)
Config:
  access_policy.json  which knowledge-base files are PUBLIC (everything else is restricted)
  .env AUTH_SECRET    long random string used to sign session tokens (required)
"""

import fnmatch
import json
import os
import re
import secrets
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from flask import Blueprint, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

try:
    import fcntl  # Linux/macOS: lock users.json across gunicorn workers
except ImportError:  # pragma: no cover
    fcntl = None

BASE_DIR = Path(__file__).parent
AUTH_DIR = BASE_DIR / "auth"
USERS_PATH = Path(os.getenv("AUTH_USERS_PATH", AUTH_DIR / "users.json"))
LOG_DIR = BASE_DIR / "logs"
ACCESS_LOG = LOG_DIR / "access.log"
POLICY_PATH = BASE_DIR / "access_policy.json"

TOKEN_HOURS = float(os.getenv("AUTH_TOKEN_HOURS", "8"))
PIN_CHANGE_MINUTES = 15
MAX_FAILED = int(os.getenv("AUTH_MAX_FAILED", "5"))
LOCK_MINUTES = int(os.getenv("AUTH_LOCK_MINUTES", "15"))
PIN_RE = re.compile(r"^\d{6,12}$")

AUTH_REQUIRED_MESSAGE = (
    "This information is restricted to authorised Sisiwenyewe personnel. "
    "Sign in with your service number and PIN to continue."
)
AUTH_EXPIRED_MESSAGE = "Your session has ended. Sign in again to view restricted information."


def _secret():
    s = os.getenv("AUTH_SECRET", "")
    if len(s) < 32:
        raise RuntimeError(
            "AUTH_SECRET is missing or too short. Add a random value of at least 32 "
            "characters to backend/.env, e.g. python3 -c \"import secrets;print(secrets.token_urlsafe(48))\""
        )
    return s


def _serializer():
    return URLSafeTimedSerializer(_secret(), salt="sisiwenyewe-auth-v1")


# ---------------------------------------------------------------- policy

_policy_cache = {"mtime": None, "public": [], "restrict_sensor": True, "restrict_profile": True}


def _policy():
    try:
        mtime = POLICY_PATH.stat().st_mtime
    except FileNotFoundError:
        return _policy_cache
    if mtime != _policy_cache["mtime"]:
        with open(POLICY_PATH, "r", encoding="utf-8") as f:
            p = json.load(f)
        _policy_cache.update(
            mtime=mtime,
            public=[x.lower() for x in p.get("public_files", [])],
            restrict_sensor=bool(p.get("restrict_live_sensor_data", True)),
            restrict_profile=bool(p.get("restrict_internal_profiles", True)),
        )
    return _policy_cache


def is_public_file(file_name: str) -> bool:
    """Default-deny: a knowledge-base file is restricted unless it matches the public list."""
    name = (file_name or "").lower()
    return any(fnmatch.fnmatch(name, pat) for pat in _policy()["public"])


def sensor_is_restricted() -> bool:
    return _policy()["restrict_sensor"]


def profile_is_restricted() -> bool:
    return _policy()["restrict_profile"]


# ---------------------------------------------------------------- users store

def normalise_sn(sn: str) -> str:
    return re.sub(r"\s+", "", (sn or "")).upper()


@contextmanager
def _locked_users(write=False):
    AUTH_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = USERS_PATH.with_suffix(".lock")
    with open(lock_path, "a+") as lf:
        if fcntl:
            fcntl.flock(lf, fcntl.LOCK_EX if write else fcntl.LOCK_SH)
        try:
            users = {}
            if USERS_PATH.exists():
                with open(USERS_PATH, "r", encoding="utf-8") as f:
                    users = json.load(f)
            box = {"users": users}
            yield box
            if write:
                fd, tmp = tempfile.mkstemp(dir=str(USERS_PATH.parent), prefix=".users-")
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(box["users"], f, indent=2, ensure_ascii=False)
                os.chmod(tmp, 0o600)
                os.replace(tmp, USERS_PATH)
        finally:
            if fcntl:
                fcntl.flock(lf, fcntl.LOCK_UN)


def load_users():
    with _locked_users() as box:
        return box["users"]


def update_users(fn):
    with _locked_users(write=True) as box:
        return fn(box["users"])


def new_temp_pin() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(6))


def hash_pin(pin: str) -> str:
    return generate_password_hash(pin, method="pbkdf2:sha256:600000")


def public_user(sn, u):
    return {"service_no": sn, "rank": u.get("rank", ""), "name": u.get("name", "")}


# ---------------------------------------------------------------- audit log

def audit(event, sn=None, **extra):
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        rec = {
            "t": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "event": event,
            "sn": sn,
            "ip": request.headers.get("X-Forwarded-For", request.remote_addr) if request else None,
        }
        rec.update(extra)
        with open(ACCESS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception as e:  # never break a request because logging failed
        print(f"Audit log error: {e}")


# ---------------------------------------------------------------- tokens

def _issue(sn, u, pin_change=False):
    return _serializer().dumps({"sn": sn, "v": u.get("token_version", 1), "pc": pin_change})


def _read_token(max_age):
    h = request.headers.get("Authorization", "")
    if not h.lower().startswith("bearer "):
        return None, None
    try:
        data = _serializer().loads(h[7:].strip(), max_age=max_age)
    except SignatureExpired:
        return None, "expired"
    except BadSignature:
        return None, "invalid"
    return data, None


def current_user():
    """Returns (user_dict or None, problem or None). problem is 'expired'/'invalid' when a bad token was sent."""
    data, problem = _read_token(int(TOKEN_HOURS * 3600))
    if not data:
        return None, problem
    if data.get("pc"):
        return None, "pin_change_pending"
    sn = data.get("sn")
    u = load_users().get(sn)
    if not u or not u.get("active") or u.get("token_version", 1) != data.get("v"):
        return None, "expired"
    out = public_user(sn, u)
    return out, None


def auth_required_response(problem=None):
    expired = problem in ("expired", "invalid")
    return jsonify({
        "answer": AUTH_EXPIRED_MESSAGE if expired else AUTH_REQUIRED_MESSAGE,
        "auth_required": True,
        "auth_expired": expired,
        "sources": [],
        "resources": [],
    })


# ---------------------------------------------------------------- routes

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _err(msg, code=400, **extra):
    body = {"ok": False, "error": msg}
    body.update(extra)
    return jsonify(body), code


@bp.route("/login", methods=["POST"])
def login():
    d = request.get_json(silent=True) or {}
    sn = normalise_sn(d.get("service_no"))
    pin = str(d.get("pin") or "").strip()
    if not sn or not pin:
        return _err("Enter your service number and PIN.")

    now = time.time()
    result = {}

    def attempt(users):
        u = users.get(sn)
        if not u:
            result["status"] = "bad"
            return
        if u.get("locked_until", 0) > now:
            result["status"] = "locked"
            result["mins"] = int((u["locked_until"] - now) // 60) + 1
            return
        if not u.get("active"):
            # check the PIN anyway so timing does not reveal account status
            check_password_hash(u.get("pin_hash", hash_pin("x")), pin)
            result["status"] = "inactive"
            return
        if check_password_hash(u.get("pin_hash", ""), pin):
            u["failed"] = 0
            u["locked_until"] = 0
            u["last_login"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            result["status"] = "ok"
            result["user"] = dict(u)
            return
        u["failed"] = u.get("failed", 0) + 1
        if u["failed"] >= MAX_FAILED:
            u["locked_until"] = now + LOCK_MINUTES * 60
            u["failed"] = 0
            result["status"] = "locked"
            result["mins"] = LOCK_MINUTES
        else:
            result["status"] = "bad"

    update_users(attempt)
    st = result.get("status")

    if st == "ok":
        u = result["user"]
        must_change = bool(u.get("must_change"))
        audit("login_ok", sn, must_change=must_change)
        return jsonify({
            "ok": True,
            "token": _issue(sn, u, pin_change=must_change),
            "must_change_pin": must_change,
            "user": public_user(sn, u),
            "expires_in": PIN_CHANGE_MINUTES * 60 if must_change else int(TOKEN_HOURS * 3600),
        })
    if st == "locked":
        audit("login_locked", sn)
        return _err(f"Too many attempts. Try again in {result.get('mins', LOCK_MINUTES)} minutes.", 429)
    if st == "inactive":
        audit("login_inactive", sn)
        return _err("This account is not active. Contact your administrator.", 403)
    audit("login_fail", sn if sn in load_users() else None, attempted=sn[:20])
    time.sleep(0.6)
    return _err("Service number or PIN is incorrect.", 401)


@bp.route("/change-pin", methods=["POST"])
def change_pin():
    d = request.get_json(silent=True) or {}
    data, problem = _read_token(int(TOKEN_HOURS * 3600))
    if not data:
        return _err("Sign in again to change your PIN.", 401)
    if data.get("pc") and _read_token(PIN_CHANGE_MINUTES * 60)[0] is None:
        return _err("That took too long. Sign in again with your one-time PIN.", 401)

    sn = data.get("sn")
    new_pin = str(d.get("new_pin") or "").strip()
    current_pin = str(d.get("current_pin") or "").strip()

    if not PIN_RE.match(new_pin):
        return _err("Your new PIN must be 6 to 12 digits.")
    if len(set(new_pin)) == 1 or new_pin in "01234567890123" or new_pin in "98765432109876":
        return _err("That PIN is too easy to guess. Avoid repeated or sequential digits.")

    result = {}

    def apply(users):
        u = users.get(sn)
        if not u or not u.get("active") or u.get("token_version", 1) != data.get("v"):
            result["err"] = ("Sign in again to change your PIN.", 401)
            return
        if not data.get("pc") and not check_password_hash(u.get("pin_hash", ""), current_pin):
            result["err"] = ("Your current PIN is incorrect.", 401)
            return
        if check_password_hash(u.get("pin_hash", ""), new_pin):
            result["err"] = ("Choose a PIN different from the one you were given.", 400)
            return
        u["pin_hash"] = hash_pin(new_pin)
        u["must_change"] = False
        u["token_version"] = u.get("token_version", 1) + 1  # ends any other sessions
        u["pin_changed"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        result["user"] = dict(u)

    update_users(apply)
    if "err" in result:
        return _err(*result["err"])
    u = result["user"]
    audit("pin_changed", sn)
    return jsonify({
        "ok": True,
        "token": _issue(sn, u),
        "user": public_user(sn, u),
        "expires_in": int(TOKEN_HOURS * 3600),
    })


@bp.route("/me", methods=["GET"])
def me():
    user, problem = current_user()
    if not user:
        return _err("Not signed in.", 401, reason=problem)
    return jsonify({"ok": True, "user": user})


@bp.route("/logout", methods=["POST"])
def logout():
    user, _ = current_user()
    if user:
        audit("logout", user["service_no"])
    return jsonify({"ok": True})
