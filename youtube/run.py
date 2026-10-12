"""DebtLab Shorts pipeline. One run = one video (VIDEOS_PER_RUN to change).

    topic -> real math -> script (Gemini, validated) -> Kokoro voice -> render -> upload

Env
  YT_PRIVACY      public | private | unlisted | off   (default: private if YT_* secrets exist, else off)
  VIDEOS_PER_RUN  default 1
  MAX_PER_DAY     default 3 (UTC day, counted from published.csv)
  YT_CHANNEL_ID   required for upload; the token must belong to this channel
  GEMINI_API_KEY, YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN

Local test (no upload):  python youtube/run.py --topic 2 --no-upload
Failed uploads are saved to youtube/queue/<id>.json (topic + script, no video) and
retried first on the next run, so the repo never stores video files.
"""
import argparse
import csv
import json
import random
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import facts  # noqa: E402
import meta  # noqa: E402
import script as scriptgen  # noqa: E402

TOPICS = HERE / "topics.csv"
PUBLISHED = HERE / "published.csv"
QUEUE = HERE / "queue"
OUT = HERE / "out"
PUB_FIELDS = ["topic_id", "date_utc", "video_id", "privacy", "pillar", "title", "script_source"]


def log(msg):
    print(f"[run] {msg}", flush=True)


def gh_annotation(level, msg):
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::{level}::{msg}", flush=True)
    else:
        log(f"{level.upper()}: {msg}")


def load_topics():
    with TOPICS.open(newline="", encoding="utf-8") as f:
        return {r["id"]: r for r in csv.DictReader(f)}


def published_rows():
    if not PUBLISHED.exists():
        return []
    with PUBLISHED.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def published_ids():
    return {r["topic_id"] for r in published_rows()}


def uploaded_today():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return sum(1 for r in published_rows() if r["date_utc"].startswith(today))


def record_published(topic, video_id, privacy, source):
    new = not PUBLISHED.exists()
    with PUBLISHED.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PUB_FIELDS)
        if new:
            w.writeheader()
        w.writerow({
            "topic_id": topic["id"],
            "date_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "video_id": video_id,
            "privacy": privacy,
            "pillar": topic["pillar"],
            "title": topic["title"],
            "script_source": source,
        })


def playlists():
    p = HERE / "playlists.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def queued():
    QUEUE.mkdir(exist_ok=True)
    items = []
    for p in sorted(QUEUE.glob("*.json")):
        items.append((p, json.loads(p.read_text(encoding="utf-8"))))
    return items


def enqueue(topic, script, source, error):
    QUEUE.mkdir(exist_ok=True)
    path = QUEUE / f"{int(topic['id']):05d}.json"
    prev = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    path.write_text(json.dumps({
        "topic": topic,
        "script": script,
        "script_source": source,
        "attempts": prev.get("attempts", 0) + 1,
        "last_error": str(error)[:500],
    }, indent=2), encoding="utf-8")
    log(f"queued topic {topic['id']} for retry")


# 2026-10-12 trendler: "credit card / pay off debt / credit score" aramalarında öne çıkan konu türü önce gelir
TREND_KEYS = {'min_trap': ['minimum payment'], 'extra_payment': ['pay off debt fast', 'extra payment', 'faster'],
              'snowball_vs_avalanche': ['snowball', 'avalanche'], 'utilization': ['utilization', 'credit score'],
              'apr_gap': ['apr', 'interest rate'], 'balance_transfer': ['balance transfer', '0%'],
              'payment_ladder': ['monthly payment', 'payoff'], 'two_friends': ['credit card debt', 'minimum']}


def trend_text():
    try:
        import requests
        out = ''
        for q in ('credit card', 'pay off debt', 'credit score'):
            r = requests.get('https://suggestqueries.google.com/complete/search',
                             params={'client': 'firefox', 'ds': 'yt', 'hl': 'en', 'q': q}, timeout=6)
            out += ' ' + ' '.join(r.json()[1]).lower()
        return out
    except Exception:
        return ''


def next_topic(topics, skip):
    nxt = [t for tid, t in topics.items() if tid not in skip][:20]
    if not nxt:
        return None
    tt = trend_text()
    hits = [t for t in nxt if any(w in tt for w in TREND_KEYS.get(t['pillar'], []))]
    if hits and random.random() < 0.5:
        log(f"trend konusu: [{hits[0]['pillar']}] {hits[0]['title']}")
        return hits[0]
    return nxt[0]


def produce(topic, script=None, source=None):
    """Renders the video. Returns (mp4_path, script, source)."""
    import render
    import tts

    built = facts.build(topic)
    cta_text, cta_card = meta.cta()
    if not script:
        script, source = scriptgen.write(topic, built, cta_text)
    log(f"topic {topic['id']} [{topic['pillar']}] {topic['title']}")
    log(f"script ({source}, {len(script.split())} words): {script}")

    out = OUT / f"{int(topic['id']):05d}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "script.txt").write_text(script, encoding="utf-8")
    wav = out / "voice.wav"
    duration, words = tts.synthesize(script, wav)
    log(f"voice {duration:.1f}s")
    mp4 = out / "video.mp4"
    render.render(mp4, wav, duration, words, topic["title"], built, cta_card)
    (out / "description.txt").write_text(meta.description(topic, built), encoding="utf-8")
    log(f"rendered {mp4}")
    return mp4, script, source, built


def privacy_mode(no_upload):
    import upload

    if no_upload:
        return "off"
    mode = (os.environ.get("YT_PRIVACY") or "").strip().lower()
    if mode not in ("public", "private", "unlisted", "off"):
        mode = "private" if upload.configured() else "off"
    return mode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", help="render this topic id (ignores queue/published)")
    ap.add_argument("--no-upload", action="store_true")
    args = ap.parse_args()

    import upload

    mode = privacy_mode(args.no_upload)
    per_run = int(os.environ.get("VIDEOS_PER_RUN") or 1)
    max_per_day = int(os.environ.get("MAX_PER_DAY") or 3)
    topics = load_topics()
    log(f"upload mode: {mode}")

    if mode != "off":
        room = max_per_day - uploaded_today()
        if room <= 0:
            log(f"daily cap of {max_per_day} reached, nothing to do")
            return
        per_run = min(per_run, room)
        try:
            log(f"channel check ok: {upload.check_channel()}")
        except Exception as e:
            gh_annotation("error", f"channel check failed, nothing uploaded: {e}")
            raise SystemExit(1)

    locked = []
    if mode == "public":
        recent = [r["video_id"] for r in published_rows() if r["privacy"] == "public"][-10:]
        try:
            locked = upload.locked_videos(recent)
        except Exception as e:
            log(f"public check skipped: {e}")
        if locked:
            gh_annotation("error", "YouTube made public uploads private (likely needs the API audit): "
                          + ", ".join(f"{v} ({why})" for v, why in locked))
        else:
            log(f"public check ok ({len(recent)} recent videos still public)")

    jobs = []
    if args.topic:
        jobs.append((topics[args.topic], None, None, None))
    else:
        q = queued()
        for path, item in q[:per_run]:
            jobs.append((item["topic"], item["script"], item["script_source"], path))
        skip = published_ids() | {item["topic"]["id"] for _, item in q}
        while len(jobs) < per_run:
            t = next_topic(topics, skip)
            if not t:
                gh_annotation("warning", "topics.csv is used up. Run generate_topics.py --seed <new> to add more.")
                break
            skip.add(t["id"])
            jobs.append((t, None, None, None))

    failed = False
    for topic, script, source, qpath in jobs:
        try:
            mp4, script, source, built = produce(topic, script, source)
        except Exception as e:
            traceback.print_exc()
            gh_annotation("error", f"render failed for topic {topic['id']}: {e}")
            failed = True
            continue

        if mode == "off":
            log("upload skipped (mode off)")
            continue
        try:
            vid = upload.upload(mp4, meta.title(topic), meta.description(topic, built), meta.tags(topic), mode)
        except upload.QuotaError as e:
            enqueue(topic, script, source, e)
            gh_annotation("warning", "YouTube quota reached, video queued for the next run.")
            break
        except Exception as e:
            traceback.print_exc()
            enqueue(topic, script, source, e)
            gh_annotation("error", f"upload failed for topic {topic['id']}: {e}")
            failed = True
            continue
        record_published(topic, vid, mode, source)
        if qpath:
            qpath.unlink(missing_ok=True)
        log(f"uploaded https://youtube.com/shorts/{vid} ({mode})")
        playlist = playlists().get(topic["pillar"])
        if playlist and mode == "public":
            try:
                upload.add_to_playlist(playlist, vid)
            except Exception as e:  # never fail a run over a playlist
                log(f"playlist add skipped: {e}")

    sys.exit(1 if failed or locked else 0)


if __name__ == "__main__":
    main()
