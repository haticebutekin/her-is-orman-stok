from functools import wraps

from flask import Flask, request, redirect, render_template_string, jsonify, session, send_file
import psycopg2
import os, random, io
from datetime import datetime
from zoneinfo import ZoneInfo
import barcode, qrcode
from barcode.writer import ImageWriter

TR_TZ = ZoneInfo("Europe/Istanbul")

# ==================== VERİTABANI (Postgres) ====================
DATABASE_URL = os.environ.get("DATABASE_URL", "")

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)) or ".", "static"))
app.secret_key = os.environ.get("SECRET_KEY", "bu-anahtari-canliya-almadan-once-degistir")

if os.path.exists(app.static_folder) and not os.path.isdir(app.static_folder):
    os.remove(app.static_folder)
if not os.path.exists(app.static_folder):
    os.makedirs(app.static_folder)

DEPOLAR = [
    "MDF SATIŞ DEPOSU",
    "LAMİNANT DEPOSU",
    "KAPI DEPOSU",
    "HGLOSS DEPOSU (MORAY YANI)",
    "SÜTÇÜ YANI",
    "HELVACI YANI",
    "RÖTBALANSÇI YANI",
    "KESİMHANE",
    "OFİS",
]

ROLLER = {
    "Ramazan": "depocu",
    "Behiç": "depocu",
    "Orhan": "depocu",
    "Berke": "muhasebeci",
    "İrem": "muhasebeci",
    "Hatice": "patron",
    "Ahmet": "patron",
}

PIN_KODLARI = {
    "Ramazan": "1111",
    "Behiç": "1111",
    "Orhan": "1111",
    "Berke": "2222",
    "İrem": "2222",
    "Hatice": "2222",
    "Ahmet": "2222",
}


def db():
    return psycopg2.connect(DATABASE_URL)


def tablolari_olustur():
    con = db()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS urun(
                    id SERIAL PRIMARY KEY,
                    ad TEXT, cins TEXT, ebat TEXT, kalinlik TEXT,
                    yuzey TEXT, sinif TEXT, renk TEXT,
                    adet INTEGER, depo TEXT, barkod TEXT UNIQUE
                )
                """)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS hareket(
                    id SERIAL PRIMARY KEY,
                    barkod TEXT,
                    ad TEXT,
                    tip TEXT,
                    adet INTEGER,
                    kullanici TEXT,
                    tarih TIMESTAMP
                )
                """)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS urun_barkod(
                    id SERIAL PRIMARY KEY,
                    urun_id INTEGER REFERENCES urun(id) ON DELETE CASCADE,
                    barkod TEXT UNIQUE
                )
                """)
                cur.execute("""
                INSERT INTO urun_barkod (urun_id, barkod)
                SELECT u.id, u.barkod FROM urun u
                WHERE u.barkod IS NOT NULL
                AND NOT EXISTS (
                    SELECT 1 FROM urun_barkod ub WHERE ub.barkod = u.barkod
                )
                """)
                cur.execute("ALTER TABLE hareket ALTER COLUMN tarih DROP DEFAULT")
    finally:
        con.close()


if DATABASE_URL:
    tablolari_olustur()


def tr_simdi():
    return datetime.now(TR_TZ).replace(tzinfo=None)


def bugunku_ozet(kullanici):
    bugun = tr_simdi().date()
    con = db()
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT tip, COUNT(*) FROM hareket
                WHERE kullanici=%s AND tarih::date=%s
                GROUP BY tip
            """, (kullanici, bugun))
            satirlar = dict(cur.fetchall())
    finally:
        con.close()
    return satirlar.get("giris", 0), satirlar.get("cikis", 0)


def barkod_uret():
    while True:
        kod = str(random.randint(100000000000, 999999999999))
        con = db()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT barkod FROM urun_barkod WHERE barkod=%s", (kod,))
                var = cur.fetchone()
        finally:
            con.close()
        if not var:
            return kod


def barkod_png_bytes(kod):
    CODE128 = barcode.get_barcode_class("code128")
    bio = io.BytesIO()
    CODE128(kod, writer=ImageWriter()).write(bio)
    bio.seek(0)
    return bio


def qr_png_bytes(kod):
    img = qrcode.make(kod)
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio


def ikon_uret():
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    for boyut in (192, 512):
        yol = os.path.join(app.static_folder, f"icon-{boyut}.png")
        if os.path.exists(yol):
            continue
        img = Image.new("RGB", (boyut, boyut), "#2196F3")
        d = ImageDraw.Draw(img)
        for y in range(boyut):
            oran = y / boyut
            r = int(0x21 + (0x00 - 0x21) * oran)
            g = int(0x96 + (0xBC - 0x96) * oran)
            b = int(0xF3 + (0xD4 - 0xF3) * oran)
            d.line([(0, y), (boyut, y)], fill=(r, g, b))
        pad = int(boyut * 0.22)
        cizgi = max(2, boyut // 35)
        d.rectangle([pad, int(pad * 1.3), boyut - pad, boyut - pad], outline="white", width=cizgi)
        d.line([(pad, int(boyut * 0.46)), (boyut - pad, int(boyut * 0.46))], fill="white", width=cizgi)
        d.line([(boyut / 2, int(pad * 1.3)), (boyut / 2, int(boyut * 0.46))], fill="white", width=max(2, cizgi // 2))
        img.save(yol)


ikon_uret()


BASE_HEAD_EXTRA = """
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#111111">
<link rel="manifest" href="/manifest.json">
<link rel="icon" href="/static/icon-192.png">
<link rel="apple-touch-icon" href="/static/icon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="mobile-web-app-capable" content="yes">
"""

ORTAK_CSS = """
:root {
  --bg:#0b0d12; --bg2:#12151c; --card:#171a22; --card2:#1c202b;
  --border:#262b38; --text:#f4f5f7; --muted:#8b93a3; --accent:#2196F3;
  --radius:16px; --radius-sm:10px;
}
* { box-sizing: border-box; }
html { scrollbar-color: #333 transparent; }
body {
  background:
    radial-gradient(1200px 600px at 50% -10%, rgba(33,150,243,.08), transparent 60%),
    var(--bg);
  color: var(--text); margin:0; padding:0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
  -webkit-tap-highlight-color: transparent;
}
input, select, button, textarea { font-size: 16px; font-family: inherit; }
a { color: inherit; }
::selection { background: rgba(33,150,243,.35); }

.topbar {
  position: fixed; top:0; left:0; right:0; z-index: 9999;
  height: 56px; padding-top: env(safe-area-inset-top);
  display:flex; align-items:center; justify-content:space-between;
  padding-left:12px; padding-right:12px;
  background: rgba(18,21,28,.75); backdrop-filter: blur(14px) saturate(140%);
  -webkit-backdrop-filter: blur(14px) saturate(140%);
  border-bottom: 1px solid rgba(255,255,255,.06);
}
.topbar-btn {
  text-decoration:none; color:white; font-size:19px; padding:8px 12px;
  border-radius:10px; transition: background .15s ease, transform .1s ease;
}
.topbar-btn:active { background:rgba(255,255,255,.08); transform: scale(0.94); }
.topbar-title { font-weight:700; font-size:14.5px; color:#eee; letter-spacing:.2px; display:flex; align-items:center; gap:7px; }
.topbar-logo { height:26px; width:26px; border-radius:6px; object-fit:contain; background:white; padding:2px; }

.sayfa {
  max-width: 520px; margin: 0 auto;
  padding: calc(56px + env(safe-area-inset-top) + 22px) 16px 60px;
  animation: belir .25s ease;
}
@keyframes belir { from { opacity:0; transform: translateY(6px);} to { opacity:1; transform:none; } }

h1, h2, h3 { text-align:center; letter-spacing:-.01em; }
h1 { font-size: 24px; }
h3.alt { color: var(--muted); font-weight:500; margin-top:-6px; font-size:14px; }

.btn {
  display:block; width:100%; margin:10px 0; padding:17px;
  font-size:17px; border-radius: var(--radius); text-decoration:none;
  color:white; font-weight:600; text-align:center; border:none; cursor:pointer;
  box-shadow: 0 4px 14px rgba(0,0,0,.28);
  transition: transform .1s ease, filter .15s ease, box-shadow .15s ease;
  letter-spacing:.1px;
}
.btn:active { filter:brightness(0.88); transform: scale(0.985); box-shadow: 0 2px 8px rgba(0,0,0,.3); }
.mavi   { background: linear-gradient(135deg, #2196F3, #00BCD4); }
.yesil  { background: linear-gradient(135deg, #00C853, #64DD17); }
.turuncu{ background: linear-gradient(135deg, #FF6F00, #FF9800); }
.mor    { background: linear-gradient(135deg, #5E35B1, #7E57C2); }
.kirmizi{ background: linear-gradient(135deg, #D50000, #FF1744); }
.turkuaz{ background: linear-gradient(135deg, #00838F, #00BFA5); }
.gri    { background: linear-gradient(135deg, #3a3f4b, #2a2e38); }

.btn-kucuk {
  display:inline-block; padding:10px 16px; font-size:14px; font-weight:600;
  border-radius: 10px; text-decoration:none; color:white; border:none; cursor:pointer;
  transition: transform .1s ease, filter .15s ease; margin-right:8px; margin-top:4px;
}
.btn-kucuk:active { filter:brightness(0.85); transform: scale(0.96); }

.kart {
  background: linear-gradient(180deg, var(--card2), var(--card));
  border:1px solid var(--border); border-radius: var(--radius);
  padding:16px; margin:12px 0; text-align:left;
  box-shadow: 0 2px 10px rgba(0,0,0,.18);
  transition: border-color .15s ease;
}

input[type=text], input[type=number], input[type=password], input[type=file], select, textarea {
  width:100%; padding:14px; margin:6px 0 14px; border-radius: var(--radius-sm);
  border:1px solid var(--border); background:#12151c; color:white;
  transition: border-color .15s ease, box-shadow .15s ease;
}
input:focus, select:focus, textarea:focus {
  outline:none; border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(33,150,243,.18);
}
label { color: var(--muted); font-size:13px; font-weight:600; letter-spacing:.2px; text-transform:uppercase; }

.arama {
  width:100%; padding:14px 16px; margin: 4px 0 16px; border-radius:999px;
  border:1px solid var(--border); background:#12151c; color:white;
  transition: border-color .15s ease, box-shadow .15s ease;
}
.arama:focus { outline:none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(33,150,243,.18); }

.pin-input {
  font-size: 34px; text-align:center; width:200px; padding:12px;
  border-radius:14px; border:1px solid var(--border); letter-spacing:10px;
  background:#12151c; color:white; display:block; margin:20px auto;
}
.pin-input:focus { outline:none; border-color: var(--accent); box-shadow: 0 0 0 3px rgba(33,150,243,.18); }

.video-alan { display:flex; justify-content:center; margin:16px 0; }
.video-alan video { border-radius: var(--radius); box-shadow:0 8px 24px rgba(0,0,0,.5); }

.qr-kutu { text-align:center; margin: 18px 0; }
.qr-kutu img { border-radius:14px; background:white; padding:10px; box-shadow: 0 4px 16px rgba(0,0,0,.25); }
.qr-not { color: var(--muted); font-size:13px; text-align:center; margin-top:8px; line-height:1.5; }

.hata { color:#FF6B6B; font-weight:600; text-align:center; }
.basari { color:#2FE686; font-weight:600; text-align:center; }

.rozet {
  display:inline-block; padding:3px 10px; border-radius:999px; font-size:11.5px;
  font-weight:700; letter-spacing:.3px; background:rgba(33,150,243,.15); color:#64B5F6;
}

.ozet-satir { display:flex; gap:10px; margin: 4px 0 18px; }
.ozet-kutu {
  flex:1; border-radius: var(--radius); padding: 14px 10px; text-align:center;
  border:1px solid var(--border);
  background: linear-gradient(180deg, var(--card2), var(--card));
}
.ozet-sayi { font-size: 26px; font-weight:800; line-height:1.1; }
.ozet-etiket { font-size:11.5px; color:var(--muted); margin-top:2px; text-transform:uppercase; letter-spacing:.3px; }
.ozet-yesil .ozet-sayi { color:#64DD17; }
.ozet-turuncu .ozet-sayi { color:#FF9800; }

.okut-kart {
  display:flex; align-items:center; gap:14px;
  text-decoration:none; color:white; border-radius: var(--radius);
  padding: 20px 18px; margin: 12px 0; border:1px solid var(--border);
  box-shadow: 0 4px 16px rgba(0,0,0,.25);
  transition: transform .12s ease, filter .15s ease;
}
.okut-kart:active { transform: scale(0.97); filter:brightness(0.92); }
.okut-yesil { background: linear-gradient(135deg, rgba(0,200,83,.22), rgba(100,221,23,.10)); border-color: rgba(100,221,23,.35); }
.okut-turuncu { background: linear-gradient(135deg, rgba(255,111,0,.22), rgba(255,152,0,.10)); border-color: rgba(255,152,0,.35); }
.okut-mavi { background: linear-gradient(135deg, rgba(33,150,243,.22), rgba(0,188,212,.10)); border-color: rgba(33,150,243,.35); }
.okut-mor { background: linear-gradient(135deg, rgba(94,53,177,.28), rgba(126,87,194,.12)); border-color: rgba(126,87,194,.4); }
.okut-kirmizi { background: linear-gradient(135deg, rgba(213,0,0,.22), rgba(255,23,68,.10)); border-color: rgba(255,23,68,.35); }
.okut-turkuaz { background: linear-gradient(135deg, rgba(0,131,143,.28), rgba(0,191,165,.12)); border-color: rgba(0,191,165,.4); }
.okut-ikon { font-size: 30px; width:46px; text-align:center; flex-shrink:0; }
.okut-metin { flex:1; }
.okut-baslik { font-size:17px; font-weight:700; }
.okut-alt { font-size:12.5px; color: var(--muted); margin-top:2px; }
.okut-ok { font-size:24px; color: var(--muted); }

.bolum-baslik {
  color: var(--muted); font-size:12.5px; font-weight:700; text-transform:uppercase;
  letter-spacing:.5px; margin: 22px 4px 8px;
}
.rapor-satir { display:flex; gap:8px; margin-bottom:6px; }
.rapor-pil {
  flex:1; text-align:center; padding:12px 6px; border-radius:999px;
  background:#12151c; border:1px solid var(--border); color:var(--text);
  text-decoration:none; font-weight:700; font-size:13px;
  transition: transform .1s ease, filter .15s ease;
}
.rapor-pil:active { transform: scale(0.96); filter:brightness(1.15); }

.kisi-kart {
  display:flex; align-items:center; gap:14px; text-decoration:none; color:white;
  border-radius: var(--radius); padding:14px 16px; margin:10px 0;
  border:1px solid var(--border);
  background: linear-gradient(180deg, var(--card2), var(--card));
  transition: transform .1s ease, filter .15s ease;
}
.kisi-kart:active { transform: scale(0.98); filter:brightness(0.92); }
.kisi-avatar {
  width:44px; height:44px; border-radius:50%; flex-shrink:0;
  display:flex; align-items:center; justify-content:center;
  font-weight:800; font-size:17px; color:white;
}
.kisi-yesil { background: linear-gradient(135deg, #00C853, #64DD17); }
.kisi-mavi { background: linear-gradient(135deg, #2196F3, #00BCD4); }
.kisi-mor { background: linear-gradient(135deg, #5E35B1, #7E57C2); }
.kisi-metin { flex:1; }
.kisi-ad { font-size:16px; font-weight:700; }
.kisi-rol { font-size:12px; color:var(--muted); margin-top:1px; }

.ozet-kutu:not(.ozet-yesil):not(.ozet-turuncu) .ozet-sayi { color: #64B5F6; }
.urun-kart {
  background: linear-gradient(180deg, var(--card2), var(--card));
  border:1px solid var(--border); border-radius: var(--radius);
  padding:14px 16px; margin:12px 0; text-align:left;
  box-shadow: 0 2px 10px rgba(0,0,0,.18);
}
.urun-kart.urun-kritik { border-color: rgba(255,152,0,.5); }
.etiket-sec-satir {
  display:flex; align-items:center; gap:8px; cursor:pointer; margin-bottom:10px;
  text-transform:none; font-size:13px; color:var(--muted); font-weight:500;
}
.etiket-sec-satir input { width:19px; height:19px; margin:0; }
.urun-ust { display:flex; align-items:center; justify-content:space-between; gap:8px; }
.urun-ad { font-size:16.5px; font-weight:700; }
.urun-adet-rozet {
  flex-shrink:0; padding:4px 11px; border-radius:999px; font-size:12.5px; font-weight:700;
  background: rgba(100,221,23,.15); color:#9CCC65;
}
.urun-adet-rozet.kritik { background: rgba(255,152,0,.18); color:#FFB74D; }
.urun-ozellik { font-size:13px; color:var(--muted); margin-top:6px; line-height:1.5; }
.urun-depo, .urun-barkod { font-size:12.5px; color:var(--muted); margin-top:3px; }
.urun-gorseller { display:flex; align-items:center; gap:14px; margin-top:10px; }
.urun-gorseller img:first-child { flex:1; max-width:180px; }
.urun-gorseller img:last-child { width:64px; }
.urun-aksiyonlar { margin-top:10px; }

.filtre-satir { display:flex; gap:8px; margin: 0 0 14px; flex-wrap:wrap; }
.filtre-cip {
  flex:1; text-align:center; padding:9px 6px; border-radius:999px;
  background:#12151c; border:1px solid var(--border); color:var(--muted);
  font-weight:700; font-size:13px; cursor:pointer; transition: all .15s ease;
  min-width: 80px;
}
.filtre-cip.aktif { background: var(--accent); border-color: var(--accent); color:white; }
.hareket-kart {
  display:flex; gap:12px; align-items:flex-start;
  background: linear-gradient(180deg, var(--card2), var(--card));
  border:1px solid var(--border); border-left:3px solid var(--border);
  border-radius: var(--radius); padding:13px 15px; margin:10px 0;
}
.hareket-kart.hareket-giris { border-left-color: #64DD17; }
.hareket-kart.hareket-cikis { border-left-color: #FF9800; }
.hareket-ikon { font-size:19px; flex-shrink:0; margin-top:1px; }
.hareket-govde { flex:1; min-width:0; }
.hareket-ust { display:flex; align-items:center; justify-content:space-between; gap:8px; }
.hareket-ad { font-size:15px; font-weight:700; }
.hareket-adet { font-size:13.5px; font-weight:800; flex-shrink:0; }
.hareket-adet.giris { color:#9CCC65; }
.hareket-adet.cikis { color:#FFB74D; }
.hareket-detay { font-size:12.5px; color:var(--muted); margin-top:3px; }
.hareket-alt { font-size:11.5px; color:var(--muted); margin-top:5px; opacity:.85; }

/* --- Toplu Excel Yükleme --- */
.yukleme-alan {
  border:2px dashed var(--border); border-radius: var(--radius);
  padding: 28px 16px; text-align:center; margin: 14px 0;
  background: linear-gradient(180deg, var(--card2), var(--card));
}
.yukleme-ikon { font-size:40px; margin-bottom:6px; }
.on-izleme-satir {
  display:flex; justify-content:space-between; align-items:center;
  padding:10px 14px; border-bottom:1px solid var(--border); font-size:13.5px;
}
.on-izleme-satir:last-child { border-bottom:none; }
.on-izleme-hata { color:#FF6B6B; font-size:12px; margin-top:2px; }
.sablon-link { display:inline-block; margin-top:8px; font-size:13px; color:var(--accent); text-decoration:none; }

/* --- Depo Özet --- */
.depo-ozet-kart {
  display:flex; align-items:center; justify-content:space-between; gap:10px;
  background: linear-gradient(180deg, var(--card2), var(--card));
  border:1px solid var(--border); border-radius: var(--radius);
  padding:14px 16px; margin:10px 0;
}
.depo-ozet-ad { font-size:14.5px; font-weight:700; }
.depo-ozet-sayilar { display:flex; gap:14px; flex-shrink:0; }
.depo-ozet-tekli { text-align:center; }
.depo-ozet-tekli .sayi { font-size:17px; font-weight:800; color:#64B5F6; }
.depo-ozet-tekli .etiket { font-size:10px; color:var(--muted); text-transform:uppercase; }

/* --- Sipariş --- */
.siparis-kart {
  display:block; text-decoration:none; color:white;
  background: linear-gradient(180deg, var(--card2), var(--card));
  border:1px solid var(--border); border-radius: var(--radius);
  padding:15px 17px; margin:10px 0;
  box-shadow: 0 2px 10px rgba(0,0,0,.18);
}
.siparis-ust { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.siparis-no { font-size:16px; font-weight:800; }
.siparis-durum {
  padding:3px 10px; border-radius:999px; font-size:11px; font-weight:700; text-transform:uppercase;
}
.siparis-durum.acik { background: rgba(255,152,0,.18); color:#FFB74D; }
.siparis-durum.tamamlandi { background: rgba(100,221,23,.15); color:#9CCC65; }
.siparis-durum.iptal { background: rgba(255,23,68,.15); color:#FF6B6B; }
.siparis-detay { font-size:13px; color:var(--muted); margin-top:6px; line-height:1.6; }
.siparis-ilerleme-bar {
  height:6px; border-radius:999px; background:#12151c; margin-top:10px; overflow:hidden;
}
.siparis-ilerleme-dolu { height:100%; background: linear-gradient(90deg, #2196F3, #00BCD4); }

.kalem-satir {
  display:flex; justify-content:space-between; align-items:center; gap:8px;
  padding:10px 0; border-bottom:1px solid var(--border); font-size:14px;
}
.kalem-satir:last-child { border-bottom:none; }
.kalem-ad { flex:1; }
.kalem-miktar { font-weight:800; font-size:13.5px; flex-shrink:0; }
.kalem-miktar.tam { color:#9CCC65; }
.kalem-miktar.eksik { color:#FFB74D; }

.urun-arama-kutu { position:relative; }
.urun-arama-sonuc {
  border:1px solid var(--border); border-radius: var(--radius-sm);
  margin-top:-8px; margin-bottom:14px; max-height:260px; overflow-y:auto;
  background:#12151c; display:none;
}
.urun-arama-oge {
  padding:12px 14px; border-bottom:1px solid var(--border); cursor:pointer; font-size:13.5px;
}
.urun-arama-oge:last-child { border-bottom:none; }
.urun-arama-oge:active { background: rgba(33,150,243,.15); }
.urun-arama-oge .ad { font-weight:700; }
.urun-arama-oge .detay { color:var(--muted); font-size:12px; margin-top:2px; }

.sepet-satir {
  display:flex; align-items:center; gap:8px;
  background:#12151c; border:1px solid var(--border); border-radius: var(--radius-sm);
  padding:10px 12px; margin-bottom:8px;
}
.sepet-ad { flex:1; font-size:13.5px; font-weight:600; }
.sepet-adet-input { width:70px !important; margin:0 !important; padding:8px !important; text-align:center; }
.sepet-sil { background:none; border:none; color:#FF6B6B; font-size:20px; cursor:pointer; padding:4px 8px; }

.uyari-kutu {
  border-radius: var(--radius); padding:14px 16px; margin: 10px 0;
  background: rgba(255,152,0,.12); border:1px solid rgba(255,152,0,.35);
  color:#FFB74D; font-size:13.5px; line-height:1.6;
}
"""

LOGO_URL = "/static/logo.png"
UYGULAMA_ADI = "HER-İŞ ORMAN ÜRÜNLERİ STOK TAKİP SİSTEMİ"

UST_BAR = f"""
<div class="topbar">
  <a href="/" class="topbar-btn" title="Ana Sayfa">🏠</a>
  <span class="topbar-title"><img src="{LOGO_URL}" class="topbar-logo" alt="logo">HER-İŞ ORMAN ÜRÜNLERİ SİPARİŞ-STOK TAKİP SİSTEMİ</span>
  <a href="/kullanici_degistir" class="topbar-btn" title="Kullanıcı Değiştir">🔁</a>
  <img src="https://upload.wikimedia.org/wikipedia/commons/3/3f/Placeholder_view_vector.svg" width="40">
</div>
"""

HOME_BTN = UST_BAR


def sayfa(icerik, baslik="Stok Takip"):
    return (
        "<!DOCTYPE html><html lang=\"tr\"><head><meta charset=\"utf-8\">"
        + "<title>" + baslik + "</title>"
        + BASE_HEAD_EXTRA
        + "<style>" + ORTAK_CSS + "</style>"
        + "</head><body>"
        + UST_BAR
        + "<div class=\"sayfa\">" + icerik + "</div>"
        + "</body></html>"
    )


@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": UYGULAMA_ADI,
        "short_name": "HER-İŞ Stok",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f1115",
        "theme_color": "#111111",
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
    })


@app.route("/qr_baglan")
def qr_baglan():
    url = request.host_url
    img = qrcode.make(url)
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return send_file(bio, mimetype="image/png")


@app.route("/barkod/<kod>.png")
def barkod_resim_endpoint(kod):
    return send_file(barkod_png_bytes(kod), mimetype="image/png")


@app.route("/qr/<kod>.png")
def qr_resim_endpoint(kod):
    return send_file(qr_png_bytes(kod), mimetype="image/png")


def rol_gerekli(*izinli_roller):
    TAM_YETKILI = ("patron", "muhasebeci")

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            rol = session.get("rol")
            if not rol:
                return redirect("/")
            if rol not in TAM_YETKILI and rol not in izinli_roller:
                return sayfa("""
                <h2>⛔ Erişim Yetkiniz Yok</h2>
                <p style="text-align:center;color:var(--muted);">
                Bu işlem senin rolüne kapalı. Yanlış kişi olarak girdiysen
                sağ üstten kullanıcı değiştir.
                </p>
                """, "Yetkisiz Erişim")
            return f(*args, **kwargs)
        return wrapper
    return decorator


@app.route("/pin_gir/<isim>", methods=["GET", "POST"])
def pin_gir(isim):
    if isim not in ROLLER:
        return redirect("/")

    hata = None
    if request.method == "POST":
        girilen = request.form.get("pin", "")
        if girilen == PIN_KODLARI.get(isim):
            session["kullanici"] = isim
            session["rol"] = ROLLER[isim]
            return redirect("/")
        hata = "❌ Yanlış PIN, tekrar dene"

    icerik = """
    <style>
    .pin-avatar {
      width:72px; height:72px; border-radius:50%; margin: 6px auto 4px;
      background: linear-gradient(135deg, #2196F3, #00BCD4);
      display:flex; align-items:center; justify-content:center;
      font-size:28px; font-weight:800; color:white;
      box-shadow: 0 6px 20px rgba(33,150,243,.35);
    }
    .pin-noktalar { display:flex; justify-content:center; gap:14px; margin: 22px 0; }
    .pin-nokta {
      width:16px; height:16px; border-radius:50%; border:2px solid var(--border);
      background:transparent; transition: all .12s ease;
    }
    .pin-nokta.dolu { background: var(--accent); border-color: var(--accent); }
    .tuş-takimi { display:grid; grid-template-columns: repeat(3, 1fr); gap:12px; max-width:280px; margin:0 auto; }
    .tuş {
      aspect-ratio:1; border-radius:50%; border:1px solid var(--border);
      background:#12151c; color:white; font-size:22px; font-weight:700;
      display:flex; align-items:center; justify-content:center; cursor:pointer;
      transition: transform .08s ease, filter .12s ease;
    }
    .tuş:active { transform: scale(0.92); filter:brightness(1.3); background:var(--accent); }
    .tuş.bos { background:transparent; border:none; cursor:default; }
    .tuş.bos:active { transform:none; filter:none; background:transparent; }
    </style>

    <div class="pin-avatar">{{isim[0]|upper}}</div>
    <h2 style="margin-bottom:2px;">{{isim}}</h2>
    <p style="text-align:center;color:var(--muted);margin-top:0;">PIN gir</p>

    {% if hata %}<p class="hata">{{hata}}</p>{% endif %}

    <div class="pin-noktalar" id="noktalar">
      <div class="pin-nokta"></div><div class="pin-nokta"></div>
      <div class="pin-nokta"></div><div class="pin-nokta"></div>
    </div>

    <form method="post" id="pin-form">
      <input type="hidden" name="pin" id="pin-gizli">
    </form>

    <div class="tuş-takimi">
      <div class="tuş" onclick="tuslaEkle('1')">1</div>
      <div class="tuş" onclick="tuslaEkle('2')">2</div>
      <div class="tuş" onclick="tuslaEkle('3')">3</div>
      <div class="tuş" onclick="tuslaEkle('4')">4</div>
      <div class="tuş" onclick="tuslaEkle('5')">5</div>
      <div class="tuş" onclick="tuslaEkle('6')">6</div>
      <div class="tuş" onclick="tuslaEkle('7')">7</div>
      <div class="tuş" onclick="tuslaEkle('8')">8</div>
      <div class="tuş" onclick="tuslaEkle('9')">9</div>
      <div class="tuş bos"></div>
      <div class="tuş" onclick="tuslaEkle('0')">0</div>
      <div class="tuş" onclick="silTusu()">⌫</div>
    </div>

    <p style="text-align:center;margin-top:24px;">
    <a href="/" style="color:var(--muted);text-decoration:none;">⬅ Geri</a>
    </p>

    <script>
    let girilenPin = "";
    function noktalariGuncelle(){
      document.querySelectorAll('.pin-nokta').forEach((n, i) => {
        n.classList.toggle('dolu', i < girilenPin.length);
      });
    }
    function tuslaEkle(rakam){
      if(girilenPin.length >= 4) return;
      girilenPin += rakam;
      if(navigator.vibrate) navigator.vibrate(15);
      noktalariGuncelle();
      if(girilenPin.length === 4){
        document.getElementById('pin-gizli').value = girilenPin;
        setTimeout(() => document.getElementById('pin-form').submit(), 120);
      }
    }
    function silTusu(){
      girilenPin = girilenPin.slice(0, -1);
      noktalariGuncelle();
    }
    </script>
    """
    return render_template_string(sayfa(icerik, "Giriş"), isim=isim, hata=hata)


@app.route("/kullanici_degistir")
def kullanici_degistir():
    session.clear()
    return redirect("/")


@app.route("/")
def index():
    kullanici = session.get("kullanici")
    rol = session.get("rol")

    if not kullanici:
        ROL_ETIKET = {"depocu": "Depocu", "muhasebeci": "Muhasebeci", "patron": "Patron"}
        ROL_RENK = {"depocu": "kisi-yesil", "muhasebeci": "kisi-mavi", "patron": "kisi-mor"}
        secim_html = ""
        for isim in ROLLER:
            bas_harf = isim[0].upper()
            rol_adi = ROL_ETIKET.get(ROLLER[isim], "")
            renk = ROL_RENK.get(ROLLER[isim], "kisi-mavi")
            secim_html += f"""
            <a href="/pin_gir/{isim}" class="kisi-kart">
              <div class="kisi-avatar {renk}">{bas_harf}</div>
              <div class="kisi-metin">
                <div class="kisi-ad">{isim}</div>
                <div class="kisi-rol">{rol_adi}</div>
              </div>
              <div class="okut-ok">›</div>
            </a>
            """

        icerik = (
            f'<div style="text-align:center;margin-bottom:6px;"><img src="{LOGO_URL}" style="width:110px;height:auto;border-radius:14px;background:white;padding:8px;box-shadow:0 6px 20px rgba(0,0,0,.35);"></div>'
            + f'<h1 style="font-size:19px;line-height:1.35;margin-bottom:2px;">{UYGULAMA_ADI}</h1>'
            + '<h3 class="alt">Devam etmek için ismini seç</h3>'
            + secim_html
            + """
            <div class="kart qr-kutu">
              <p style="margin-top:0;">📱 Bu siteyi telefonundan hızlı açmak için QR'ı okut:</p>
              <img src="/qr_baglan" width="170" height="170">
              <p class="qr-not">Açıldıktan sonra tarayıcı menüsünden
              "Ana Ekrana Ekle" seçersen, ikonu telefonuna normal bir
              uygulama gibi kurabilirsin.</p>
            </div>
            """
        )
        return sayfa(icerik, "Giriş - " + UYGULAMA_ADI)

    butonlar = ""
    if rol in ("depocu", "muhasebeci", "patron"):
        giris_sayisi, cikis_sayisi = bugunku_ozet(kullanici)
        butonlar += f"""
        <div class="ozet-satir">
          <div class="ozet-kutu ozet-yesil"><div class="ozet-sayi">{giris_sayisi}</div><div class="ozet-etiket">Bugün Giriş</div></div>
          <div class="ozet-kutu ozet-turuncu"><div class="ozet-sayi">{cikis_sayisi}</div><div class="ozet-etiket">Bugün Çıkış</div></div>
        </div>
        <a href="/kamera/giris" class="okut-kart okut-yesil">
          <div class="okut-ikon">⬆️</div>
          <div class="okut-metin"><div class="okut-baslik">Giriş Okut</div><div class="okut-alt">Depoya gelen ürünü tara</div></div>
          <div class="okut-ok">›</div>
        </a>
        <a href="/kamera/cikis" class="okut-kart okut-turuncu">
          <div class="okut-ikon">⬇️</div>
          <div class="okut-metin"><div class="okut-baslik">Çıkış Okut</div><div class="okut-alt">Depodan çıkan ürünü tara</div></div>
          <div class="okut-ok">›</div>
        </a>
        """
    if rol in ("depocu",):
        butonlar += """
        <a href="/depo_stok" class="okut-kart okut-turkuaz">
          <div class="okut-ikon">🏭</div>
          <div class="okut-metin"><div class="okut-baslik">Depo Stok Durumu</div><div class="okut-alt">Hangi depoda ne kadar var</div></div>
          <div class="okut-ok">›</div>
        </a>
        """
    if rol in ("muhasebeci", "patron"):
        butonlar += """
        <div class="bolum-baslik">Sipariş</div>
        <a href="/siparis_olustur" class="okut-kart okut-yesil">
          <div class="okut-ikon">🧾</div>
          <div class="okut-metin"><div class="okut-baslik">Yeni Sipariş Oluştur</div><div class="okut-alt">Depocuya hazırlatılacak ürünleri seç</div></div>
          <div class="okut-ok">›</div>
        </a>
        <a href="/siparisler" class="okut-kart okut-turuncu">
          <div class="okut-ikon">📋</div>
          <div class="okut-metin"><div class="okut-baslik">Siparişler</div><div class="okut-alt">Açık ve tamamlanan siparişler</div></div>
          <div class="okut-ok">›</div>
        </a>

        <div class="bolum-baslik">İşlemler</div>
        <a href="/ekle" class="okut-kart okut-mavi">
          <div class="okut-ikon">➕</div>
          <div class="okut-metin"><div class="okut-baslik">Ürün Ekle</div><div class="okut-alt">Yeni ürün kaydı oluştur</div></div>
          <div class="okut-ok">›</div>
        </a>
        <a href="/toplu_yukle" class="okut-kart okut-turkuaz">
          <div class="okut-ikon">📥</div>
          <div class="okut-metin"><div class="okut-baslik">Excel'den Toplu Yükle</div><div class="okut-alt">Excel yükle → otomatik barkod → toplu etiket</div></div>
          <div class="okut-ok">›</div>
        </a>
        <a href="/liste" class="okut-kart okut-mor">
          <div class="okut-ikon">📦</div>
          <div class="okut-metin"><div class="okut-baslik">Stok Listesi</div><div class="okut-alt">Ürünleri görüntüle, etiket bas</div></div>
          <div class="okut-ok">›</div>
        </a>
        <a href="/depo_stok" class="okut-kart okut-turkuaz">
          <div class="okut-ikon">🏭</div>
          <div class="okut-metin"><div class="okut-baslik">Depo Stok Durumu</div><div class="okut-alt">Hangi depoda ne kadar ürün var</div></div>
          <div class="okut-ok">›</div>
        </a>
        <a href="/hareketler" class="okut-kart okut-kirmizi">
          <div class="okut-ikon">📊</div>
          <div class="okut-metin"><div class="okut-baslik">Hareketler</div><div class="okut-alt">Tüm giriş/çıkış geçmişi</div></div>
          <div class="okut-ok">›</div>
        </a>

        <div class="bolum-baslik">Raporlar</div>
        <div class="rapor-satir">
          <a href="/rapor/excel" class="rapor-pil">📥 XLSX</a>
          <a href="/rapor/xls" class="rapor-pil">📥 XLS</a>
          <a href="/rapor/csv" class="rapor-pil">📥 CSV</a>
        </div>
        """

    icerik = (
        "<h1>📦 STOK PANEL</h1>"
        + '<h3 class="alt">👤 ' + kullanici + ' (' + rol + ')</h3>'
        + butonlar
    )
    return sayfa(icerik, "Stok Panel")


@app.route("/ekle", methods=["GET", "POST"])
@rol_gerekli("depocu", "patron")
def ekle2():
    on_dolu_barkod = request.args.get("barkod", "")

    if request.method == "POST":
        ad = request.form.get("ad", "").strip()
        if not ad:
            return sayfa('<p class="hata">❌ Ürün adı boş olamaz.</p><a class="btn gri" href="/ekle">⬅ Geri Dön</a>', "Hata")

        try:
            adet = int(request.form.get("adet", "").strip())
        except (TypeError, ValueError):
            return sayfa('<p class="hata">❌ Adet sayısal olmalı.</p><a class="btn gri" href="/ekle">⬅ Geri Dön</a>', "Hata")

        barkod = request.form.get("barkod")
        if not barkod:
            barkod = barkod_uret()

        con = db()
        try:
            with con:
                with con.cursor() as cur:
                    cur.execute("""
                    INSERT INTO urun(ad,cins,ebat,kalinlik,yuzey,sinif,renk,adet,depo,barkod)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        ad,
                        request.form.get("cins", ""),
                        request.form.get("ebat", ""),
                        request.form.get("kalinlik", ""),
                        request.form.get("yuzey", ""),
                        request.form.get("sinif", ""),
                        request.form.get("renk", ""),
                        adet,
                        request.form.get("depo", ""),
                        barkod,
                    ))
                    cur.execute("""
                    INSERT INTO hareket (barkod, ad, tip, adet, kullanici, tarih)
                    VALUES (%s, %s, 'giris', %s, %s, %s)
                    """, (barkod, ad, adet, session.get("kullanici", "Bilinmiyor"), tr_simdi()))
        finally:
            con.close()

        icerik = (
            '<div style="text-align:center;font-size:52px;margin-bottom:4px;">✅</div>'
            + '<h2 style="margin-top:0;">Ürün Kaydedildi</h2>'
            + '<p style="text-align:center;color:var(--muted);margin-top:-8px;"><b style="color:var(--text);">' + ad + '</b></p>'
            + '<div class="kart" style="text-align:center;">'
            + '<span class="rozet">Barkod</span><br><br>'
            + '<b style="font-size:18px;letter-spacing:1px;">' + barkod + '</b><br><br>'
            + '<img src="/barkod/' + barkod + '.png" width="260"><br><br>'
            + '<img src="/qr/' + barkod + '.png" width="140">'
            + '</div>'
            + '<a href="/etiket/' + barkod + '" target="_blank" class="okut-kart okut-mavi">'
            + '<div class="okut-ikon">🖨️</div><div class="okut-metin"><div class="okut-baslik">Etiket Yazdır</div></div><div class="okut-ok">›</div></a>'
            + '<a href="/liste" class="okut-kart okut-mor">'
            + '<div class="okut-ikon">📦</div><div class="okut-metin"><div class="okut-baslik">Stok Listesine Git</div></div><div class="okut-ok">›</div></a>'
            + '<a href="/ekle" class="okut-kart okut-yesil">'
            + '<div class="okut-ikon">➕</div><div class="okut-metin"><div class="okut-baslik">Yeni Ürün Ekle</div></div><div class="okut-ok">›</div></a>'
        )
        return sayfa(icerik, "Ürün Kaydedildi")

    icerik = """
    <h2 style="margin-bottom:2px;">➕ Ürün Ekle</h2>
    <p style="text-align:center;color:var(--muted);margin-top:0;">Yeni ürün bilgilerini gir</p>

    {% if on_dolu_barkod %}
    <div class="sonuc-kart sonuc-yeni" style="margin-bottom:4px;">
      📷 Okutulan barkod: <b>{{on_dolu_barkod}}</b> — bu ürün stokta yok, yeni ürün olarak ekleyin.
    </div>
    {% endif %}

    <form method="post">
    <div class="kart">
    <label>Barkod</label>
    <input name="barkod" value="{{on_dolu_barkod}}" placeholder="Boş bırak = otomatik barkod">
    <label>Ürün Adı</label>
    <input name="ad" placeholder="Ürün Adı" required>
    </div>

    <div class="kart">
    <label>Cins</label>
    <input name="cins" placeholder="Cins">
    <label>Ebat</label>
    <input name="ebat" placeholder="Ebat">
    <label>Kalınlık</label>
    <input name="kalinlik" placeholder="Kalınlık">
    <label>Yüzey</label>
    <select name="yuzey" required>
        <option value="">Seçiniz</option>
        <option value="HG">HG</option>
        <option value="MAT">MAT</option>
    </select>
    <label>Sınıf</label>
    <input name="sinif" placeholder="Sınıf">
    <label>Renk</label>
    <input name="renk" placeholder="Renk">
    </div>

    <div class="kart">
    <label>Adet</label>
    <input name="adet" type="number" placeholder="Adet" required>
    <label>Depo</label>
    <select name="depo">
    {% for d in depolar %}
    <option>{{d}}</option>
    {% endfor %}
    </select>
    <button class="btn mavi">Kaydet</button>
    </form>
    """
    return render_template_string(sayfa(icerik, "Ürün Ekle"), depolar=DEPOLAR, on_dolu_barkod=on_dolu_barkod)


# ============ TOPLU EXCEL YÜKLEME ============
# Excel şablonu: Ad | Cins | Ebat | Adet | Depo  (Barkod otomatik üretilir)
TOPLU_SABLON_BASLIKLAR = ["Ad", "Cins", "Ebat", "Adet", "Depo"]


@app.route("/toplu_sablon.xlsx")
@rol_gerekli("muhasebeci")
def toplu_sablon():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "Ürünler"
    ws.append(TOPLU_SABLON_BASLIKLAR)
    for c in ws[1]:
        c.font = Font(name="Arial", bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="2196F3")
    ws.append(["Örnek MDF Levha", "MDF", "210x280", 10, DEPOLAR[0]])
    for col_cells in ws.columns:
        uzunluk = max((len(str(c.value)) if c.value is not None else 0) for c in col_cells)
        ws.column_dimensions[col_cells[0].column_letter].width = min(max(uzunluk + 2, 10), 40)

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    return send_file(
        bio,
        as_attachment=True,
        download_name="toplu_urun_sablonu.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/toplu_yukle", methods=["GET", "POST"])
@rol_gerekli("muhasebeci")
def toplu_yukle():
    if request.method == "POST":
        dosya = request.files.get("dosya")
        if not dosya or dosya.filename == "":
            return sayfa('<p class="hata">❌ Dosya seçilmedi.</p><a class="btn gri" href="/toplu_yukle">⬅ Geri Dön</a>', "Hata")

        from openpyxl import load_workbook
        try:
            wb = load_workbook(dosya, data_only=True)
        except Exception:
            return sayfa('<p class="hata">❌ Dosya okunamadı. Geçerli bir .xlsx dosyası yükleyin.</p><a class="btn gri" href="/toplu_yukle">⬅ Geri Dön</a>', "Hata")

        ws = wb.active
        satirlar = list(ws.iter_rows(values_only=True))
        if not satirlar:
            return sayfa('<p class="hata">❌ Excel dosyası boş.</p><a class="btn gri" href="/toplu_yukle">⬅ Geri Dön</a>', "Hata")

        baslik_satiri = [str(h).strip().lower() if h is not None else "" for h in satirlar[0]]

        def sutun_bul(*adaylar):
            for aday in adaylar:
                if aday in baslik_satiri:
                    return baslik_satiri.index(aday)
            return None

        idx_ad = sutun_bul("ad", "ürün adı", "urun adi", "ürün", "urun")
        idx_cins = sutun_bul("cins")
        idx_ebat = sutun_bul("ebat")
        idx_adet = sutun_bul("adet")
        idx_depo = sutun_bul("depo")

        if idx_ad is None or idx_adet is None:
            return sayfa(
                '<p class="hata">❌ Excel\'de en az "Ad" ve "Adet" sütunları olmalı.</p>'
                '<p style="text-align:center;color:var(--muted);font-size:13px;">Beklenen sütunlar: Ad, Cins, Ebat, Adet, Depo</p>'
                '<a class="btn gri" href="/toplu_yukle">⬅ Geri Dön</a>', "Hata")

        eklenenler = []
        hatalar = []

        con = db()
        try:
            with con:
                with con.cursor() as cur:
                    for satir_no, satir in enumerate(satirlar[1:], start=2):
                        if satir is None or all(h is None or str(h).strip() == "" for h in satir):
                            continue

                        def deger_al(idx):
                            if idx is None or idx >= len(satir):
                                return ""
                            v = satir[idx]
                            return str(v).strip() if v is not None else ""

                        ad = deger_al(idx_ad)
                        cins = deger_al(idx_cins)
                        ebat = deger_al(idx_ebat)
                        depo = deger_al(idx_depo)
                        adet_ham = deger_al(idx_adet)

                        if not ad:
                            hatalar.append(f"Satır {satir_no}: Ürün adı boş, atlandı.")
                            continue

                        try:
                            adet = int(float(adet_ham)) if adet_ham != "" else 0
                        except (TypeError, ValueError):
                            hatalar.append(f"Satır {satir_no}: '{ad}' — Adet sayısal değil, atlandı.")
                            continue

                        barkod = barkod_uret()

                        cur.execute("""
                        INSERT INTO urun(ad,cins,ebat,kalinlik,yuzey,sinif,renk,adet,depo,barkod)
                        VALUES(%s,%s,%s,'', '', '', '', %s,%s,%s)
                        """, (ad, cins, ebat, adet, depo, barkod))
                        cur.execute("""
                        INSERT INTO hareket (barkod, ad, tip, adet, kullanici, tarih)
                        VALUES (%s, %s, 'giris', %s, %s, %s)
                        """, (barkod, ad, adet, session.get("kullanici", "Bilinmiyor"), tr_simdi()))

                        eklenenler.append((ad, barkod, adet))
        finally:
            con.close()

        if not eklenenler:
            hata_html = "".join(f'<div class="on-izleme-hata">{h}</div>' for h in hatalar) or "<p>Eklenecek geçerli satır bulunamadı.</p>"
            return sayfa(
                '<p class="hata">❌ Hiçbir ürün eklenemedi.</p>'
                + f'<div class="kart">{hata_html}</div>'
                + '<a class="btn gri" href="/toplu_yukle">⬅ Geri Dön</a>', "Hata")

        satir_html = "".join(
            f'<div class="on-izleme-satir"><span>{ad}</span><span style="color:var(--muted);">{barkod} · {adet} adet</span></div>'
            for ad, barkod, adet in eklenenler
        )
        hata_html = ""
        if hatalar:
            hata_html = '<div class="kart"><b style="color:#FFB74D;">⚠️ Atlanan satırlar</b>' \
                        + "".join(f'<div class="on-izleme-hata">{h}</div>' for h in hatalar) + '</div>'

        barkod_inputlari = "".join(f'<input type="hidden" name="barkod" value="{b}">' for _, b, _ in eklenenler)

        icerik = (
            '<div style="text-align:center;font-size:52px;margin-bottom:4px;">✅</div>'
            + f'<h2 style="margin-top:0;">{len(eklenenler)} Ürün Eklendi</h2>'
            + f'<div class="kart" style="padding:6px 16px;">{satir_html}</div>'
            + hata_html
            + f"""
            <form method="post" action="/etiketler" target="_blank">
              {barkod_inputlari}
              <button class="btn turkuaz" type="submit">🖨️ {len(eklenenler)} Ürünün Etiketini Tek Sayfada Yazdır</button>
            </form>
            """
            + '<a href="/liste" class="okut-kart okut-mor">'
            + '<div class="okut-ikon">📦</div><div class="okut-metin"><div class="okut-baslik">Stok Listesine Git</div></div><div class="okut-ok">›</div></a>'
            + '<a href="/toplu_yukle" class="okut-kart okut-turkuaz">'
            + '<div class="okut-ikon">📥</div><div class="okut-metin"><div class="okut-baslik">Yeni Dosya Yükle</div></div><div class="okut-ok">›</div></a>'
        )
        return sayfa(icerik, "Toplu Yükleme Tamamlandı")

    icerik = """
    <h2 style="margin-bottom:2px;">📥 Excel'den Toplu Yükle</h2>
    <p style="text-align:center;color:var(--muted);margin-top:0;">
    Ad, Cins, Ebat, Adet, Depo sütunlu bir Excel (.xlsx) dosyası yükle —
    her satır için otomatik barkod üretilir ve ürünler tek seferde eklenir.
    </p>

    <div class="kart" style="text-align:center;">
      <a class="sablon-link" href="/toplu_sablon.xlsx">📄 Örnek Excel Şablonunu İndir</a>
    </div>

    <form method="post" enctype="multipart/form-data">
    <div class="yukleme-alan">
      <div class="yukleme-ikon">📊</div>
      <p style="margin:6px 0;color:var(--muted);font-size:14px;">.xlsx dosyanı seç</p>
      <input type="file" name="dosya" accept=".xlsx" required>
    </div>
    <button class="btn turkuaz">Yükle ve Ürünleri Ekle</button>
    </form>

    <div class="kart">
      <b style="font-size:13.5px;">📋 Beklenen sütunlar:</b>
      <div style="color:var(--muted);font-size:13px;margin-top:6px;line-height:1.8;">
        <b style="color:var(--text);">Ad</b> (zorunlu) · Cins · Ebat ·
        <b style="color:var(--text);">Adet</b> (zorunlu) · Depo<br>
        Barkod otomatik üretilir, Excel'e barkod yazmana gerek yok.
      </div>
    </div>
    """
    return sayfa(icerik, "Toplu Yükleme")


@app.route("/duzenle/<eski_barkod>", methods=["GET", "POST"])
@rol_gerekli("muhasebeci")
def duzenle(eski_barkod):
    if request.method == "POST":
        ad = request.form.get("ad", "").strip()
        if not ad:
            return sayfa('<p class="hata">❌ Ürün adı boş olamaz.</p><a class="btn gri" href="/duzenle/' + eski_barkod + '">⬅ Geri Dön</a>', "Hata")

        try:
            adet = int(request.form.get("adet", "").strip())
        except (TypeError, ValueError):
            return sayfa('<p class="hata">❌ Adet sayısal olmalı.</p><a class="btn gri" href="/duzenle/' + eski_barkod + '">⬅ Geri Dön</a>', "Hata")

        yeni_barkod = request.form.get("barkod", "").strip()
        if not yeni_barkod:
            yeni_barkod = eski_barkod

        con = db()
        try:
            with con:
                with con.cursor() as cur:
                    if yeni_barkod != eski_barkod:
                        cur.execute("SELECT id FROM urun WHERE barkod=%s", (yeni_barkod,))
                        if cur.fetchone():
                            con.close()
                            return sayfa(
                                '<p class="hata">❌ Bu barkod zaten başka bir üründe kullanılıyor.</p>'
                                '<a class="btn gri" href="/duzenle/' + eski_barkod + '">⬅ Geri Dön</a>',
                                "Hata"
                            )
                    cur.execute("""
                        UPDATE urun
                        SET ad=%s, cins=%s, ebat=%s, kalinlik=%s, yuzey=%s, sinif=%s, renk=%s, adet=%s, depo=%s, barkod=%s
                        WHERE barkod=%s
                    """, (
                        ad,
                        request.form.get("cins", ""),
                        request.form.get("ebat", ""),
                        request.form.get("kalinlik", ""),
                        request.form.get("yuzey", ""),
                        request.form.get("sinif", ""),
                        request.form.get("renk", ""),
                        adet,
                        request.form.get("depo", ""),
                        yeni_barkod,
                        eski_barkod,
                    ))
        finally:
            con.close()

        icerik = (
            '<div style="text-align:center;font-size:52px;margin-bottom:4px;">✅</div>'
            + '<h2 style="margin-top:0;">Ürün Güncellendi</h2>'
            + '<p style="text-align:center;color:var(--muted);margin-top:-8px;"><b style="color:var(--text);">' + ad + '</b></p>'
            + '<div class="kart" style="text-align:center;">'
            + '<span class="rozet">Barkod</span><br><br>'
            + '<b style="font-size:18px;letter-spacing:1px;">' + yeni_barkod + '</b><br><br>'
            + '<img src="/barkod/' + yeni_barkod + '.png" width="260"><br><br>'
            + '<img src="/qr/' + yeni_barkod + '.png" width="140">'
            + '</div>'
            + (
                '<div class="sonuc-kart sonuc-yeni">📌 Barkod değişti. Üründe önceden yapıştırılmış eski etiket varsa, üzerinde artık eski barkod yazıyor olacak — yeni etiket basmayı unutma.</div>'
                if yeni_barkod != eski_barkod else ''
            )
            + '<a href="/etiket/' + yeni_barkod + '" target="_blank" class="okut-kart okut-mavi">'
            + '<div class="okut-ikon">🖨️</div><div class="okut-metin"><div class="okut-baslik">Etiket Yazdır</div></div><div class="okut-ok">›</div></a>'
            + '<a href="/liste" class="okut-kart okut-mor">'
            + '<div class="okut-ikon">📦</div><div class="okut-metin"><div class="okut-baslik">Stok Listesine Git</div></div><div class="okut-ok">›</div></a>'
        )
        return sayfa(icerik, "Ürün Güncellendi")

    con = db()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT ad,cins,ebat,kalinlik,yuzey,sinif,renk,adet,depo,barkod FROM urun WHERE barkod=%s", (eski_barkod,))
            row = cur.fetchone()
    finally:
        con.close()

    if not row:
        return sayfa('<p class="hata">❌ Ürün bulunamadı.</p><a class="btn gri" href="/liste">⬅ Stok Listesine Dön</a>', "Hata")

    ad, cins, ebat, kalinlik, yuzey, sinif, renk, adet, depo, barkod = row

    icerik = """
    <h2 style="margin-bottom:2px;">✏️ Ürün Düzenle</h2>
    <p style="text-align:center;color:var(--muted);margin-top:0;">{{ad}}</p>

    <div class="sonuc-kart sonuc-yeni">
      📌 Ürün gerçek hayatta zaten üstünde barkod ile mi geldi? Aşağıdaki
      <b>Barkod</b> alanına o barkodu yazıp kaydedersen, sistemdeki barkod
      onunla değişir ve bundan sonra taradığında direkt bu ürünü bulur.
    </div>

    <form method="post">
    <div class="kart">
    <label>Barkod</label>
    <input name="barkod" value="{{barkod}}">
    <label>Ürün Adı</label>
    <input name="ad" value="{{ad}}" placeholder="Ürün Adı" required>
    </div>

    <div class="kart">
    <label>Cins</label>
    <input name="cins" value="{{cins or ''}}" placeholder="Cins">
    <label>Ebat</label>
    <input name="ebat" value="{{ebat or ''}}" placeholder="Ebat">
    <label>Kalınlık</label>
    <input name="kalinlik" value="{{kalinlik or ''}}" placeholder="Kalınlık">
    <label>Yüzey</label>
    <select name="yuzey" required>
        <option value="">Seçiniz</option>
        <option value="HG" {{ 'selected' if yuzey=='HG' else '' }}>HG</option>
        <option value="MAT" {{ 'selected' if yuzey=='MAT' else '' }}>MAT</option>
    </select>
    <label>Sınıf</label>
    <input name="sinif" value="{{sinif or ''}}" placeholder="Sınıf">
    <label>Renk</label>
    <input name="renk" value="{{renk or ''}}" placeholder="Renk">
    </div>

    <div class="kart">
    <label>Adet</label>
    <input name="adet" type="number" value="{{adet}}" placeholder="Adet" required>
    <label>Depo</label>
    <select name="depo">
    {% for d in depolar %}
    <option {{ 'selected' if d==depo else '' }}>{{d}}</option>
    {% endfor %}
    </select>
    <button class="btn mavi">Kaydet</button>
    </div>
    </form>

    <p style="text-align:center;margin-top:10px;">
    <a href="/liste" style="color:var(--muted);text-decoration:none;">⬅ Kaydetmeden Geri Dön</a>
    </p>
    """
    return render_template_string(
        sayfa(icerik, "Ürün Düzenle"),
        ad=ad, cins=cins, ebat=ebat, kalinlik=kalinlik, yuzey=yuzey,
        sinif=sinif, renk=renk, adet=adet, depo=depo, barkod=barkod, depolar=DEPOLAR
    )


@app.route("/liste")
@rol_gerekli("muhasebeci")
def liste():
    depo_filtre = request.args.get("depo", "")

    con = db()
    try:
        with con.cursor() as cur:
            if depo_filtre:
                cur.execute("SELECT * FROM urun WHERE depo=%s ORDER BY ad", (depo_filtre,))
            else:
                cur.execute("SELECT * FROM urun ORDER BY ad")
            urunler = cur.fetchall()
    finally:
        con.close()

    KRITIK_ESIK = 5
    toplam_urun = len(urunler)
    toplam_adet = sum(u[8] for u in urunler)
    kritik_sayisi = sum(1 for u in urunler if u[8] <= KRITIK_ESIK)

    filtre_html = '<div class="filtre-satir">'
    filtre_html += f'<a href="/liste" class="filtre-cip {"aktif" if not depo_filtre else ""}" style="text-decoration:none;display:block;">Tümü</a>'
    for d in DEPOLAR:
        aktif = "aktif" if depo_filtre == d else ""
        filtre_html += f'<a href="/liste?depo={d}" class="filtre-cip {aktif}" style="text-decoration:none;display:block;">{d.split(" ")[0]}</a>'
    filtre_html += '</div>'

    kartlar = ""
    for u in urunler:
        kritik_mi = u[8] <= KRITIK_ESIK
        ozellikler = " · ".join([x for x in [u[2], u[3], u[4], u[5], u[6], u[7]] if x])
        kartlar += f"""
        <div class='urun-kart {"urun-kritik" if kritik_mi else ""}' id="urun-{u[10]}">
        <label class="etiket-sec-satir">
        <input type="checkbox" class="etiket-sec" value="{u[10]}">
        <span>Etikete ekle</span>
        </label>
        <div class="urun-ust">
          <div class="urun-ad">{u[1]}</div>
          <div class="urun-adet-rozet {'kritik' if kritik_mi else ''}">{u[8]} adet</div>
        </div>
        <div class="urun-ozellik">{ozellikler or '-'}</div>
        <div class="urun-depo">🏭 {u[9]}</div>
        <div class="urun-barkod">🔢 {u[10]}</div>
        <div class="urun-gorseller">
          <img src="/barkod/{u[10]}.png">
          <img src="/qr/{u[10]}.png">
        </div>
        <div class="urun-aksiyonlar">
        <button class="btn-kucuk mavi" onclick="window.location.href='/duzenle/{u[10]}'">✏️ Düzenle</button>
        <button class="btn-kucuk turkuaz" onclick="window.open('/etiket/{u[10]}','_blank')">🖨️ Etiket</button>
        <button class="btn-kucuk kirmizi" onclick="urunSil('{u[10]}')">🗑️ Sil</button>
        </div>
        </div>
        """

    icerik = (
        "<h2>📦 STOK</h2>"
        + f"""
        <div class="ozet-satir" style="margin-bottom:14px;">
          <div class="ozet-kutu"><div class="ozet-sayi">{toplam_urun}</div><div class="ozet-etiket">Ürün Çeşidi</div></div>
          <div class="ozet-kutu"><div class="ozet-sayi">{toplam_adet}</div><div class="ozet-etiket">Toplam Adet</div></div>
          <div class="ozet-kutu ozet-turuncu"><div class="ozet-sayi">{kritik_sayisi}</div><div class="ozet-etiket">Kritik Stok</div></div>
        </div>
        """
        + '<div style="text-align:right;margin:-6px 0 10px;"><a href="/depo_stok" style="color:var(--accent);text-decoration:none;font-size:12.5px;font-weight:600;">🏭 Depo Bazlı Özet →</a></div>'
        + filtre_html
        + '<input class="arama" id="arama" placeholder="🔍 Ürün, barkod veya depo ara..." oninput="ara()">'
        + '<div style="display:flex;gap:8px;margin-bottom:14px;">'
        + '<button class="btn-kucuk mavi" style="flex:1;text-align:center;" onclick="tumunuSec()">☑️ Tümünü Seç</button>'
        + '<button class="btn-kucuk gri" style="flex:1;text-align:center;" onclick="secimiTemizle()">✖️ Temizle</button>'
        + '</div>'
        + '<div id="liste">' + kartlar + '</div>'
        + """
        <div id="alt-yazdir-bar" style="display:none;position:fixed;left:0;right:0;bottom:0;z-index:9999;
             padding:12px 16px calc(12px + env(safe-area-inset-bottom));
             background:rgba(18,21,28,.92);backdrop-filter:blur(14px);border-top:1px solid rgba(255,255,255,.08);">
          <button class="btn turkuaz" style="margin:0;max-width:520px;margin:0 auto;" onclick="secilenleriYazdir()">
            🖨️ Seçilenleri Tek Sayfada Yazdır (<span id="secili-sayisi">0</span>)
          </button>
        </div>

        <script>
        function ara(){
          var q = document.getElementById('arama').value.toLocaleLowerCase('tr');
          document.querySelectorAll('#liste .urun-kart').forEach(function(k){
            var metin = k.textContent.toLocaleLowerCase('tr');
            k.style.display = metin.indexOf(q) !== -1 ? '' : 'none';
          });
        }
        function urunSil(barkod){
          if(!confirm('Bu ürünü silmek istediğine emin misin? Bu işlem geri alınamaz.')) return;
          fetch('/sil/' + encodeURIComponent(barkod), { method: 'POST' })
            .then(r => r.json())
            .then(d => {
              if(d.ok){
                var el = document.getElementById('urun-' + barkod);
                if(el) el.remove();
              } else {
                alert('Silinemedi, tekrar dene.');
              }
            });
        }
        function secimSayaciGuncelle(){
          var secililer = document.querySelectorAll('.etiket-sec:checked');
          var bar = document.getElementById('alt-yazdir-bar');
          document.getElementById('secili-sayisi').textContent = secililer.length;
          bar.style.display = secililer.length > 0 ? 'block' : 'none';
        }
        document.getElementById('liste').addEventListener('change', function(e){
          if(e.target.classList.contains('etiket-sec')) secimSayaciGuncelle();
        });
        function tumunuSec(){
          document.querySelectorAll('#liste .urun-kart').forEach(function(k){
            if(k.style.display !== 'none'){
              var kutu = k.querySelector('.etiket-sec');
              if(kutu) kutu.checked = true;
            }
          });
          secimSayaciGuncelle();
        }
        function secimiTemizle(){
          document.querySelectorAll('.etiket-sec').forEach(k => k.checked = false);
          secimSayaciGuncelle();
        }
        function secilenleriYazdir(){
          var barkodlar = Array.from(document.querySelectorAll('.etiket-sec:checked')).map(k => k.value);
          if(barkodlar.length === 0) return;
          var form = document.createElement('form');
          form.method = 'POST';
          form.action = '/etiketler';
          form.target = '_blank';
          barkodlar.forEach(function(b){
            var girdi = document.createElement('input');
            girdi.type = 'hidden';
            girdi.name = 'barkod';
            girdi.value = b;
            form.appendChild(girdi);
          });
          document.body.appendChild(form);
          form.submit();
          document.body.removeChild(form);
        }
        </script>
        """
    )
    return sayfa(icerik, "Stok Listesi")


@app.route("/depo_stok")
@rol_gerekli("depocu", "muhasebeci", "patron")
def depo_stok():
    con = db()
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT depo, COUNT(*) AS cesit, COALESCE(SUM(adet),0) AS toplam
                FROM urun GROUP BY depo
            """)
            satirlar = dict((r[0] or "Depo Belirtilmemiş", (r[1], r[2])) for r in cur.fetchall())
    finally:
        con.close()

    genel_toplam = sum(v[1] for v in satirlar.values())
    genel_cesit = sum(v[0] for v in satirlar.values())

    kartlar = ""
    sirali_depolar = list(DEPOLAR) + [d for d in satirlar if d not in DEPOLAR]
    for d in sirali_depolar:
        cesit, toplam = satirlar.get(d, (0, 0))
        kartlar += f"""
        <a href="/liste?depo={d}" class="depo-ozet-kart" style="text-decoration:none;color:white;">
          <div class="depo-ozet-ad">🏭 {d}</div>
          <div class="depo-ozet-sayilar">
            <div class="depo-ozet-tekli"><div class="sayi">{cesit}</div><div class="etiket">Çeşit</div></div>
            <div class="depo-ozet-tekli"><div class="sayi">{toplam}</div><div class="etiket">Adet</div></div>
          </div>
        </a>
        """

    icerik = (
        "<h2>🏭 DEPO STOK DURUMU</h2>"
        + f"""
        <div class="ozet-satir" style="margin-bottom:6px;">
          <div class="ozet-kutu"><div class="ozet-sayi">{len(sirali_depolar)}</div><div class="ozet-etiket">Depo</div></div>
          <div class="ozet-kutu"><div class="ozet-sayi">{genel_cesit}</div><div class="ozet-etiket">Ürün Çeşidi</div></div>
          <div class="ozet-kutu"><div class="ozet-sayi">{genel_toplam}</div><div class="ozet-etiket">Toplam Adet</div></div>
        </div>
        """
        + '<p style="text-align:center;color:var(--muted);font-size:12.5px;margin-top:0;">Bir depoya dokunarak o depodaki ürünleri görebilirsin.</p>'
        + kartlar
    )
    return sayfa(icerik, "Depo Stok Durumu")


@app.route("/hareketler")
@rol_gerekli("muhasebeci")
def hareket_listesi():
    con = db()
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT h.ad, h.barkod, h.tip, h.adet, h.kullanici, h.tarih,
                       u.cins, u.sinif, u.yuzey, u.renk, u.ebat, u.depo
                FROM hareket h
                LEFT JOIN urun u ON u.barkod = h.barkod
                ORDER BY h.id DESC
            """)
            kayitlar = cur.fetchall()
    finally:
        con.close()

    kartlar = ""
    for ad, barkod, tip, adet, kullanici, tarih, cins, sinif, yuzey, renk, ebat, depo in kayitlar:
        ozellikler = " · ".join([x for x in [cins, sinif, yuzey, renk, ebat] if x])
        giris_mi = tip == "giris"
        kartlar += f"""
        <div class="hareket-kart {'hareket-giris' if giris_mi else 'hareket-cikis'}" data-tip="{tip}">
          <div class="hareket-ikon">{'⬆️' if giris_mi else '⬇️'}</div>
          <div class="hareket-govde">
            <div class="hareket-ust">
              <div class="hareket-ad">{ad}</div>
              <div class="hareket-adet {'giris' if giris_mi else 'cikis'}">{'+' if giris_mi else '-'}{adet}</div>
            </div>
            <div class="hareket-detay">{ozellikler or '-'}{(' · 🏭 ' + depo) if depo else ''}</div>
            <div class="hareket-alt">🔢 {barkod} &nbsp;·&nbsp; 👤 {kullanici} &nbsp;·&nbsp; 🕒 {tarih}</div>
          </div>
        </div>
        """

    icerik = (
        "<h2>📊 TÜM HAREKETLER</h2>"
        + '<input class="arama" id="arama" placeholder="🔍 Ürün, barkod veya kullanıcı ara..." oninput="ara()">'
        + """
        <div class="filtre-satir">
          <button class="filtre-cip aktif" data-filtre="hepsi" onclick="filtrele('hepsi', this)">Tümü</button>
          <button class="filtre-cip" data-filtre="giris" onclick="filtrele('giris', this)">⬆️ Giriş</button>
          <button class="filtre-cip" data-filtre="cikis" onclick="filtrele('cikis', this)">⬇️ Çıkış</button>
        </div>
        """
        + '<div id="hareketler">' + kartlar + '</div>'
        + """
        <script>
        let aktifFiltre = 'hepsi';
        function ara(){
          var q = document.getElementById('arama').value.toLocaleLowerCase('tr');
          uygula(q);
        }
        function filtrele(tip, btn){
          aktifFiltre = tip;
          document.querySelectorAll('.filtre-cip').forEach(c => c.classList.remove('aktif'));
          btn.classList.add('aktif');
          uygula(document.getElementById('arama').value.toLocaleLowerCase('tr'));
        }
        function uygula(q){
          document.querySelectorAll('#hareketler .hareket-kart').forEach(function(k){
            var metinUyar = k.textContent.toLocaleLowerCase('tr').indexOf(q) !== -1;
            var tipUyar = aktifFiltre === 'hepsi' || k.dataset.tip === aktifFiltre;
            k.style.display = (metinUyar && tipUyar) ? '' : 'none';
          });
        }
        </script>
        """
    )
    return sayfa(icerik, "Hareketler")


@app.route("/rapor/excel")
@rol_gerekli("muhasebeci")
def rapor_excel():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()

    ws1 = wb.active
    ws1.title = "Stok"
    basliklar1 = ["Ürün Adı", "Cins", "Ebat", "Kalınlık", "Yüzey", "Sınıf", "Renk", "Adet", "Depo", "Barkod"]
    ws1.append(basliklar1)
    for c in ws1[1]:
        c.font = Font(name="Arial", bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="2196F3")

    con = db()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT ad,cins,ebat,kalinlik,yuzey,sinif,renk,adet,depo,barkod FROM urun")
            urunler = cur.fetchall()
    finally:
        con.close()
    for satir in urunler:
        ws1.append(list(satir))
    for row_cells in ws1.iter_rows(min_row=2):
        for cell in row_cells:
            cell.font = Font(name="Arial")
    for col_cells in ws1.columns:
        uzunluk = max((len(str(c.value)) if c.value is not None else 0) for c in col_cells)
        ws1.column_dimensions[col_cells[0].column_letter].width = min(max(uzunluk + 2, 10), 40)

    ws2 = wb.create_sheet("Hareketler")
    basliklar2 = ["Ürün Adı", "Barkod", "İşlem", "Adet", "Kullanıcı", "Tarih"]
    ws2.append(basliklar2)
    for c in ws2[1]:
        c.font = Font(name="Arial", bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="2196F3")

    con = db()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT ad,barkod,tip,adet,kullanici,tarih FROM hareket ORDER BY id DESC")
            hareketler = cur.fetchall()
    finally:
        con.close()
    for satir in hareketler:
        ws2.append(list(satir))
    for row_cells in ws2.iter_rows(min_row=2):
        for cell in row_cells:
            cell.font = Font(name="Arial")
    for col_cells in ws2.columns:
        uzunluk = max((len(str(c.value)) if c.value is not None else 0) for c in col_cells)
        ws2.column_dimensions[col_cells[0].column_letter].width = min(max(uzunluk + 2, 10), 30)

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    dosya_adi = f"stok_raporu_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return send_file(
        bio,
        as_attachment=True,
        download_name=dosya_adi,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@app.route("/rapor/xls")
@rol_gerekli("muhasebeci")
def rapor_xls():
    import xlwt

    wb = xlwt.Workbook()
    baslik_stili = xlwt.easyxf(
        "font: bold on, color white; pattern: pattern solid, fore_colour blue;"
    )

    ws1 = wb.add_sheet("Stok")
    basliklar1 = ["Ürün Adı", "Cins", "Ebat", "Kalınlık", "Yüzey", "Sınıf", "Renk", "Adet", "Depo", "Barkod"]
    for col, b in enumerate(basliklar1):
        ws1.write(0, col, b, baslik_stili)

    con = db()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT ad,cins,ebat,kalinlik,yuzey,sinif,renk,adet,depo,barkod FROM urun")
            urunler = cur.fetchall()
    finally:
        con.close()
    for row_idx, satir in enumerate(urunler, start=1):
        for col_idx, deger in enumerate(satir):
            ws1.write(row_idx, col_idx, deger)
    for col_idx in range(len(basliklar1)):
        ws1.col(col_idx).width = 256 * 18

    ws2 = wb.add_sheet("Hareketler")
    basliklar2 = ["Ürün Adı", "Barkod", "İşlem", "Adet", "Kullanıcı", "Tarih"]
    for col, b in enumerate(basliklar2):
        ws2.write(0, col, b, baslik_stili)

    con = db()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT ad,barkod,tip,adet,kullanici,tarih FROM hareket ORDER BY id DESC")
            hareketler = cur.fetchall()
    finally:
        con.close()
    for row_idx, satir in enumerate(hareketler, start=1):
        for col_idx, deger in enumerate(satir):
            ws2.write(row_idx, col_idx, str(deger) if deger is not None else "")
    for col_idx in range(len(basliklar2)):
        ws2.col(col_idx).width = 256 * 18

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    dosya_adi = f"stok_raporu_{datetime.now().strftime('%Y%m%d_%H%M')}.xls"
    return send_file(
        bio,
        as_attachment=True,
        download_name=dosya_adi,
        mimetype="application/vnd.ms-excel",
    )


@app.route("/rapor/csv")
@rol_gerekli("muhasebeci")
def rapor_csv():
    import csv

    si = io.StringIO()
    writer = csv.writer(si, delimiter=";")
    writer.writerow(["Ürün Adı", "Cins", "Ebat", "Kalınlık", "Yüzey", "Sınıf", "Renk", "Adet", "Depo", "Barkod"])

    con = db()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT ad,cins,ebat,kalinlik,yuzey,sinif,renk,adet,depo,barkod FROM urun")
            urunler = cur.fetchall()
    finally:
        con.close()

    # Barkod hücresini ="..." formülü olarak yazıyoruz; aksi halde Excel
    # 12 haneli barkodu sayı sanıp bilimsel gösterime çeviriyor
    # (örn. 1,23457E+11) ve barkod okunmaz hale geliyor.
    for satir in urunler:
        satir = list(satir)
        if satir[9]:
            satir[9] = f'="{satir[9]}"'
        writer.writerow(satir)

    output = io.BytesIO(si.getvalue().encode("utf-8-sig"))
    output.seek(0)

    dosya_adi = f"stok_raporu_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return send_file(
        output,
        as_attachment=True,
        download_name=dosya_adi,
        mimetype="text/csv",
    )


@app.route("/hizli_islem", methods=["POST"])
@rol_gerekli("depocu")
def hizli_islem():
    data = request.get_json()
    barkod = data.get("barkod")
    tip = data.get("tip")
    siparis_id = data.get("siparis_id")
    kullanici = session.get("kullanici", "Bilinmiyor")
    rol = session.get("rol")

    con = db()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute("SELECT id, ad, adet, cins, ebat, yuzey, sinif, renk, depo FROM urun WHERE barkod=%s", (barkod,))
                row = cur.fetchone()

                if not row:
                    if tip == "giris":
                        return jsonify({"ok": False, "yeni": True, "barkod": barkod})
                    return jsonify({"ok": False, "msg": "Bu ürün sizin sattığınız ürünler arasında değil, çıkış yapılamaz"})

                uid, ad, adet, cins, ebat, yuzey, sinif, renk, depo = row

                # ---- Sipariş kontrolü: depocu, açık siparişte olmayan ürünü çıkış yapamaz ----
                kalem_id = None
                if tip == "cikis" and rol == "depocu":
                    if not siparis_id:
                        return jsonify({"ok": False, "msg": "Önce bir sipariş seçmelisin. Sipariş olmadan çıkış yapılamaz."})
                    cur.execute("SELECT durum FROM siparis WHERE id=%s", (siparis_id,))
                    sip = cur.fetchone()
                    if not sip or sip[0] != 'acik':
                        return jsonify({"ok": False, "msg": "Bu sipariş artık açık değil."})
                    cur.execute("SELECT id, istenen, verilen FROM siparis_kalem WHERE siparis_id=%s AND barkod=%s", (siparis_id, barkod))
                    kalem = cur.fetchone()
                    if not kalem:
                        return jsonify({"ok": False, "msg": "⚠️ YANLIŞ ÜRÜN! Bu ürün bu siparişte yok.", "yanlis_urun": True, "urun_adi": ad})
                    kalem_id, istenen, verilen = kalem
                    if verilen >= istenen:
                        return jsonify({"ok": False, "msg": f"'{ad}' için istenen {istenen} adet zaten tamamlandı.", "tamamlandi_uyari": True})

                if tip == "cikis" and adet <= 0:
                    return jsonify({"ok": False, "msg": "Stok yok"})

                if tip == "giris":
                    adet += 1
                else:
                    adet -= 1
                if adet < 0:
                    adet = 0

                cur.execute("UPDATE urun SET adet=%s WHERE id=%s", (adet, uid))
                cur.execute("""
                INSERT INTO hareket (barkod, ad, tip, adet, kullanici, tarih)
                VALUES (%s, %s, %s, %s, %s, %s)
                """, (barkod, ad, tip, 1, kullanici, tr_simdi()))

                siparis_ilerleme = None
                if kalem_id:
                    cur.execute("UPDATE siparis_kalem SET verilen = verilen + 1 WHERE id=%s", (kalem_id,))
                    cur.execute("SELECT SUM(istenen), SUM(verilen) FROM siparis_kalem WHERE siparis_id=%s", (siparis_id,))
                    top_ist, top_ver = cur.fetchone()
                    siparis_ilerleme = {"istenen": top_ist, "verilen": top_ver}
                    if top_ver >= top_ist:
                        cur.execute("UPDATE siparis SET durum='tamamlandi' WHERE id=%s", (siparis_id,))
                        siparis_ilerleme["tamamlandi"] = True

                cur.execute("""
                SELECT SUM(adet) FROM hareket WHERE kullanici=%s AND tip='cikis'
                """, (kullanici,))
                toplam = cur.fetchone()[0]
                if not toplam:
                    toplam = 0

                return jsonify({
                    "ok": True, "ad": ad, "adet": adet, "toplam": toplam,
                    "cins": cins, "ebat": ebat, "yuzey": yuzey, "sinif": sinif,
                    "renk": renk, "depo": depo, "siparis_ilerleme": siparis_ilerleme,
                })
    finally:
        con.close()


@app.route("/sil/<barkod>", methods=["POST"])
@rol_gerekli("muhasebeci")
def urun_sil(barkod):
    con = db()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute("DELETE FROM urun WHERE barkod=%s", (barkod,))
                silindi = cur.rowcount > 0
    finally:
        con.close()
    return jsonify({"ok": silindi})


@app.route("/etiket/<barkod>")
@rol_gerekli("muhasebeci")
def etiket(barkod):
    con = db()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT ad,cins,ebat,kalinlik,yuzey,sinif,renk,depo FROM urun WHERE barkod=%s", (barkod,))
            row = cur.fetchone()
    finally:
        con.close()

    if not row:
        return sayfa('<p class="hata">❌ Ürün bulunamadı.</p><a class="btn gri" href="/liste">⬅ Geri Dön</a>', "Hata")

    ad, cins, ebat, kalinlik, yuzey, sinif, renk, depo = row

    ozellikler = " · ".join([x for x in [cins, ebat, kalinlik, yuzey, sinif, renk] if x])

    html = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
    <meta charset="utf-8">
    <title>Etiket - {ad}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        @page {{ size: 40mm 58mm; margin: 2mm; }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: Arial, sans-serif; margin:0; padding:0;
            background:#fff; color:#000;
        }}
        .etiket {{
            width: 36mm; padding: 1.5mm; text-align:center; margin:0 auto;
        }}
        .ad {{ font-size: 11px; font-weight:800; margin-bottom:1mm; line-height:1.15; }}
        .ozellik {{ font-size: 7.5px; color:#333; margin-bottom:1mm; line-height:1.25; }}
        .depo {{ font-size: 7.5px; color:#555; margin-bottom:1mm; }}
        img.barkod {{ width: 100%; max-width: 34mm; }}
        img.qr {{ width: 13mm; margin-top:1mm; }}
        .yazdir-btn {{
            display:block; margin: 6mm auto 0; padding:14px 24px;
            background:#2196F3; color:white; border:none; border-radius:10px;
            font-size:16px; font-weight:700; cursor:pointer;
        }}
        @media print {{
            .yazdir-btn {{ display:none; }}
            body {{ margin:0; }}
        }}
    </style>
    </head>
    <body>
        <div class="etiket">
            <div class="ad">{ad}</div>
            <div class="ozellik">{ozellikler}</div>
            {'<div class="depo">🏭 ' + depo + '</div>' if depo else ''}
            <img class="barkod" src="/barkod/{barkod}.png">
            <img class="qr" src="/qr/{barkod}.png">
        </div>
        <button class="yazdir-btn" onclick="window.print()">🖨️ Yazdır</button>
    </body>
    </html>
    """
    return html


@app.route("/etiketler", methods=["GET", "POST"])
@rol_gerekli("muhasebeci")
def etiketler():
    if request.method == "POST":
        barkodlar = [b.strip() for b in request.form.getlist("barkod") if b.strip()]
    else:
        barkod_param = request.args.get("barkodlar", "")
        barkodlar = [b.strip() for b in barkod_param.split(",") if b.strip()]

    if not barkodlar:
        return sayfa('<p class="hata">❌ Etiket için ürün seçilmedi.</p><a class="btn gri" href="/liste">⬅ Stok Listesine Dön</a>', "Hata")

    con = db()
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT ad,cins,ebat,kalinlik,yuzey,sinif,renk,depo,barkod
                FROM urun WHERE barkod = ANY(%s)
            """, (barkodlar,))
            satirlar = cur.fetchall()
    finally:
        con.close()

    sirali = {s[8]: s for s in satirlar}
    satirlar = [sirali[b] for b in barkodlar if b in sirali]

    if not satirlar:
        return sayfa('<p class="hata">❌ Seçilen ürünler bulunamadı.</p><a class="btn gri" href="/liste">⬅ Stok Listesine Dön</a>', "Hata")

    etiket_html = ""
    for ad, cins, ebat, kalinlik, yuzey, sinif, renk, depo, barkod in satirlar:
        ozellikler = " · ".join([x for x in [cins, ebat, kalinlik, yuzey, sinif, renk] if x])
        etiket_html += f"""
        <div class="etiket">
            <div class="ad">{ad}</div>
            <div class="ozellik">{ozellikler}</div>
            {'<div class="depo">🏭 ' + depo + '</div>' if depo else ''}
            <img class="barkod" src="/barkod/{barkod}.png">
            <img class="qr" src="/qr/{barkod}.png">
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html lang="tr">
    <head>
    <meta charset="utf-8">
    <title>Etiketler ({len(satirlar)} adet)</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        @page {{ size: 40mm 58mm; margin: 2mm; }}
        * {{ box-sizing: border-box; }}
        body {{
            font-family: Arial, sans-serif; margin:0; padding:0;
            background:#e9e9e9; color:#000;
        }}
        .sayfa-ic {{
            max-width: 500px; margin: 0 auto; padding: 16px;
        }}
        .ust-arac {{
            display:flex; justify-content:center; gap:10px; margin-bottom:16px;
        }}
        .yazdir-btn, .geri-btn {{
            padding:14px 24px; border:none; border-radius:10px;
            font-size:16px; font-weight:700; cursor:pointer; text-decoration:none;
            display:inline-block;
        }}
        .yazdir-btn {{ background:#2196F3; color:white; }}
        .geri-btn {{ background:#555; color:white; }}
        .izgara {{
            display: flex; flex-direction: column; gap: 4mm;
        }}
        .etiket {{
            width: 36mm; margin: 0 auto;
            border: 1px dashed #bbb;
            padding: 1.5mm; text-align:center;
            background: white;
            page-break-after: always;
            break-after: page;
        }}
        .etiket:last-child {{ page-break-after: auto; break-after: auto; }}
        .ad {{ font-size: 11px; font-weight:800; margin-bottom:1mm; line-height:1.15; }}
        .ozellik {{ font-size: 7.5px; color:#333; margin-bottom:1mm; line-height:1.25; }}
        .depo {{ font-size: 7.5px; color:#555; margin-bottom:1mm; }}
        img.barkod {{ width: 100%; max-width: 34mm; }}
        img.qr {{ width: 13mm; margin-top:1mm; }}
        @media print {{
            .ust-arac {{ display:none; }}
            body {{ background:white; margin:0; }}
            .sayfa-ic {{ max-width:none; padding:0; }}
            .etiket {{ border: none; }}
        }}
    </style>
    </head>
    <body>
        <div class="sayfa-ic">
            <div class="ust-arac">
                <button class="yazdir-btn" onclick="window.print()">🖨️ Sayfayı Yazdır ({len(satirlar)} etiket)</button>
                <a class="geri-btn" href="/liste">⬅ Listeye Dön</a>
            </div>
            <div class="izgara">
                {etiket_html}
            </div>
        </div>
    </body>
    </html>
    """
    return html


@app.route("/geri_al", methods=["POST"])
@rol_gerekli("depocu")
def geri_al():
    data = request.get_json()
    barkod = data.get("barkod")
    tip = data.get("tip")
    siparis_id = data.get("siparis_id")

    con = db()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute("SELECT id, adet FROM urun WHERE barkod=%s", (barkod,))
                row = cur.fetchone()
                if not row:
                    return jsonify({"ok": False})

                uid, adet = row
                if tip == "giris":
                    adet -= 1
                else:
                    adet += 1
                if adet < 0:
                    adet = 0

                cur.execute("UPDATE urun SET adet=%s WHERE id=%s", (adet, uid))

                if tip == "cikis" and siparis_id:
                    cur.execute("""
                        UPDATE siparis_kalem SET verilen = GREATEST(verilen - 1, 0)
                        WHERE siparis_id=%s AND barkod=%s
                    """, (siparis_id, barkod))
                    cur.execute("UPDATE siparis SET durum='acik' WHERE id=%s AND durum='tamamlandi'", (siparis_id,))
    finally:
        con.close()

    return jsonify({"ok": True})


# ============ SİPARİŞ SİSTEMİ ============

def siparis_tablolarini_olustur():
    con = db()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute("""
                CREATE TABLE IF NOT EXISTS siparis(
                    id SERIAL PRIMARY KEY,
                    musteri TEXT,
                    depo TEXT,
                    durum TEXT DEFAULT 'acik',
                    olusturan TEXT,
                    tarih TIMESTAMP,
                    aciklama TEXT
                )
                """)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS siparis_kalem(
                    id SERIAL PRIMARY KEY,
                    siparis_id INTEGER REFERENCES siparis(id) ON DELETE CASCADE,
                    barkod TEXT,
                    ad TEXT,
                    istenen INTEGER,
                    verilen INTEGER DEFAULT 0
                )
                """)
    finally:
        con.close()


if DATABASE_URL:
    siparis_tablolarini_olustur()


@app.route("/urun_ara")
@rol_gerekli("muhasebeci")
def urun_ara():
    q = request.args.get("q", "").strip()
    if len(q) < 1:
        return jsonify([])
    con = db()
    try:
        with con.cursor() as cur:
            cur.execute("""
                SELECT ad, barkod, adet, depo, cins, ebat FROM urun
                WHERE ad ILIKE %s OR barkod ILIKE %s
                ORDER BY ad LIMIT 20
            """, (f"%{q}%", f"%{q}%"))
            satirlar = cur.fetchall()
    finally:
        con.close()
    return jsonify([
        {"ad": s[0], "barkod": s[1], "adet": s[2], "depo": s[3] or "", "cins": s[4] or "", "ebat": s[5] or ""}
        for s in satirlar
    ])


@app.route("/siparis_olustur", methods=["GET", "POST"])
@rol_gerekli("muhasebeci")
def siparis_olustur():
    if request.method == "POST":
        musteri = request.form.get("musteri", "").strip()
        depo = request.form.get("depo", "")
        aciklama = request.form.get("aciklama", "").strip()
        barkodlar = request.form.getlist("kalem_barkod")
        adlar = request.form.getlist("kalem_ad")
        adetler = request.form.getlist("kalem_adet")

        kalemler = []
        for b, a, adet_str in zip(barkodlar, adlar, adetler):
            b = b.strip()
            if not b:
                continue
            try:
                adet = int(adet_str)
            except (TypeError, ValueError):
                adet = 0
            if adet <= 0:
                continue
            kalemler.append((b, a, adet))

        if not kalemler:
            return sayfa('<p class="hata">❌ En az bir ürün ve adet girmelisin.</p><a class="btn gri" href="/siparis_olustur">⬅ Geri Dön</a>', "Hata")

        con = db()
        try:
            with con:
                with con.cursor() as cur:
                    cur.execute("""
                        INSERT INTO siparis (musteri, depo, durum, olusturan, tarih, aciklama)
                        VALUES (%s,%s,'acik',%s,%s,%s) RETURNING id
                    """, (musteri, depo, session.get("kullanici", "Bilinmiyor"), tr_simdi(), aciklama))
                    siparis_id = cur.fetchone()[0]
                    for barkod, ad, adet in kalemler:
                        cur.execute("""
                            INSERT INTO siparis_kalem (siparis_id, barkod, ad, istenen, verilen)
                            VALUES (%s,%s,%s,%s,0)
                        """, (siparis_id, barkod, ad, adet))
        finally:
            con.close()

        return redirect(f"/siparis/{siparis_id}")

    icerik = """
    <h2 style="margin-bottom:2px;">🧾 Yeni Sipariş Oluştur</h2>
    <p style="text-align:center;color:var(--muted);margin-top:0;">
    Depocuya hazırlatılacak ürünleri seç, depocu sadece bu listedeki ürünleri çıkış yapabilir.
    </p>

    <form method="post" id="siparis-form">
    <div class="kart">
    <label>Müşteri / Sipariş Adı (opsiyonel)</label>
    <input name="musteri" placeholder="Örn: Ahmet Bey - Mutfak Dolabı">
    <label>Depo</label>
    <select name="depo" required>
    """ + "".join(f'<option>{d}</option>' for d in DEPOLAR) + """
    </select>
    <label>Not (opsiyonel)</label>
    <input name="aciklama" placeholder="Örn: Bugün teslim edilecek">
    </div>

    <div class="kart">
    <label>Ürün Ara ve Ekle</label>
    <div class="urun-arama-kutu">
      <input type="text" id="urun-arama" class="arama" placeholder="🔍 Ürün adı veya barkod yaz..." autocomplete="off" oninput="urunAra()">
      <div class="urun-arama-sonuc" id="urun-arama-sonuc"></div>
    </div>
    <div id="sepet"></div>
    <p id="sepet-bos" style="color:var(--muted);font-size:13px;text-align:center;margin:10px 0;">Henüz ürün eklenmedi.</p>
    </div>

    <div id="gizli-alanlar"></div>
    <button type="submit" class="btn yesil">✅ Siparişi Oluştur</button>
    </form>

    <script>
    let sepet = {};
    let aramaZamanlayici = null;

    function urunAra(){
      clearTimeout(aramaZamanlayici);
      const q = document.getElementById('urun-arama').value.trim();
      const kutu = document.getElementById('urun-arama-sonuc');
      if(q.length < 1){ kutu.style.display='none'; kutu.innerHTML=''; return; }
      aramaZamanlayici = setTimeout(() => {
        fetch('/urun_ara?q=' + encodeURIComponent(q))
          .then(r => r.json())
          .then(sonuclar => {
            if(sonuclar.length === 0){
              kutu.innerHTML = '<div class="urun-arama-oge" style="color:var(--muted);">Ürün bulunamadı</div>';
              kutu.style.display = 'block';
              return;
            }
            kutu.innerHTML = sonuclar.map(u => `
              <div class="urun-arama-oge" onclick='sepeteEkle(${JSON.stringify(JSON.stringify(u))})'>
                <div class="ad">${u.ad}</div>
                <div class="detay">🔢 ${u.barkod} · 📦 Stokta: ${u.adet} · 🏭 ${u.depo}</div>
              </div>
            `).join('');
            kutu.style.display = 'block';
          });
      }, 250);
    }

    function sepeteEkle(uJson){
      const u = JSON.parse(uJson);
      if(!sepet[u.barkod]){
        sepet[u.barkod] = { ad: u.ad, adet: 1, stok: u.adet };
      } else {
        sepet[u.barkod].adet += 1;
      }
      document.getElementById('urun-arama').value = '';
      document.getElementById('urun-arama-sonuc').style.display = 'none';
      sepetiCiz();
    }

    function sepettenSil(barkod){
      delete sepet[barkod];
      sepetiCiz();
    }

    function adetGuncelle(barkod, deger){
      const adet = parseInt(deger);
      if(sepet[barkod]) sepet[barkod].adet = isNaN(adet) ? 1 : Math.max(1, adet);
    }

    function sepetiCiz(){
      const kapsayici = document.getElementById('sepet');
      const bosMesaj = document.getElementById('sepet-bos');
      const barkodlar = Object.keys(sepet);
      bosMesaj.style.display = barkodlar.length === 0 ? 'block' : 'none';
      kapsayici.innerHTML = barkodlar.map(b => `
        <div class="sepet-satir">
          <div class="sepet-ad">${sepet[b].ad}<br><span style="color:var(--muted);font-size:11px;">🔢 ${b} · Stokta ${sepet[b].stok}</span></div>
          <input type="number" class="sepet-adet-input" min="1" value="${sepet[b].adet}" onchange="adetGuncelle('${b}', this.value)">
          <button type="button" class="sepet-sil" onclick="sepettenSil('${b}')">✕</button>
        </div>
      `).join('');

      const gizli = document.getElementById('gizli-alanlar');
      gizli.innerHTML = barkodlar.map(b => `
        <input type="hidden" name="kalem_barkod" value="${b}">
        <input type="hidden" name="kalem_ad" value="${sepet[b].ad}">
        <input type="hidden" name="kalem_adet" value="${sepet[b].adet}">
      `).join('');
    }

    document.getElementById('siparis-form').addEventListener('submit', function(e){
      if(Object.keys(sepet).length === 0){
        e.preventDefault();
        alert('Lütfen en az bir ürün ekle.');
      }
    });

    document.addEventListener('click', function(e){
      const kutu = document.getElementById('urun-arama-sonuc');
      if(!kutu.contains(e.target) && e.target.id !== 'urun-arama'){
        kutu.style.display = 'none';
      }
    });
    </script>
    """
    return sayfa(icerik, "Yeni Sipariş")


@app.route("/siparisler")
@rol_gerekli("muhasebeci")
def siparisler():
    durum_filtre = request.args.get("durum", "acik")

    con = db()
    try:
        with con.cursor() as cur:
            if durum_filtre == "hepsi":
                cur.execute("""
                    SELECT s.id, s.musteri, s.depo, s.durum, s.olusturan, s.tarih,
                           COALESCE(SUM(k.istenen),0), COALESCE(SUM(k.verilen),0)
                    FROM siparis s LEFT JOIN siparis_kalem k ON k.siparis_id = s.id
                    GROUP BY s.id ORDER BY s.id DESC
                """)
            else:
                cur.execute("""
                    SELECT s.id, s.musteri, s.depo, s.durum, s.olusturan, s.tarih,
                           COALESCE(SUM(k.istenen),0), COALESCE(SUM(k.verilen),0)
                    FROM siparis s LEFT JOIN siparis_kalem k ON k.siparis_id = s.id
                    WHERE s.durum=%s GROUP BY s.id ORDER BY s.id DESC
                """, (durum_filtre,))
            satirlar = cur.fetchall()
    finally:
        con.close()

    kartlar = ""
    for sid, musteri, depo, durum, olusturan, tarih, istenen, verilen in satirlar:
        yuzde = int((verilen / istenen) * 100) if istenen else 0
        kartlar += f"""
        <a href="/siparis/{sid}" class="siparis-kart">
          <div class="siparis-ust">
            <div class="siparis-no">🧾 Sipariş #{sid}{' — ' + musteri if musteri else ''}</div>
            <div class="siparis-durum {durum}">{durum}</div>
          </div>
          <div class="siparis-detay">
            🏭 {depo} &nbsp;·&nbsp; 👤 {olusturan} &nbsp;·&nbsp; 🕒 {tarih}<br>
            📦 {verilen} / {istenen} adet hazırlandı
          </div>
          <div class="siparis-ilerleme-bar"><div class="siparis-ilerleme-dolu" style="width:{yuzde}%;"></div></div>
        </a>
        """

    if not kartlar:
        kartlar = '<p style="text-align:center;color:var(--muted);margin-top:24px;">Bu filtrede sipariş bulunamadı.</p>'

    icerik = (
        "<h2>📋 SİPARİŞLER</h2>"
        + f"""
        <div class="filtre-satir">
          <a href="/siparisler?durum=acik" class="filtre-cip {'aktif' if durum_filtre=='acik' else ''}" style="text-decoration:none;display:block;">Açık</a>
          <a href="/siparisler?durum=tamamlandi" class="filtre-cip {'aktif' if durum_filtre=='tamamlandi' else ''}" style="text-decoration:none;display:block;">Tamamlandı</a>
          <a href="/siparisler?durum=hepsi" class="filtre-cip {'aktif' if durum_filtre=='hepsi' else ''}" style="text-decoration:none;display:block;">Tümü</a>
        </div>
        """
        + '<a href="/siparis_olustur" class="okut-kart okut-yesil"><div class="okut-ikon">➕</div><div class="okut-metin"><div class="okut-baslik">Yeni Sipariş</div></div><div class="okut-ok">›</div></a>'
        + kartlar
    )
    return sayfa(icerik, "Siparişler")


@app.route("/siparis/<int:siparis_id>")
@rol_gerekli("depocu", "muhasebeci", "patron")
def siparis_detay(siparis_id):
    con = db()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT id, musteri, depo, durum, olusturan, tarih, aciklama FROM siparis WHERE id=%s", (siparis_id,))
            sip = cur.fetchone()
            if not sip:
                return sayfa('<p class="hata">❌ Sipariş bulunamadı.</p><a class="btn gri" href="/siparisler">⬅ Geri Dön</a>', "Hata")
            cur.execute("SELECT ad, barkod, istenen, verilen FROM siparis_kalem WHERE siparis_id=%s ORDER BY id", (siparis_id,))
            kalemler = cur.fetchall()
    finally:
        con.close()

    _, musteri, depo, durum, olusturan, tarih, aciklama = sip

    kalem_html = ""
    for ad, barkod, istenen, verilen in kalemler:
        tam = verilen >= istenen
        kalem_html += f"""
        <div class="kalem-satir">
          <div class="kalem-ad">{ad}<br><span style="color:var(--muted);font-size:11.5px;">🔢 {barkod}</span></div>
          <div class="kalem-miktar {'tam' if tam else 'eksik'}">{verilen} / {istenen}</div>
        </div>
        """

    rol = session.get("rol")
    aksiyon_html = ""
    if rol == "depocu" and durum == "acik":
        aksiyon_html = f'<a href="/kamera/cikis?siparis_id={siparis_id}" class="btn turuncu">⬇️ Bu Siparişi Okutarak Hazırla</a>'
    if rol in ("muhasebeci", "patron") and durum == "acik":
        aksiyon_html += f"""
        <form method="post" action="/siparis_iptal/{siparis_id}" onsubmit="return confirm('Bu siparişi iptal etmek istediğine emin misin?');">
          <button class="btn kirmizi" type="submit">🗑️ Siparişi İptal Et</button>
        </form>
        """

    icerik = (
        f"<h2>🧾 Sipariş #{siparis_id}</h2>"
        + f'<h3 class="alt">{musteri or "—"}</h3>'
        + f"""
        <div class="kart">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span class="siparis-durum {durum}">{durum}</span>
            <span style="color:var(--muted);font-size:12.5px;">🏭 {depo}</span>
          </div>
          <div style="color:var(--muted);font-size:12.5px;">👤 {olusturan} &nbsp;·&nbsp; 🕒 {tarih}</div>
          {'<div style="color:var(--muted);font-size:13px;margin-top:8px;">📝 ' + aciklama + '</div>' if aciklama else ''}
        </div>
        <div class="kart" style="padding:6px 16px;">
          <div class="bolum-baslik" style="margin:10px 0 2px;">Ürünler</div>
          {kalem_html}
        </div>
        """
        + aksiyon_html
        + '<a href="/siparisler" class="okut-kart okut-mor"><div class="okut-ikon">📋</div><div class="okut-metin"><div class="okut-baslik">Tüm Siparişlere Dön</div></div><div class="okut-ok">›</div></a>'
    )
    return sayfa(icerik, f"Sipariş #{siparis_id}")


@app.route("/siparis_iptal/<int:siparis_id>", methods=["POST"])
@rol_gerekli("muhasebeci")
def siparis_iptal(siparis_id):
    con = db()
    try:
        with con:
            with con.cursor() as cur:
                cur.execute("UPDATE siparis SET durum='iptal' WHERE id=%s", (siparis_id,))
    finally:
        con.close()
    return redirect(f"/siparis/{siparis_id}")


@app.route("/kamera/<tip>")
@rol_gerekli("depocu")
def kamera(tip):
    if tip not in ("giris", "cikis"):
        tip = "giris"
    kullanici = session.get("kullanici", "Bilinmiyor")
    rol = session.get("rol")
    siparis_id = request.args.get("siparis_id", "")

    # Çıkış modunda depocu önce açık bir sipariş seçmeli (yanlış ürün çıkışını engellemek için)
    if tip == "cikis" and rol == "depocu" and not siparis_id:
        con = db()
        try:
            with con.cursor() as cur:
                cur.execute("""
                    SELECT s.id, s.musteri, s.depo, COALESCE(SUM(k.istenen),0), COALESCE(SUM(k.verilen),0)
                    FROM siparis s LEFT JOIN siparis_kalem k ON k.siparis_id = s.id
                    WHERE s.durum='acik' GROUP BY s.id ORDER BY s.id DESC
                """)
                acik_siparisler = cur.fetchall()
        finally:
            con.close()

        kartlar = ""
        for sid, musteri, depo, istenen, verilen in acik_siparisler:
            yuzde = int((verilen / istenen) * 100) if istenen else 0
            kartlar += f"""
            <a href="/kamera/cikis?siparis_id={sid}" class="siparis-kart">
              <div class="siparis-ust">
                <div class="siparis-no">🧾 #{sid}{' — ' + musteri if musteri else ''}</div>
                <div class="siparis-durum acik">açık</div>
              </div>
              <div class="siparis-detay">🏭 {depo} &nbsp;·&nbsp; 📦 {verilen} / {istenen} adet</div>
              <div class="siparis-ilerleme-bar"><div class="siparis-ilerleme-dolu" style="width:{yuzde}%;"></div></div>
            </a>
            """

        if not acik_siparisler:
            kartlar = '<div class="uyari-kutu">⚠️ Şu anda size atanmış açık bir sipariş yok. Çıkış yapmadan önce muhasebeciden bir sipariş oluşturmasını iste.</div>'

        icerik = (
            "<h2>⬇️ Çıkış İçin Sipariş Seç</h2>"
            + '<p style="text-align:center;color:var(--muted);margin-top:0;">Yanlış ürün verilmesini önlemek için önce hangi siparişi hazırladığını seç.</p>'
            + kartlar
        )
        return sayfa(icerik, "Sipariş Seç")

    siparis_bilgi_html = ""
    if tip == "cikis" and siparis_id:
        con = db()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT musteri, depo, durum FROM siparis WHERE id=%s", (siparis_id,))
                sip = cur.fetchone()
                cur.execute("SELECT ad, barkod, istenen, verilen FROM siparis_kalem WHERE siparis_id=%s ORDER BY id", (siparis_id,))
                kalemler = cur.fetchall()
        finally:
            con.close()

        if sip:
            musteri, depo, durum = sip
            kalem_satirlari = "".join(
                f'<div class="kalem-satir"><div class="kalem-ad">{ad}</div><div class="kalem-miktar {"tam" if verilen>=istenen else "eksik"}">{verilen}/{istenen}</div></div>'
                for ad, barkod, istenen, verilen in kalemler
            )
            siparis_bilgi_html = f"""
            <div class="kart" style="padding:12px 16px;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <b>🧾 Sipariş #{siparis_id}{' — ' + musteri if musteri else ''}</b>
                <span class="siparis-durum {durum}">{durum}</span>
              </div>
              <div style="color:var(--muted);font-size:12px;margin:4px 0 8px;">🏭 {depo} — sadece bu listedeki ürünler okutulabilir</div>
              {kalem_satirlari}
            </div>
            """

    icerik = """
    <style>
    .mod-gecis {
      display:flex; background:#12151c; border:1px solid var(--border);
      border-radius:999px; padding:4px; margin-bottom:16px;
    }
    .mod-btn {
      flex:1; text-align:center; padding:12px 8px; border-radius:999px;
      font-weight:700; font-size:14.5px; cursor:pointer; border:none;
      background:transparent; color:var(--muted); transition: all .18s ease;
    }
    .mod-btn.aktif-giris { background: linear-gradient(135deg,#00C853,#64DD17); color:#fff; }
    .mod-btn.aktif-cikis { background: linear-gradient(135deg,#FF6F00,#FF9800); color:#fff; }

    .kamera-cerceve {
      position:relative; border-radius:20px; overflow:hidden; margin-bottom:14px;
      border:2px solid var(--border); background:#000;
      box-shadow: 0 8px 28px rgba(0,0,0,.5);
      aspect-ratio: 4/3;
    }
    .kamera-cerceve video { width:100%; height:100%; object-fit:cover; display:block; }
    .kamera-ustkatman {
      position:absolute; inset:0; pointer-events:none;
      display:flex; align-items:center; justify-content:center;
    }
    .tarama-kutu {
      width:72%; height:42%; border:3px solid rgba(255,255,255,.85);
      border-radius:14px; box-shadow: 0 0 0 999px rgba(0,0,0,.28);
    }
    .kamera-araclar {
      position:absolute; top:10px; right:10px; display:flex; flex-direction:column; gap:8px;
      pointer-events:auto;
    }
    .araç-btn {
      width:42px; height:42px; border-radius:50%; border:none; cursor:pointer;
      background:rgba(0,0,0,.5); color:white; font-size:19px;
      display:flex; align-items:center; justify-content:center;
      backdrop-filter: blur(6px);
    }
    .araç-btn.aktif { background: var(--accent); }
    .kamera-baslat-alan { text-align:center; padding: 40px 10px; }

    .sonuc-kart {
      border-radius: var(--radius); padding:18px; margin: 4px 0 14px;
      border:1px solid var(--border); background: linear-gradient(180deg, var(--card2), var(--card));
      animation: belir .2s ease;
    }
    .sonuc-basari { border-color: rgba(100,221,23,.4); }
    .sonuc-hata { border-color: rgba(255,23,68,.4); }
    .sonuc-yeni { border-color: rgba(33,150,243,.4); }
    .sonuc-yanlis { border-color: rgba(255,23,68,.6); background: linear-gradient(180deg, rgba(255,23,68,.14), var(--card)); }
    .sonuc-ust { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
    .sonuc-ikon { font-size:26px; }
    .sonuc-ad { font-size:17px; font-weight:800; }
    .sonuc-satirlar { font-size:13.5px; color:var(--muted); line-height:1.9; }
    .sonuc-satirlar b { color: var(--text); font-weight:600; }

    .geri-al-btn {
      display:block; width:100%; text-align:center; padding:13px;
      border-radius: var(--radius-sm); border:1px dashed var(--border);
      background:transparent; color:var(--muted); font-weight:600; font-size:13.5px;
      cursor:pointer; margin-top:2px;
    }
    .geri-al-btn:active { background: rgba(255,255,255,.05); }

    .elle-giris-alan { margin-top:8px; }
    .elle-giris-satir { display:flex; gap:8px; }
    .elle-giris-satir input { margin:0; flex:1; }
    .elle-giris-satir button { width:auto; margin:0; padding:0 18px; white-space:nowrap; }
    </style>

    <h3 class="alt" style="margin-bottom:2px;">👤 {{kullanici}}</h3>

    <div class="mod-gecis">
      <button type="button" id="btn-giris" class="mod-btn" onclick="modDegistir('giris')">⬆️ GİRİŞ</button>
      <button type="button" id="btn-cikis" class="mod-btn" onclick="modDegistir('cikis')">⬇️ ÇIKIŞ</button>
    </div>

    {{siparis_bilgi_html|safe}}

    <div class="kamera-cerceve" id="kamera-cerceve" style="display:none;">
      <video id="video"></video>
      <div class="kamera-ustkatman"><div class="tarama-kutu"></div></div>
      <div class="kamera-araclar">
        <button type="button" class="araç-btn" id="flash-btn" onclick="flashDegistir()" style="display:none;">💡</button>
      </div>
    </div>

    <div class="kamera-baslat-alan" id="baslat-alan">
      <button class="btn yesil" style="max-width:320px;margin:0 auto;" onclick="baslat()">📷 Kamerayı Başlat</button>
    </div>

    <div id="sonuc-alan"></div>

    <div class="kart elle-giris-alan">
      <label>Barkod okunmuyorsa elle gir</label>
      <div class="elle-giris-satir">
        <input type="text" id="elle-barkod" inputmode="numeric" placeholder="Barkod numarası">
        <button class="btn mavi" style="width:auto;" onclick="elleGonder()">Ekle</button>
      </div>
    </div>

    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <script>
    let codeReader;
    let kilit = false;
    let bipSes;
    let aktifTip = "{{tip}}";
    let flashAcik = false;
    let sonIslem = null;
    let siparisId = {{ (siparis_id or 'null') }};

    function modDegistir(yeniTip){
        aktifTip = yeniTip;
        document.getElementById('btn-giris').className = 'mod-btn' + (yeniTip === 'giris' ? ' aktif-giris' : '');
        document.getElementById('btn-cikis').className = 'mod-btn' + (yeniTip === 'cikis' ? ' aktif-cikis' : '');
        if(yeniTip === 'cikis' && !siparisId){
            window.location.href = '/kamera/cikis';
            return;
        }
        if(yeniTip === 'giris'){
            window.location.href = '/kamera/giris';
            return;
        }
    }
    modDegistir(aktifTip);

    function baslat(){
        bipSes = new Audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg");
        document.getElementById('baslat-alan').style.display = 'none';
        document.getElementById('kamera-cerceve').style.display = 'block';

        codeReader = new ZXing.BrowserMultiFormatReader();
        codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {
            if (result && !kilit) {
                kilit = true;
                isleGonder(result.text);
            }
            if (err && !(err instanceof ZXing.NotFoundException)) {
                console.log(err);
            }
        });

        setTimeout(fenerKontrolEt, 800);
    }

    function fenerKontrolEt(){
        const video = document.getElementById('video');
        const stream = video.srcObject;
        if(!stream) return;
        const track = stream.getVideoTracks()[0];
        if(!track || !track.getCapabilities) return;
        const yetenekler = track.getCapabilities();
        if(yetenekler.torch){
            document.getElementById('flash-btn').style.display = 'flex';
        }
    }

    function flashDegistir(){
        const video = document.getElementById('video');
        const stream = video.srcObject;
        if(!stream) return;
        const track = stream.getVideoTracks()[0];
        flashAcik = !flashAcik;
        track.applyConstraints({ advanced: [{ torch: flashAcik }] }).catch(e => console.log(e));
        document.getElementById('flash-btn').classList.toggle('aktif', flashAcik);
    }

    function elleGonder(){
        const kutu = document.getElementById('elle-barkod');
        const kod = kutu.value.trim();
        if(!kod) return;
        kutu.value = '';
        isleGonder(kod);
    }

    function isleGonder(barkod){
        if(bipSes){ bipSes.currentTime = 0; bipSes.play().catch(e => {}); }
        if(navigator.vibrate) navigator.vibrate(70);

        fetch("/hizli_islem", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ barkod: barkod, tip: aktifTip, siparis_id: siparisId })
        })
        .then(r => r.json())
        .then(d => sonucGoster(d, barkod))
        .finally(() => { setTimeout(() => { kilit = false; }, 1200); });
    }

    function sonucGoster(d, barkod){
        const alan = document.getElementById('sonuc-alan');

        if (d.ok) {
            sonIslem = { barkod: barkod, tip: aktifTip, siparis_id: siparisId };
            const baslikRengi = aktifTip === 'giris' ? '✅' : '📤';
            let siparisSatiri = '';
            if(d.siparis_ilerleme){
                siparisSatiri = `<br>🧾 Sipariş toplam: <b>${d.siparis_ilerleme.verilen} / ${d.siparis_ilerleme.istenen}</b>` +
                    (d.siparis_ilerleme.tamamlandi ? ' — 🎉 Sipariş tamamlandı!' : '');
            }
            alan.innerHTML = `
              <div class="sonuc-kart sonuc-basari">
                <div class="sonuc-ust"><span class="sonuc-ikon">${baslikRengi}</span><span class="sonuc-ad">${d.ad}</span></div>
                <div class="sonuc-satirlar">
                  🏷️ Cins: <b>${d.cins || '-'}</b> &nbsp; 🔖 Sınıf: <b>${d.sinif || '-'}</b><br>
                  ✨ Yüzey: <b>${d.yuzey || '-'}</b> &nbsp; 🎨 Renk: <b>${d.renk || '-'}</b><br>
                  📏 Ebat: <b>${d.ebat || '-'}</b> &nbsp; 🏭 Depo: <b>${d.depo || '-'}</b><br>
                  📦 Kalan Stok: <b>${d.adet}</b> &nbsp; 📊 Bugünkü Toplam: <b>${d.toplam}</b>${siparisSatiri}
                </div>
                <button class="geri-al-btn" onclick="geriAl()">↩️ Bu işlemi geri al</button>
              </div>`;
        } else if (d.yeni) {
            alan.innerHTML = `
              <div class="sonuc-kart sonuc-yeni">
                <div class="sonuc-ust"><span class="sonuc-ikon">🆕</span><span class="sonuc-ad">Bu barkod stokta yok</span></div>
                <div class="sonuc-satirlar">Yeni ürün ekleme sayfasına yönlendiriliyorsunuz...</div>
              </div>`;
            setTimeout(() => { window.location.href = "/ekle?barkod=" + encodeURIComponent(barkod); }, 1000);
        } else if (d.yanlis_urun) {
            if(navigator.vibrate) navigator.vibrate([120,80,120,80,120]);
            alan.innerHTML = `
              <div class="sonuc-kart sonuc-yanlis">
                <div class="sonuc-ust"><span class="sonuc-ikon">🚫</span><span class="sonuc-ad">${d.msg}</span></div>
                <div class="sonuc-satirlar">"${d.urun_adi || ''}" bu siparişte listelenmiyor. Lütfen sipariş listesindeki ürünleri kontrol et.</div>
              </div>`;
        } else {
            if(navigator.vibrate) navigator.vibrate([60,60,60]);
            alan.innerHTML = `
              <div class="sonuc-kart sonuc-hata">
                <div class="sonuc-ust"><span class="sonuc-ikon">❌</span><span class="sonuc-ad">${d.msg || 'Bulunamadı'}</span></div>
              </div>`;
        }
    }

    function geriAl(){
        if(!sonIslem) return;
        fetch("/geri_al", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(sonIslem)
        })
        .then(r => r.json())
        .then(d => {
            if(d.ok){
                document.getElementById('sonuc-alan').innerHTML =
                  '<div class="sonuc-kart"><div class="sonuc-ust"><span class="sonuc-ikon">↩️</span><span class="sonuc-ad">İşlem geri alındı</span></div></div>';
                sonIslem = null;
            }
        });
    }
    </script>
    """
    return render_template_string(
        sayfa(icerik, "Barkod Okut"),
        tip=tip, kullanici=kullanici,
        siparis_id=(int(siparis_id) if siparis_id else None),
        siparis_bilgi_html=siparis_bilgi_html,
    )


if __name__ == "__main__":
    app.run(debug=True)
