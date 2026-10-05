#!/usr/bin/env python3
"""
Manage authorised personnel for Sisiwenyewe restricted access.
Run on the backend server, inside the backend folder.

  python3 manage_users.py import roster.xlsx        # add/update from the nominal roll
  python3 manage_users.py import roster.xlsx --allow PRESENT,COURSE
  python3 manage_users.py list
  python3 manage_users.py reset RO/14249            # issue a new one-time PIN
  python3 manage_users.py disable RO/14249          # block access immediately
  python3 manage_users.py enable RO/14249
  python3 manage_users.py add RO/12345 LT "JOHN DOE"

Roster format (first sheet): No | Service No | Rank | Name | Name | Status
(the same layout as the CBRNe HAZMAT nominal roll). A CSV with the same
columns also works.

New one-time PINs are written to auth/pins_<date>.csv (readable by the
server owner only). Hand each PIN to the soldier privately, then delete
the file. Soldiers must set their own PIN at first sign-in.
"""

import argparse
import csv
import os
import sys
import time

import access_control as ac

DEFAULT_ALLOW = "PRESENT,COURSE"


def read_roster(path):
    rows = []
    if path.lower().endswith(".csv"):
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = [tuple(r) for r in csv.reader(f)]
    else:
        import openpyxl  # pip install openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        rows = list(wb.worksheets[0].iter_rows(values_only=True))
    people = []
    for r in rows:
        cells = [("" if c is None else str(c).strip()) for c in r]
        if len(cells) < 3:
            continue
        sn = ac.normalise_sn(cells[1])
        if "/" not in sn or not any(ch.isdigit() for ch in sn):
            continue  # header / title rows
        name = " ".join(x for x in cells[3:5] if x).strip()
        people.append({
            "sn": sn,
            "rank": cells[2].upper(),
            "name": " ".join(name.split()).upper(),
            "status": (cells[5] if len(cells) > 5 else "").upper(),
        })
    return people


def write_pins(issued):
    if not issued:
        return None
    ac.AUTH_DIR.mkdir(parents=True, exist_ok=True)
    path = ac.AUTH_DIR / f"pins_{time.strftime('%Y%m%d-%H%M%S')}.csv"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["service_no", "rank", "name", "one_time_pin"])
        w.writerows(issued)
    return path


def cmd_import(args):
    allow = {s.strip().upper() for s in args.allow.split(",") if s.strip()}
    people = read_roster(args.file)
    if not people:
        sys.exit("No personnel rows found. Check the file layout.")
    issued, summary = [], {"added": 0, "updated": 0, "active": 0, "inactive": 0}

    def apply(users):
        for p in people:
            active = p["status"] in allow
            u = users.get(p["sn"])
            if u is None:
                pin = ac.new_temp_pin()
                users[p["sn"]] = {
                    "rank": p["rank"], "name": p["name"], "status": p["status"],
                    "active": active, "pin_hash": ac.hash_pin(pin), "must_change": True,
                    "token_version": 1, "failed": 0, "locked_until": 0,
                    "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                }
                summary["added"] += 1
                if active:
                    issued.append([p["sn"], p["rank"], p["name"], pin])
            else:
                if u.get("active") and not active:
                    u["token_version"] = u.get("token_version", 1) + 1  # end sessions
                u.update(rank=p["rank"], name=p["name"], status=p["status"], active=active)
                summary["updated"] += 1
            summary["active" if active else "inactive"] += 1

    ac.update_users(apply)
    path = write_pins(issued)
    print(f"Roster: {len(people)} people · added {summary['added']} · updated {summary['updated']}")
    print(f"Active (status in {', '.join(sorted(allow))}): {summary['active']} · blocked: {summary['inactive']}")
    if path:
        print(f"One-time PINs for {len(issued)} new active users written to: {path}")
        print("Give each PIN privately, then delete that file.")


def cmd_list(args):
    users = ac.load_users()
    now = time.time()
    print(f"{'SERVICE NO':<12} {'RANK':<7} {'NAME':<26} {'STATUS':<18} {'ACCESS':<8} {'PIN':<10} LAST LOGIN")
    for sn, u in sorted(users.items()):
        access = "LOCKED" if u.get("locked_until", 0) > now else ("ACTIVE" if u.get("active") else "BLOCKED")
        pin = "one-time" if u.get("must_change") else "set"
        print(f"{sn:<12} {u.get('rank',''):<7} {u.get('name','')[:26]:<26} {u.get('status','')[:18]:<18} {access:<8} {pin:<10} {u.get('last_login','-')}")


def _one(sn, fn):
    sn = ac.normalise_sn(sn)
    out = {}

    def apply(users):
        if sn not in users:
            out["missing"] = True
            return
        fn(users[sn], out)

    ac.update_users(apply)
    if out.get("missing"):
        sys.exit(f"{sn} is not in the user list.")
    return sn, out


def cmd_reset(args):
    def f(u, out):
        pin = ac.new_temp_pin()
        u.update(pin_hash=ac.hash_pin(pin), must_change=True, failed=0, locked_until=0,
                 token_version=u.get("token_version", 1) + 1)
        out["pin"] = pin
    sn, out = _one(args.sn, f)
    print(f"New one-time PIN for {sn}: {out['pin']}  (they must change it at sign-in)")


def cmd_disable(args):
    def f(u, out):
        u.update(active=False, token_version=u.get("token_version", 1) + 1)
    sn, _ = _one(args.sn, f)
    print(f"{sn} blocked. Any open session has ended.")


def cmd_enable(args):
    def f(u, out):
        u.update(active=True, failed=0, locked_until=0)
    sn, _ = _one(args.sn, f)
    print(f"{sn} enabled.")


def cmd_add(args):
    sn = ac.normalise_sn(args.sn)
    pin = ac.new_temp_pin()

    def apply(users):
        if sn in users:
            sys.exit(f"{sn} already exists. Use reset or enable.")
        users[sn] = {"rank": args.rank.upper(), "name": args.name.upper(), "status": "MANUAL",
                     "active": True, "pin_hash": ac.hash_pin(pin), "must_change": True,
                     "token_version": 1, "failed": 0, "locked_until": 0,
                     "created": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    ac.update_users(apply)
    print(f"Added {sn}. One-time PIN: {pin}")


def main():
    p = argparse.ArgumentParser(description="Manage Sisiwenyewe restricted-access users")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("import"); s.add_argument("file"); s.add_argument("--allow", default=DEFAULT_ALLOW); s.set_defaults(fn=cmd_import)
    s = sub.add_parser("list"); s.set_defaults(fn=cmd_list)
    for name, fn in (("reset", cmd_reset), ("disable", cmd_disable), ("enable", cmd_enable)):
        s = sub.add_parser(name); s.add_argument("sn"); s.set_defaults(fn=fn)
    s = sub.add_parser("add"); s.add_argument("sn"); s.add_argument("rank"); s.add_argument("name"); s.set_defaults(fn=cmd_add)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
