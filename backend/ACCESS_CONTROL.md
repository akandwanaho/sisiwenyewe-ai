# Restricted access — setup and administration

General CBRN questions stay public. Anything that draws on restricted material requires a
service number + PIN sign-in. Restricted material is:

- every knowledge-base file NOT listed in `access_policy.json` → `public_files`
  (default-deny: newly indexed documents are restricted until you list them as public)
- live sensor data and sensor analysis
- internal profiles

The check happens in the Flask backend (`/chat`), so calling the API directly does not
bypass it. The web page only shows the sign-in form.

## 1. Deploy (backend server)

```bash
cd backend
git pull                                    # or copy the new files in
echo "AUTH_SECRET=$(python3 -c 'import secrets;print(secrets.token_urlsafe(48))')" >> .env
pip install openpyxl                        # only needed for manage_users.py import
# restart the service (gunicorn / systemd) as you normally do
```

New files: `access_control.py`, `access_policy.json`, `manage_users.py`. Changed: `app.py`.
No new packages for the API itself (uses Flask's built-in itsdangerous and werkzeug).

## 2. Load the nominal roll

Copy the roster spreadsheet to the server (do NOT commit it), then:

```bash
python3 manage_users.py import "CBRNe HAZMAT roll.xlsx"     # PRESENT + COURSE get access
python3 manage_users.py list
```

One-time PINs are written to `auth/pins_<date>.csv` (owner-only permissions). Give each
soldier their PIN privately, then delete the file. On first sign-in each soldier must set
their own 6–12 digit PIN.

Re-running `import` with an updated roll updates rank/name/status, blocks anyone whose
status changes away from PRESENT/COURSE (their session ends at once), and issues PINs only
to new people. Use `--allow PRESENT,COURSE,STUDY LEAVE` to change who gets access.

## 3. Day-to-day

| Task | Command |
|---|---|
| Forgotten PIN / suspected leak | `python3 manage_users.py reset RO/14249` |
| Remove access immediately | `python3 manage_users.py disable RA/198426` |
| Restore access | `python3 manage_users.py enable RA/198426` |
| Add someone not on the roll | `python3 manage_users.py add RO/12345 LT "JOHN DOE"` |
| See who has access | `python3 manage_users.py list` |
| Audit trail | `tail -f logs/access.log` |

## Security behaviour

- PINs stored as salted PBKDF2-SHA256 hashes (600k rounds), never in plain text.
- 5 wrong PINs → account locked 15 minutes (`AUTH_MAX_FAILED`, `AUTH_LOCK_MINUTES`).
- Sessions last 8 hours (`AUTH_TOKEN_HOURS`); the page also signs out after 30 minutes idle
  and when the browser tab is closed.
- Restricted answers are never saved in the browser's conversation history.
- Disable, reset or PIN change ends that person's open sessions.
- Every sign-in, failure, lockout and restricted question is logged with service number and IP.
- Exported conversations containing restricted answers are marked RESTRICTED.

## Deciding what is public

Edit `access_policy.json`. Patterns are case-insensitive file names; `*` is a wildcard.
Changes apply without a restart. To restrict a file, remove it from `public_files`.
