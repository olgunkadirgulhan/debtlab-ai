"""Pinterest RSS auto-publish feed (no API / app review needed).

Each run releases the next N pins from pins.queue(): renders 1000x1500 JPEGs into
web/public/pins/ and rewrites web/public/pins.xml. In Pinterest (business account):
Settings > Bulk create Pins > Auto-publish > add https://debtlabai.com/pins.xml + a board.
Pinterest polls the feed and creates a Pin for every new item (drip: N per day).

    python tools/pinterest/feed.py            # release PINS_PER_RUN (default 3)
    python tools/pinterest/feed.py --n 10     # first run: seed more
"""
import argparse
import csv
import os
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

import pins

ROOT = pins.ROOT
PUB = ROOT / "web" / "public"
IMG = PUB / "pins"
LOG = Path(__file__).resolve().parent / "feed.csv"
SITE = pins.SITE


def released():
    if not LOG.exists():
        return []
    with LOG.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=int(os.environ.get("PINS_PER_RUN") or 3))
    n = ap.parse_args().n
    IMG.mkdir(parents=True, exist_ok=True)
    rows = released()
    done = {r["id"] for r in rows}
    by_id = {p["id"]: p for p in pins.queue()}
    now = datetime.now(timezone.utc)
    new = [p for p in pins.queue() if p["id"] not in done][:n]
    for i, spec in enumerate(new):
        pins.render(spec).convert("RGB").save(IMG / f"{spec['id']}.jpg", "JPEG", quality=85, optimize=True)
        rows.append({"id": spec["id"], "at": now.replace(second=i).isoformat()})
    with LOG.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "at"])
        w.writeheader()
        w.writerows(rows)
    items = []
    for r in reversed(rows[-200:]):   # newest first
        p = by_id.get(r["id"])
        if not p or not (IMG / f"{p['id']}.jpg").exists():
            continue
        img = f"{SITE}/pins/{p['id']}.jpg"
        size = (IMG / f"{p['id']}.jpg").stat().st_size
        link = p["link"] + ("&" if "?" in p["link"] else "?") + "utm_source=pinterest&utm_medium=social"
        items.append(f"""  <item>
    <title>{escape(p['title'][:100])}</title>
    <link>{escape(link)}</link>
    <guid isPermaLink="false">{escape(p['id'])}</guid>
    <pubDate>{format_datetime(datetime.fromisoformat(r['at']))}</pubDate>
    <description>{escape(p['description'][:500])}</description>
    <enclosure url="{img}" length="{size}" type="image/jpeg"/>
    <media:content url="{img}" medium="image" type="image/jpeg" width="1000" height="1500"/>
  </item>""")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
<channel>
  <title>DebtLab: debt payoff calculators and tables</title>
  <link>{SITE}/</link>
  <description>Free debt payoff calculators, payoff tables and printables.</description>
  <language>en-us</language>
  <lastBuildDate>{format_datetime(now)}</lastBuildDate>
{chr(10).join(items)}
</channel>
</rss>
"""
    (PUB / "pins.xml").write_text(xml, encoding="utf-8")
    print(f"released {len(new)}, feed has {len(items)} items")


if __name__ == "__main__":
    main()
