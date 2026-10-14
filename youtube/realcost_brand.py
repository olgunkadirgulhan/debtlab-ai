#!/usr/bin/env python3
"""realcost_brand.py — kanalın "The Real Cost" kimliği (2026-10-14): banner, profil, açıklama, eski videoları gizleme.

    python youtube/realcost_brand.py --make                # sadece görseller (youtube/assets/rc_*.png)
    python youtube/realcost_brand.py --apply [--hide-old]  # YouTube'a uygula (CI: brand.yml)

--hide-old: eski DebtLab Short'larını SİLMEZ, gizli yapar; id'ler youtube/hidden_old.json'a yazılır.
Kanal adı/handle ve profil resmi API ile değişmez → Studio'dan elle.
"""
import csv, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import realcost as R  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

A = HERE / 'assets'
DESCRIPTION = """The sticker price is never the real price.

Each Short takes one price, a car, a house, a credit card balance, a loan or a yearly spending habit, and shows what it really costs once interest and time are added. The rates come from the Federal Reserve (via FRED) and Freddie Mac, and spending averages from the Bureau of Labor Statistics. They are pulled fresh for every video and the source is in every description.

New Shorts every day.

Run your own numbers with the free calculators: https://debtlabai.com

Educational only. Not financial advice."""
KEYWORDS = ['the real cost', 'real cost', 'true cost', 'car loan', 'mortgage', 'credit card debt', 'minimum payment',
            'personal loan', 'interest', 'cost of living', 'personal finance', 'money', 'budget', 'debt']


def banner():
    W, H = 2560, 1440
    img = Image.new('RGB', (W, H), R.BG); d = ImageDraw.Draw(img)
    for y in range(0, H, 4):
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * y / H) for a, b in zip(R.BG, R.BG2)))
    cy = H // 2
    tag = R.price_tag('STICKER PRICE', '$30,000', -6)
    img.paste(tag, (W // 2 - 770, cy - tag.height // 2), tag)
    d.text((W // 2 + 360, cy - 60), 'THE REAL COST', font=R.font(R.ANTON, 150), fill=R.WHITE, anchor='mm')
    d.rounded_rectangle([W // 2 - 20, cy + 40, W // 2 + 420, cy + 100], radius=12, fill=R.GREY)
    d.rounded_rectangle([W // 2 + 410, cy + 40, W // 2 + 740, cy + 100], radius=12, fill=R.ORANGE)
    d.text((W // 2 + 360, cy + 160), 'PRICE  +  INTEREST  +  TIME', font=R.font(R.MONT, 40), fill=R.DIM, anchor='mm')
    img.save(A / 'rc_banner_2560x1440.png')


def profile():
    S = 800
    img = Image.new('RGB', (S, S), R.BG); d = ImageDraw.Draw(img)
    d.rounded_rectangle([150, 250, 650, 550], radius=24, fill=R.ORANGE)
    d.ellipse([190, 375, 240, 425], fill=R.BG)
    d.text((440, 400), '$', font=R.font(R.ANTON, 260), fill=R.BG, anchor='mm')
    d.text((S // 2, 660), 'THE REAL COST', font=R.font(R.ANTON, 80), fill=R.WHITE, anchor='mm')
    img.save(A / 'rc_profile_800x800.png')


def apply(hide_old):
    import upload
    from googleapiclient.http import MediaFileUpload
    yt = upload._client()
    ch = yt.channels().list(part='snippet,brandingSettings', mine=True).execute()['items'][0]
    print('kanal:', ch['snippet']['title'])
    url = yt.channelBanners().insert(media_body=MediaFileUpload(str(A / 'rc_banner_2560x1440.png'), mimetype='image/png')).execute()['url']
    b = ch.get('brandingSettings', {}); b.setdefault('channel', {})
    b['channel']['description'] = DESCRIPTION
    b['channel']['keywords'] = ' '.join(f'"{k}"' if ' ' in k else k for k in KEYWORDS)
    b['channel'].pop('unsubscribedTrailer', None)
    b.setdefault('image', {})['bannerExternalUrl'] = url
    b.pop('hints', None)
    yt.channels().update(part='brandingSettings', body={'id': ch['id'], 'brandingSettings': b}).execute()
    print('✓ banner + açıklama + anahtar kelimeler (eski fragman kaldırıldı)')
    if not hide_old:
        return
    with (HERE / 'published.csv').open(encoding='utf-8') as f:
        old = [r['video_id'] for r in csv.DictReader(f) if not r['topic_id'].startswith('rc:') and r['video_id']]
    hf = HERE / 'hidden_old.json'; hidden = json.loads(hf.read_text()) if hf.exists() else []
    for i in range(0, len(old), 50):
        for v in yt.videos().list(part='status,snippet', id=','.join(old[i:i + 50])).execute().get('items', []):
            if v['status']['privacyStatus'] == 'private': continue
            st = v['status']; was = st['privacyStatus']; st['privacyStatus'] = 'private'; st.pop('publishAt', None)
            yt.videos().update(part='status', body={'id': v['id'], 'status': st}).execute()
            hidden.append({'id': v['id'], 'was': was, 'title': v['snippet']['title']})
            print(f"  gizlendi: {v['id']} | {v['snippet']['title'][:60]}")
    hf.write_text(json.dumps(hidden, indent=1, ensure_ascii=False))
    print(f'✓ {len(hidden)} eski video gizli (geri almak için youtube/hidden_old.json)')


if __name__ == '__main__':
    if '--make' in sys.argv or not (A / 'rc_banner_2560x1440.png').exists():
        banner(); profile(); print('✓ assets/rc_banner_2560x1440.png, rc_profile_800x800.png')
    if '--apply' in sys.argv:
        apply('--hide-old' in sys.argv)
