"""Posts the next N pins from the queue (pins.py) to Pinterest, API v5.

Env: PINTEREST_APP_ID, PINTEREST_APP_SECRET, PINTEREST_REFRESH_TOKEN, PINTEREST_BOARD_ID
     PINS_PER_RUN (default 3)
Without credentials it exits 0, so the workflow can be enabled before the account exists.

    python tools/pinterest/post.py            # post
    python tools/pinterest/post.py --dry-run  # render + print only
"""
import argparse
import base64
import csv
import io
import os
import sys
import time
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(__file__))
import pins  # noqa: E402

API = "https://api.pinterest.com/v5"


def access_token():
    r = requests.post(
        f"{API}/oauth/token",
        auth=(os.environ["PINTEREST_APP_ID"], os.environ["PINTEREST_APP_SECRET"]),
        data={"grant_type": "refresh_token", "refresh_token": os.environ["PINTEREST_REFRESH_TOKEN"]},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def post(token, spec, png):
    body = {
        "board_id": os.environ["PINTEREST_BOARD_ID"],
        "title": spec["title"][:100],
        "description": spec["description"][:500],
        "link": spec["link"],
        "alt_text": spec["title"][:500],
        "media_source": {"source_type": "image_base64", "content_type": "image/png", "data": base64.b64encode(png).decode()},
    }
    r = requests.post(f"{API}/pins", json=body, headers={"Authorization": f"Bearer {token}"}, timeout=60)
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code} {r.text[:300]}")
    return r.json()["id"]


def log(spec, pin_id):
    new = not pins.POSTED.exists()
    with pins.POSTED.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["id", "pin_id", "date_utc", "link"])
        w.writerow([spec["id"], pin_id, datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"), spec["link"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    n = int(os.environ.get("PINS_PER_RUN") or 3)
    todo = pins.pending()[:n]
    if not todo:
        print("queue empty")
        return
    need = ["PINTEREST_APP_ID", "PINTEREST_APP_SECRET", "PINTEREST_REFRESH_TOKEN", "PINTEREST_BOARD_ID"]
    if not args.dry_run and not all(os.environ.get(k) for k in need):
        print("Pinterest credentials not set yet; skipping.")
        return
    token = None if args.dry_run else access_token()
    for spec in todo:
        buf = io.BytesIO()
        pins.render(spec).save(buf, "PNG", optimize=True)
        if args.dry_run:
            print("dry-run:", spec["id"], len(buf.getvalue()) // 1024, "KB |", spec["title"])
            continue
        pin_id = post(token, spec, buf.getvalue())
        log(spec, pin_id)
        print("posted", spec["id"], pin_id)
        time.sleep(5)


if __name__ == "__main__":
    main()
