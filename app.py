from functools import wraps

from flask import Flask, request, redirect, render_template_string, jsonify, session, send_file
import sqlite3, os, random
from datetime import datetime
import barcode, qrcode
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "bu-anahtari-canliya-almadan-once-degistir")
DB = "stok.db"

# STATIC FIX
if os.path.exists("static") and not os.path.isdir("static"):
    os.remove("static")
if not os.path.exists("static"):
    os.makedirs("static")

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
    return sqlite3.connect(DB)


# TABLOLAR
with db() as con:
    con.execute("""
    CREATE TABLE IF NOT EXISTS urun(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT, cins TEXT, ebat TEXT, kalinlik TEXT,
        yuzey TEXT, sinif TEXT, renk TEXT,
        adet INTEGER, depo TEXT, barkod TEXT UNIQUE
    )
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS hareket(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barkod TEXT,
        ad TEXT,
        tip TEXT,
        adet INTEGER,
        kullanici TEXT,
        tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)


def barkod_uret():
    while True:
        kod = str(random.randint(100000000000, 999999999999))
        with db() as con:
            var = con.execute("SELECT barkod FROM urun WHERE barkod=?", (kod,)).fetchone()
        if not var:
            return kod


def barkod_resim(kod):
    CODE128 = barcode.get_barcode_class("code128")
    img = CODE128(kod, writer=ImageWriter())
    img.save(os.path.join("static", kod))


def qr_uret(kod):
    img = qrcode.make(kod)
    img.save(os.path.join("static", kod + "_qr.png"))


HOME_BTN = """
<a href="/" style="
position:fixed;
top:10px;
left:10px;
padding:10px 15px;
background:#2196F3;
color:white;
text-decoration:none;
border-radius:8px;
font-weight:bold;
z-index:9999;
box-shadow:0 2px 6px rgba(0,0,0,0.4);
">
🏠 Ana Sayfa
</a>
<a href="/kullanici_degistir" style="
position:fixed;
top:10px;
right:10px;
padding:10px 15px;
background:#555;
color:white;
text-decoration:none;
border-radius:8px;
font-weight:bold;
z-index:9999;
box-shadow:0 2px 6px rgba(0,0,0,0.4);
">
🔁 Kullanıcı Değiştir
</a>
"""


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
                return HOME_BTN + """
                <h2>⛔ Bu sayfaya erişim yetkiniz yok</h2>
                <p>Bu işlem senin rolüne kapalı. Yanlış kişi olarak girdiysen sağ üstten kullanıcı değiştir.</p>
                """
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

    return render_template_string("""
    <html>
    <head>
    <style>
    body { background:#111; font-family:Arial; text-align:center; color:white; padding-top:60px; }
    input {
        font-size: 32px;
        text-align: center;
        width: 180px;
        padding: 10px;
        border-radius: 10px;
        border: none;
        letter-spacing: 10px;
    }
    button {
        display:block; margin:20px auto 0; padding:15px 40px;
        font-size:20px; border-radius:10px; border:none;
        background: linear-gradient(to right, #2196F3, #00BCD4);
        color:white; font-weight:bold;
    }
    .geri { color:#999; text-decoration:none; display:block; margin-top:30px; }
    </style>
    </head>
    <body>
    <h2>👤 {{isim}}</h2>
    <p>PIN gir</p>

    {% if hata %}<p style="color:#FF5252;font-weight:bold;">{{hata}}</p>{% endif %}

    <form method="post">
    <input type="password" name="pin" inputmode="numeric" pattern="[0-9]*" maxlength="4" autofocus>
    <br>
    <button>Giriş Yap</button>
    </form>

    <a class="geri" href="/">⬅ Geri</a>
    </body>
    </html>
    """, isim=isim, hata=hata)


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
            secim_html += f'<a href="/pin_gir/{isim}" class="btn mavi">{isim}</a>'

        return """
        <html>
        <head>
        <style>
        body { background:#111; font-family:Arial; text-align:center; color:white; }
        h1 { margin-top:20px; }
        .btn {
            display:block; width:80%; margin:15px auto; padding:20px;
            font-size:22px; border-radius:10px; text-decoration:none;
            color:white; font-weight:bold;
        }
        .mavi { background: linear-gradient(to right, #2196F3, #00BCD4); }
        </style>
        </head>
        <body>
        <h1>👋 Kimsin?</h1>
        """ + secim_html + """
        </body>
        </html>
        """

    # Role göre buton seti — patron ve muhasebeci tam yetkili
    butonlar = ""
    if rol in ("depocu", "muhasebeci", "patron"):
        butonlar += '<a href="/kamera/giris" class="btn yesil">⬆ GİRİŞ</a>'
        butonlar += '<a href="/kamera/cikis" class="btn turuncu">📷 ÇIKIŞ OKUT</a>'
    if rol in ("muhasebeci", "patron"):
        butonlar += '<a href="/ekle" class="btn mavi">➕ ÜRÜN EKLE</a>'
        butonlar += '<a href="/liste" class="btn mor">📦 STOK</a>'
        butonlar += '<a href="/hareketler" class="btn kirmizi">📊 HAREKET</a>'
        butonlar += '<a href="/rapor/excel" class="btn turkuaz">📥 EXCEL (XLSX) İNDİR</a>'
        butonlar += '<a href="/rapor/xls" class="btn turkuaz">📥 EXCEL 2003 (XLS) İNDİR</a>'
        butonlar += '<a href="/rapor/csv" class="btn turkuaz">📥 CSV İNDİR</a>'

    return """
    <html>
    <head>
    <style>
    body {
        background: #111;
        font-family: Arial;
        text-align: center;
        color: white;
    }
    h1 { margin-top: 20px; }
    h3 { color: #999; font-weight: normal; }
    .btn {
        display: block;
        width: 80%;
        margin: 15px auto;
        padding: 20px;
        font-size: 22px;
        border-radius: 10px;
        text-decoration: none;
        color: white;
        font-weight: bold;
    }
    .mavi { background: linear-gradient(to right, #2196F3, #00BCD4); }
    .yesil { background: linear-gradient(to right, #00C853, #64DD17); }
    .turuncu { background: linear-gradient(to right, #FF6F00, #FF9800); }
    .mor { background: linear-gradient(to right, #5E35B1, #7E57C2); }
    .kirmizi { background: linear-gradient(to right, #D50000, #FF1744); }
    .turkuaz { background: linear-gradient(to right, #00838F, #00BFA5); }
    </style>
    </head>
    <body>
    """ + HOME_BTN + f"""

    <h1>📦 STOK PANEL</h1>
    <h3>👤 {kullanici} ({rol})</h3>

    {butonlar}

    </body>
    </html>
    """


# EKLE — depocu (giriş sırasında yeni ürün) + patron
@app.route("/ekle", methods=["GET", "POST"])
@rol_gerekli("depocu", "patron")
def ekle2():
    on_dolu_barkod = request.args.get("barkod", "")

    if request.method == "POST":
        barkod = request.form.get("barkod")
        if not barkod:
            barkod = barkod_uret()

        with db() as con:
            con.execute("""
            INSERT INTO urun(ad,cins,ebat,kalinlik,yuzey,sinif,renk,adet,depo,barkod)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """, (
                request.form["ad"],
                request.form["cins"],
                request.form["ebat"],
                request.form["kalinlik"],
                request.form["yuzey"],
                request.form["sinif"],
                request.form["renk"],
                int(request.form["adet"]),
                request.form["depo"],
                barkod,
            ))
            con.execute("""
            INSERT INTO hareket (barkod, ad, tip, adet, kullanici)
            VALUES (?, ?, 'giris', ?, ?)
            """, (barkod, request.form["ad"], int(request.form["adet"]), session.get("kullanici", "Bilinmiyor")))

        barkod_resim(barkod)
        qr_uret(barkod)

        return HOME_BTN + f"""
        <h2>✅ Ürün Kaydedildi</h2>
        <b>{request.form["ad"]}</b><br><br>
        📦 Barkod: {barkod}<br><br>
        <img src="/static/{barkod}.png" width="300"><br><br>
        <img src="/static/{barkod}_qr.png" width="150"><br><br>
        <a href="/liste">📦 Stok Listesine Git</a><br><br>
        <a href="/ekle">➕ Yeni Ürün Ekle</a><br><br>
        """

    return render_template_string(HOME_BTN + """

    <h3>Ürün Bilgisi</h3>

    {% if on_dolu_barkod %}
    <p style="color:#2196F3;font-weight:bold;">📷 Okutulan barkod: {{on_dolu_barkod}} — bu ürün stokta yok, yeni ürün olarak ekleyin.</p>
    {% endif %}

    <form method="post">
    <input name="barkod" value="{{on_dolu_barkod}}" placeholder="Boş bırak = otomatik barkod"><br><br>
    <input name="ad" placeholder="Ürün Adı" required><br><br>
    <input name="cins" placeholder="Cins"><br><br>
    <input name="ebat" placeholder="Ebat"><br><br>
    <input name="kalinlik" placeholder="Kalınlık"><br><br>
    <label>Yüzey</label><br>
    <select name="yuzey" required>
        <option value="">Seçiniz</option>
        <option value="HG">HG</option>
        <option value="MAT">MAT</option>
    </select><br><br>
    <input name="sinif" placeholder="Sınıf"><br><br>
    <input name="renk" placeholder="Renk"><br><br>
    <input name="adet" type="number" placeholder="Adet" required><br><br>
    <label>Depo</label><br>
    <select name="depo">
    {% for d in depolar %}
    <option>{{d}}</option>
    {% endfor %}
    </select>
    <br><br>
    <button>Kaydet</button>
    </form>
    """, depolar=DEPOLAR, on_dolu_barkod=on_dolu_barkod)


# LİSTE — muhasebeci + patron
@app.route("/liste")
@rol_gerekli("muhasebeci")
def liste():
    with db() as con:
        urunler = con.execute("SELECT * FROM urun").fetchall()

    html = HOME_BTN + "<h2>STOK</h2>"
    for u in urunler:
        html += f"""
        <div style='border:1px solid gray; padding:10px; margin:10px'>
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
        <img src="/static/{u[10]}.png" width="200"><br>
        <img src="/static/{u[10]}_qr.png" width="100">
        </div>
        """
    return html


# HAREKETLER — muhasebeci + patron
@app.route("/hareketler")
@rol_gerekli("muhasebeci")
def hareket_listesi():
    with db() as con:
        kayitlar = con.execute("""
            SELECT h.ad, h.barkod, h.tip, h.adet, h.kullanici, h.tarih,
                   u.cins, u.sinif, u.yuzey, u.renk, u.ebat, u.depo
            FROM hareket h
            LEFT JOIN urun u ON u.barkod = h.barkod
            ORDER BY h.id DESC
        """).fetchall()

    html = HOME_BTN + "<h2>📊 TÜM HAREKETLER</h2><br>"
    for ad, barkod, tip, adet, kullanici, tarih, cins, sinif, yuzey, renk, ebat, depo in kayitlar:
        html += f"""
        📦 {ad} <br>
        🏷️ Cins: {cins or '-'} &nbsp;&nbsp; 🔖 Sınıf: {sinif or '-'} &nbsp;&nbsp; ✨ Yüzey: {yuzey or '-'} <br>
        🎨 Renk: {renk or '-'} &nbsp;&nbsp; 📏 Ebat: {ebat or '-'} &nbsp;&nbsp; 🏭 Depo: {depo or '-'} <br>
        🔢 {barkod} <br>
        🔄 {tip.upper()} <br>
        ➕/➖ {adet} <br>
        👤 {kullanici} <br>
        🕒 {tarih} <br>
        ----------------------<br>
        """
    return html


# EXCEL RAPOR (XLSX — Excel 2007 ve üzeri) — muhasebeci + patron
@app.route("/rapor/excel")
@rol_gerekli("muhasebeci")
def rapor_excel():
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    import io

    wb = Workbook()

    # --- STOK SAYFASI ---
    ws1 = wb.active
    ws1.title = "Stok"
    basliklar1 = ["Ürün Adı", "Cins", "Ebat", "Kalınlık", "Yüzey", "Sınıf", "Renk", "Adet", "Depo", "Barkod"]
    ws1.append(basliklar1)
    for c in ws1[1]:
        c.font = Font(name="Arial", bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="2196F3")

    with db() as con:
        urunler = con.execute(
            "SELECT ad,cins,ebat,kalinlik,yuzey,sinif,renk,adet,depo,barkod FROM urun"
        ).fetchall()
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

    with db() as con:
        hareketler = con.execute(
            "SELECT ad,barkod,tip,adet,kullanici,tarih FROM hareket ORDER BY id DESC"
        ).fetchall()
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
# openpyxl xlsx (Office 2007+) üretir; Excel 2003 bunu tanımaz.
# Bu route xlwt ile klasik .xls üretir, Excel 2003 dahil her sürümde açılır.
# Not: xlwt sayfa başına 65.536 satır / 256 sütun sınırına sahiptir.
@app.route("/rapor/xls")
@rol_gerekli("muhasebeci")
def rapor_xls():
    import xlwt
    import io

    wb = xlwt.Workbook()

    baslik_stili = xlwt.easyxf(
        "font: bold on, color white; pattern: pattern solid, fore_colour blue;"
    )

    # --- STOK SAYFASI ---
    ws1 = wb.add_sheet("Stok")
    basliklar1 = ["Ürün Adı", "Cins", "Ebat", "Kalınlık", "Yüzey", "Sınıf", "Renk", "Adet", "Depo", "Barkod"]
    for col, b in enumerate(basliklar1):
        ws1.write(0, col, b, baslik_stili)

    with db() as con:
        urunler = con.execute(
            "SELECT ad,cins,ebat,kalinlik,yuzey,sinif,renk,adet,depo,barkod FROM urun"
        ).fetchall()
    for row_idx, satir in enumerate(urunler, start=1):
        for col_idx, deger in enumerate(satir):
            ws1.write(row_idx, col_idx, deger)
    for col_idx in range(len(basliklar1)):
        ws1.col(col_idx).width = 256 * 18  # yaklaşık 18 karakter genişlik

    # --- HAREKETLER SAYFASI ---
    ws2 = wb.add_sheet("Hareketler")
    basliklar2 = ["Ürün Adı", "Barkod", "İşlem", "Adet", "Kullanıcı", "Tarih"]
    for col, b in enumerate(basliklar2):
        ws2.write(0, col, b, baslik_stili)

    with db() as con:
        hareketler = con.execute(
            "SELECT ad,barkod,tip,adet,kullanici,tarih FROM hareket ORDER BY id DESC"
        ).fetchall()
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
    import io

    si = io.StringIO()
    writer = csv.writer(si, delimiter=";")  # Türkçe Windows Excel ; ayraç bekler
    writer.writerow(["Ürün Adı", "Cins", "Ebat", "Kalınlık", "Yüzey", "Sınıf", "Renk", "Adet", "Depo", "Barkod"])

    with db() as con:
        urunler = con.execute(
            "SELECT ad,cins,ebat,kalinlik,yuzey,sinif,renk,adet,depo,barkod FROM urun"
        ).fetchall()
    writer.writerows(urunler)

    output = io.BytesIO(si.getvalue().encode("utf-8-sig"))  # BOM: ş,ğ,ü,ö,ç,ı bozulmasın
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

    with db() as con:
        cur = con.cursor()
        cur.execute("SELECT id, ad, adet, cins, ebat, yuzey, sinif, renk, depo FROM urun WHERE barkod=?", (barkod,))
        row = cur.fetchone()

        if not row:
            if tip == "giris":
                # Barkod DB'de yok ama giriş yapılıyor -> yeni ürün ekleme akışına yönlendir
                return jsonify({"ok": False, "yeni": True, "barkod": barkod})
            # Çıkış (mal verme) tarafında: sadece sizin sisteme kayıtlı sattığınız
            # ürünler çıkış yapılabilir. Kayıtlı olmayan barkod kesinlikle reddedilir.
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

        cur.execute("UPDATE urun SET adet=? WHERE id=?", (adet, uid))
        cur.execute("""
        INSERT INTO hareket (barkod, ad, tip, adet, kullanici)
        VALUES (?, ?, ?, ?, ?)
        """, (barkod, ad, tip, 1, kullanici))

        toplam = cur.execute("""
        SELECT SUM(adet) FROM hareket WHERE kullanici=? AND tip='cikis'
        """, (kullanici,)).fetchone()[0]
        if not toplam:
            toplam = 0

        con.commit()

        return jsonify({
            "ok": True, "ad": ad, "adet": adet, "toplam": toplam,
            "cins": cins, "ebat": ebat, "yuzey": yuzey, "sinif": sinif,
            "renk": renk, "depo": depo,
        })


# GERİ AL — depocu + patron
@app.route("/geri_al", methods=["POST"])
@rol_gerekli("depocu")
def geri_al():
    data = request.get_json()
    barkod = data.get("barkod")
    tip = data.get("tip")

    with db() as con:
        cur = con.cursor()
        cur.execute("SELECT id, adet FROM urun WHERE barkod=?", (barkod,))
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

        cur.execute("UPDATE urun SET adet=? WHERE id=?", (adet, uid))
        con.commit()

    return jsonify({"ok": True})


# KAMERA (barkod okutma ekranı) — depocu + patron, kullanıcı artık oturumdan otomatik
@app.route("/kamera/<tip>")
@rol_gerekli("depocu")
def kamera(tip):
    kullanici = session.get("kullanici", "Bilinmiyor")

    return render_template_string(HOME_BTN + """
    <h2>{{tip.upper()}} OKUT</h2>
    <h3 style="color:#999;">👤 {{kullanici}}</h3>

    <button onclick="baslat()">Kamerayı Başlat</button>

    <br><br>

    <video id="video" width="300" height="200"></video>

    <h3 id="sonuc"></h3>

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
    """, tip=tip, kullanici=kullanici)


if __name__ == "__main__":
    app.run(debug=True)
