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
# Render'da Postgres eklentisi oluşturunca sana bir "Internal Database URL"
# verir. Bunu bu servisin Environment sekmesinde DATABASE_URL adıyla ekle.
# Örnek: postgres://kullanici:sifre@host/veritabani
#
# Not: Eğer bağlantı hatası alırsan (SSL required vb.) DATABASE_URL'in
# sonuna "?sslmode=require" ekleyebilirsin.
DATABASE_URL = os.environ.get("DATABASE_URL", "")

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)) or ".", "static"))
app.secret_key = os.environ.get("SECRET_KEY", "bu-anahtari-canliya-almadan-once-degistir")

# STATIC FIX (sadece uygulama ikonları için kullanılıyor, artık ürün/barkod resmi için değil)
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
]

# KULLANICI -> ROL
ROLLER = {
    "Ramazan": "depocu",
    "Behiç": "depocu",
    "Orhan": "depocu",
    "Berke": "muhasebeci",
    "İrem": "muhasebeci",
    "Hatice": "patron",
    "Ahmet": "patron",
}

# KULLANICI -> PIN (GEÇİCİ! Canlıya almadan önce bunları gerçek PIN'lerle değiştirin)
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
    """Her çağrıda yeni bir Postgres bağlantısı açar. 'with db() as con:' bloğu
    bittiğinde otomatik commit/rollback yapılır ama bağlantıyı kapatmaz;
    bu yüzden fonksiyonlar sonunda con.close() çağırıyoruz."""
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
                # Var olan kurulumlarda sütun DEFAULT CURRENT_TIMESTAMP ile
                # gelmiş olabilir (UTC saatiyle) — kaldırıyoruz, çünkü tarihi
                # artık her INSERT'te Türkiye saatiyle biz açıkça veriyoruz.
                cur.execute("ALTER TABLE hareket ALTER COLUMN tarih DROP DEFAULT")
    finally:
        con.close()


if DATABASE_URL:
    tablolari_olustur()


def tr_simdi():
    """Türkiye saatiyle (Europe/Istanbul) şu anki zamanı, saat dilimi
    bilgisi olmadan (naive) döndürür — tarih sütununa böyle yazıyoruz."""
    return datetime.now(TR_TZ).replace(tzinfo=None)


def barkod_uret():
    while True:
        kod = str(random.randint(100000000000, 999999999999))
        con = db()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT barkod FROM urun WHERE barkod=%s", (kod,))
                var = cur.fetchone()
        finally:
            con.close()
        if not var:
            return kod


def barkod_png_bytes(kod):
    """Barkod resmini diske yazmadan bellekte üretir."""
    CODE128 = barcode.get_barcode_class("code128")
    bio = io.BytesIO()
    CODE128(kod, writer=ImageWriter()).write(bio)
    bio.seek(0)
    return bio


def qr_png_bytes(kod):
    """QR resmini diske yazmadan bellekte üretir."""
    img = qrcode.make(kod)
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    bio.seek(0)
    return bio


def ikon_uret():
    """Uygulama ikonlarını (PWA / ana ekrana ekle için) bir kere üretir.
    Bunlar kullanıcı verisi değil, sabit uygulama ikonu olduğu için static
    klasöründe kalması sorun değil; her başlangıçta zaten yeniden üretiliyor."""
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


# ==================== ORTAK TASARIM ====================

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
.topbar-title { font-weight:700; font-size:14.5px; color:#eee; letter-spacing:.2px; }

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
  transition: transform .1s ease, filter .15s ease;
}
.btn-kucuk:active { filter:brightness(0.85); transform: scale(0.96); }

.kart {
  background: linear-gradient(180deg, var(--card2), var(--card));
  border:1px solid var(--border); border-radius: var(--radius);
  padding:16px; margin:12px 0; text-align:left;
  box-shadow: 0 2px 10px rgba(0,0,0,.18);
  transition: border-color .15s ease;
}

input[type=text], input[type=number], input[type=password], select, textarea {
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
"""

UST_BAR = """
<div class="topbar">
  <a href="/" class="topbar-btn" title="Ana Sayfa">🏠</a>
  <span class="topbar-title">📦 Stok Takip</span>
  <a href="/kullanici_degistir" class="topbar-btn" title="Kullanıcı Değiştir">🔁</a>
</div>
"""

# Geriye dönük uyumluluk için eski isim korunuyor
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
        "name": "Stok Takip",
        "short_name": "Stok Takip",
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


# Barkod ve QR resimleri artık diske yazılmıyor; her istekte anlık üretiliyor.
@app.route("/barkod/<kod>.png")
def barkod_resim_endpoint(kod):
    return send_file(barkod_png_bytes(kod), mimetype="image/png")


@app.route("/qr/<kod>.png")
def qr_resim_endpoint(kod):
    return send_file(qr_png_bytes(kod), mimetype="image/png")


def rol_gerekli(*izinli_roller):
    """Sadece belirtilen rollerin (ve her zaman patron + muhasebecinin) erişebileceği sayfalar için."""
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


# KULLANICI SEÇ / PIN GİR
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
    <h2>👤 {{isim}}</h2>
    <p style="text-align:center;color:var(--muted);">PIN gir</p>

    {% if hata %}<p class="hata">{{hata}}</p>{% endif %}

    <form method="post">
    <input class="pin-input" type="password" name="pin" inputmode="numeric" pattern="[0-9]*" maxlength="4" autofocus>
    <button class="btn mavi">Giriş Yap</button>
    </form>

    <p style="text-align:center;margin-top:24px;">
    <a href="/" style="color:var(--muted);text-decoration:none;">⬅ Geri</a>
    </p>
    """
    return render_template_string(sayfa(icerik, "Giriş"), isim=isim, hata=hata)


@app.route("/kullanici_degistir")
def kullanici_degistir():
    session.clear()
    return redirect("/")


# ANA
@app.route("/")
def index():
    kullanici = session.get("kullanici")
    rol = session.get("rol")

    if not kullanici:
        secim_html = ""
        for isim in ROLLER:
            secim_html += '<a href="/pin_gir/' + isim + '" class="btn mavi">' + isim + '</a>'

        icerik = (
            "<h1>👋 Kimsin?</h1>"
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
        return sayfa(icerik, "Giriş - Stok Takip")

    # Role göre buton seti — patron ve muhasebeci tam yetkili
    butonlar = ""
    if rol in ("depocu", "muhasebeci", "patron"):
        butonlar += '<a href="/kamera/giris" class="btn yesil">⬆ GİRİŞ OKUT</a>'
        butonlar += '<a href="/kamera/cikis" class="btn turuncu">📷 ÇIKIŞ OKUT</a>'
    if rol in ("muhasebeci", "patron"):
        butonlar += '<a href="/ekle" class="btn mavi">➕ ÜRÜN EKLE</a>'
        butonlar += '<a href="/liste" class="btn mor">📦 STOK LİSTESİ</a>'
        butonlar += '<a href="/hareketler" class="btn kirmizi">📊 HAREKETLER</a>'
        butonlar += '<a href="/rapor/excel" class="btn turkuaz">📥 EXCEL (XLSX)</a>'
        butonlar += '<a href="/rapor/xls" class="btn turkuaz">📥 EXCEL 2003 (XLS)</a>'
        butonlar += '<a href="/rapor/csv" class="btn turkuaz">📥 CSV İNDİR</a>'

    icerik = (
        "<h1>📦 STOK PANEL</h1>"
        + '<h3 class="alt">👤 ' + kullanici + ' (' + rol + ')</h3>'
        + butonlar
    )
    return sayfa(icerik, "Stok Panel")


# EKLE — depocu (giriş sırasında yeni ürün) + patron
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
            '<h2>✅ Ürün Kaydedildi</h2>'
            + '<p style="text-align:center;"><b>' + ad + '</b></p>'
            + '<div class="kart" style="text-align:center;">'
            + '📦 Barkod: ' + barkod + '<br><br>'
            + '<img src="/barkod/' + barkod + '.png" width="260"><br><br>'
            + '<img src="/qr/' + barkod + '.png" width="140">'
            + '</div>'
            + '<a class="btn mor" href="/liste">📦 Stok Listesine Git</a>'
            + '<a class="btn mavi" href="/ekle">➕ Yeni Ürün Ekle</a>'
        )
        return sayfa(icerik, "Ürün Kaydedildi")

    icerik = """
    <h3>Ürün Bilgisi</h3>

    {% if on_dolu_barkod %}
    <p class="hata" style="color:#2196F3;">📷 Okutulan barkod: {{on_dolu_barkod}} — bu ürün stokta yok, yeni ürün olarak ekleyin.</p>
    {% endif %}

    <form method="post">
    <label>Barkod</label>
    <input name="barkod" value="{{on_dolu_barkod}}" placeholder="Boş bırak = otomatik barkod">
    <label>Ürün Adı</label>
    <input name="ad" placeholder="Ürün Adı" required>
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


# LİSTE — muhasebeci + patron
@app.route("/liste")
@rol_gerekli("muhasebeci")
def liste():
    con = db()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT * FROM urun")
            urunler = cur.fetchall()
    finally:
        con.close()

    kartlar = ""
    for u in urunler:
        kartlar += f"""
        <div class='kart' id="urun-{u[10]}">
        <b>{u[1]}</b><br>
        Cins: {u[2]}<br>
        Ebat: {u[3]}<br>
        Kalınlık: {u[4]}<br>
        Yüzey: {u[5]}<br>
        Sınıf: {u[6]}<br>
        Renk: {u[7]}<br>
        Adet: {u[8]}<br>
        Depo: {u[9]}<br>
        Barkod: {u[10]}<br>
        <img src="/barkod/{u[10]}.png" width="180"><br>
        <img src="/qr/{u[10]}.png" width="90"><br><br>
        <button class="btn-kucuk kirmizi" onclick="urunSil('{u[10]}')">🗑️ Sil</button>
        </div>
        """

    icerik = (
        "<h2>📦 STOK</h2>"
        + '<input class="arama" id="arama" placeholder="🔍 Ürün, barkod veya depo ara..." oninput="ara()">'
        + '<div id="liste">' + kartlar + '</div>'
        + """
        <script>
        function ara(){
          var q = document.getElementById('arama').value.toLocaleLowerCase('tr');
          document.querySelectorAll('#liste .kart').forEach(function(k){
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
        </script>
        """
    )
    return sayfa(icerik, "Stok Listesi")


# HAREKETLER — muhasebeci + patron
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
        kartlar += f"""
        <div class="kart">
        📦 <b>{ad}</b><br>
        🏷️ Cins: {cins or '-'} &nbsp; 🔖 Sınıf: {sinif or '-'} &nbsp; ✨ Yüzey: {yuzey or '-'}<br>
        🎨 Renk: {renk or '-'} &nbsp; 📏 Ebat: {ebat or '-'} &nbsp; 🏭 Depo: {depo or '-'}<br>
        🔢 {barkod}<br>
        🔄 {tip.upper()} &nbsp; ➕/➖ {adet}<br>
        👤 {kullanici} &nbsp; 🕒 {tarih}
        </div>
        """

    icerik = (
        "<h2>📊 TÜM HAREKETLER</h2>"
        + '<input class="arama" id="arama" placeholder="🔍 Ürün, barkod veya kullanıcı ara..." oninput="ara()">'
        + '<div id="hareketler">' + kartlar + '</div>'
        + """
        <script>
        function ara(){
          var q = document.getElementById('arama').value.toLocaleLowerCase('tr');
          document.querySelectorAll('#hareketler .kart').forEach(function(k){
            var metin = k.textContent.toLocaleLowerCase('tr');
            k.style.display = metin.indexOf(q) !== -1 ? '' : 'none';
          });
        }
        </script>
        """
    )
    return sayfa(icerik, "Hareketler")


# EXCEL RAPOR (XLSX — Excel 2007 ve üzeri) — muhasebeci + patron
@app.route("/rapor/excel")
@rol_gerekli("muhasebeci")
def rapor_excel():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    wb = Workbook()

    # --- STOK SAYFASI ---
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

    # --- HAREKETLER SAYFASI ---
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


# EXCEL 2003 RAPOR (XLS — eski binary format) — muhasebeci + patron
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


# CSV RAPOR (her Excel sürümünde sorunsuz açılır) — muhasebeci + patron
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
    writer.writerows(urunler)

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
    kullanici = session.get("kullanici", "Bilinmiyor")

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

                cur.execute("""
                SELECT SUM(adet) FROM hareket WHERE kullanici=%s AND tip='cikis'
                """, (kullanici,))
                toplam = cur.fetchone()[0]
                if not toplam:
                    toplam = 0

                return jsonify({
                    "ok": True, "ad": ad, "adet": adet, "toplam": toplam,
                    "cins": cins, "ebat": ebat, "yuzey": yuzey, "sinif": sinif,
                    "renk": renk, "depo": depo,
                })
    finally:
        con.close()


# ÜRÜN SİL — muhasebeci + patron
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


# GERİ AL — depocu + patron
@app.route("/geri_al", methods=["POST"])
@rol_gerekli("depocu")
def geri_al():
    data = request.get_json()
    barkod = data.get("barkod")
    tip = data.get("tip")

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
    finally:
        con.close()

    return jsonify({"ok": True})


# KAMERA (barkod okutma ekranı) — depocu + patron, kullanıcı artık oturumdan otomatik
@app.route("/kamera/<tip>")
@rol_gerekli("depocu")
def kamera(tip):
    kullanici = session.get("kullanici", "Bilinmiyor")

    icerik = """
    <h2>{{tip.upper()}} OKUT</h2>
    <h3 class="alt">👤 {{kullanici}}</h3>

    <button class="btn yesil" onclick="baslat()">Kamerayı Başlat</button>

    <div class="video-alan">
    <video id="video" width="300" height="200"></video>
    </div>

    <h3 id="sonuc" style="text-align:left;"></h3>

    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <script>
    let codeReader;
    let kilit = false;
    let bipSes;

    function baslat(){
        bipSes = new Audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg");
        codeReader = new ZXing.BrowserMultiFormatReader();

        codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {
            if (result && !kilit) {
                kilit = true;

                let barkod = result.text;

                bipSes.currentTime = 0;
                bipSes.play().catch(e => console.log(e));

                fetch("/hizli_islem", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        barkod: barkod,
                        tip: "{{tip}}"
                    })
                })
                .then(r => r.json())
                .then(d => {
                    if (d.ok) {
                        document.body.style.background = "green";
                        document.getElementById("sonuc").innerHTML =
                            "✅ Barkod: " + barkod + "<br>" +
                            "📦 Ürün: " + d.ad + "<br>" +
                            "🏷️ Cins: " + (d.cins || "-") + "<br>" +
                            "🔖 Sınıf: " + (d.sinif || "-") + "<br>" +
                            "✨ Yüzey: " + (d.yuzey || "-") + "<br>" +
                            "🎨 Renk: " + (d.renk || "-") + "<br>" +
                            "📏 Ebat: " + (d.ebat || "-") + "<br>" +
                            "🏭 Depo: " + (d.depo || "-") + "<br>" +
                            "📦 Kalan: " + d.adet + "<br>" +
                            "📊 Senin Toplam Çıkışın: " + d.toplam + "<br>" +
                            "👤 Kullanıcı: {{kullanici}}";
                    } else if (d.yeni) {
                        document.body.style.background = "#2196F3";
                        document.getElementById("sonuc").innerHTML =
                            "🆕 Bu barkod stokta yok, yeni ürün ekleme sayfasına yönlendiriliyorsunuz...";
                        setTimeout(() => {
                            window.location.href = "/ekle?barkod=" + encodeURIComponent(barkod);
                        }, 1200);
                        return;
                    } else {
                        document.body.style.background = "red";
                        document.getElementById("sonuc").innerHTML =
                            "❌ Hata: " + (d.msg || "Bulunamadı");
                    }

                    setTimeout(() => { kilit = false; }, 2000);
                });
            }

            if (err && !(err instanceof ZXing.NotFoundException)) {
                console.log(err);
            }
        });
    }
    </script>
    """
    return render_template_string(sayfa(icerik, tip.upper() + " Okut"), tip=tip, kullanici=kullanici)


if __name__ == "__main__":
    app.run(debug=True)
