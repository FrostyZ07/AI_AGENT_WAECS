"""Make the app look freshly installed (for a demo recording), and put your data back afterwards.

    uv run python scripts/demo_reset.py reset              # back up, revoke Google, empty the app's tables
    uv run python scripts/demo_reset.py restore <backup>   # put a backup back (replaces what is there now)

Uses the same agent-api/.env as the app, so no env changes. Settings are kept (they are your preferences).
Google Calendar events and the "EA Follow-ups" task list live in Google, not here, so they are not touched.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so `app` imports when run from agent-api/

from psycopg.types.json import Jsonb  # noqa: E402

from app import google_api, store  # noqa: E402

TABLES = ["requests", "approvals", "meeting_prep", "brief", "audit_log", "oauth_token"]
SERIALS = {"approvals": "id", "audit_log": "id"}
BACKUPS = Path(__file__).resolve().parent / "backups"


def backup() -> Path:
    BACKUPS.mkdir(exist_ok=True)
    path = BACKUPS / f"backup-{datetime.now():%Y%m%d-%H%M%S}.json"
    data = {t: store._q(f"SELECT * FROM {t}") for t in TABLES}
    path.write_text(json.dumps(data, default=str, indent=1), encoding="utf-8")
    print(f"Backup: {path}  ({', '.join(f'{t}={len(r)}' for t, r in data.items())})")
    return path


def wipe() -> None:
    store._q(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY", write=True)


def reset() -> None:
    backup()
    try:
        google_api.disconnect()  # revoke at Google too, so the recording shows the real consent screen
    except Exception as e:
        print(f"Google revoke skipped: {e}")
    wipe()
    print("Done. The app is now in its first-run state (settings kept).")


def restore(path: str) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    backup()  # whatever the demo created, in case you want it
    wipe()
    for table, rows in data.items():
        for row in rows:
            cols = list(row)
            vals = [Jsonb(v) if isinstance(v, (dict, list)) else v for v in row.values()]
            store._q(f"INSERT INTO {table} ({', '.join(f'"{c}"' for c in cols)}) VALUES ({', '.join(['%s'] * len(cols))})",
                     tuple(vals), write=True)
        if table in SERIALS and rows:
            col = SERIALS[table]
            store._q(f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), (SELECT max({col}) FROM {table}))")
        print(f"{table}: {len(rows)} rows restored")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "reset":
        if input("This empties requests, approvals, brief, prep, audit log and the Google token (a backup is saved first). Type yes: ") == "yes":
            reset()
    elif len(sys.argv) == 3 and sys.argv[1] == "restore":
        restore(sys.argv[2])
    else:
        print(__doc__)
