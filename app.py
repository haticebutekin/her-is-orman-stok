from flask import Flask, request, redirect, render_template_string, jsonify
import sqlite3, os
import barcode, qrcode
from barcode.writer import ImageWriter

app = Flask(__name__)
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
"KESİMHANE"
]

def db():
    return sqlite3.connect(DB)

# TABLO
with db() as con:
    con.execute("""
    CREATE TABLE IF NOT EXISTS urun(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT,cins TEXT,ebat TEXT,kalinlik TEXT,
        yuzey TEXT,sinif TEXT,renk TEXT,
        adet INTEGER,depo TEXT,barkod TEXT UNIQUE
    )
    """)

with db() as con:
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

# BARKOD
def barkod_uret():
    with db() as con:
        sayi = con.execute("SELECT COUNT(*) FROM urun").fetchone()[0] + 1
    return str(100000000000 + sayi)

def barkod_resim(kod):
    yol = os.path.join("static", kod)
    CODE128 = barcode.get_barcode_class("code128")
    img = CODE128(kod, writer=ImageWriter())
    img.save(yol)

def qr_uret(kod):
    img = qrcode.make(kod)
    img.save(os.path.join("static", kod+"_qr.png"))

# ANA
@app.route("/")
def index():
    return """
    <h1>📦 STOK PRO</h1>
    <a href="/ekle">➕ Ürün Ekle</a><br>
    <a href="/liste">📋 Liste</a><br>
    <a href="/kamera/giris">📥 Giriş</a><br>
    <a href="/kamera/cikis">📤 Çıkış</a><br>
    <a href="/hareketler">📊 Hareketler</a>
    """

# EKLE
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method == "POST":
        barkod = request.form.get("barkod") or barkod_uret()

        with db() as con:
            con.execute("""
            INSERT INTO urun(ad,cins,ebat,kalinlik,yuzey,sinif,renk,adet,depo,barkod)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            """,(
                request.form["ad"],
                request.form["cins"],
                request.form["ebat"],
                request.form["kalinlik"],
                request.form["yuzey"],
                request.form["sinif"],
                request.form["renk"],
                int(request.form["adet"]),
                request.form["depo"],
                barkod
            ))

        barkod_resim(barkod)
        qr_uret(barkod)

        return redirect("/liste")

    return render_template_string("""
    <form method="post">
    <input name="ad" placeholder="Ad">
    <input name="cins" placeholder="Cins">
    <input name="ebat" placeholder="Ebat">
    <input name="kalinlik" placeholder="Kalınlık">
    <input name="yuzey" placeholder="Yüzey">
    <input name="sinif" placeholder="Sınıf">
    <input name="renk" placeholder="Renk">
    <input name="adet" type="number" placeholder="Adet">
    <select name="depo">
    {% for d in depolar %}
    <option>{{d}}</option>
    {% endfor %}
    </select>
    <button>Kaydet</button>
    </form>
    """, depolar=DEPOLAR)

# LİSTE
@app.route("/liste")
def liste():
    with db() as con:
        urunler = con.execute("SELECT * FROM urun").fetchall()

    html = "<h2>STOK</h2>"
    for u in urunler:
        html += f"{u[1]} - {u[8]}<br>"
    return html

# HAREKET
@app.route("/hareketler")
def hareketler():
    with db() as con:
        rows = con.execute("""
        SELECT barkod, ad, tip, adet, kullanici, tarih 
        FROM hareket ORDER BY id DESC
        """).fetchall()

    html = "<h2>Hareketler</h2>"
    for r in rows:
        html += f"{r}<br>"
    return html

# HIZLI İŞLEM
@app.route("/hizli_islem", methods=["POST"])
def hizli_islem():
    data = request.get_json()
    barkod = data.get("barkod")
    tip = data.get("tip")
    kullanici = data.get("kullanici", "Kamera")

    with db() as con:
        cur = con.cursor()
        cur.execute("SELECT id, ad, adet FROM urun WHERE barkod=?", (barkod,))
        row = cur.fetchone()

        if not row:
            return jsonify({"ok":False})

        uid, ad, adet = row

        # STOK KONTROL
        if tip == "cikis" and adet <= 0:
            return jsonify({"ok":False, "msg":"Stok yok"})

        if tip == "giris":
            adet += 1
        else:
            adet -= 1

        if adet < 0:
            adet = 0

        cur.execute("UPDATE urun SET adet=? WHERE id=?", (adet, uid))

        cur.execute("""
        INSERT INTO hareket (barkod,ad,tip,adet,kullanici) 
        VALUES (?,?,?,?,?)
        """,(barkod,ad,tip,1,kullanici))

        con.commit()

    return jsonify({"ok":True,"ad":ad,"adet":adet})

# GERİ AL
@app.route("/geri_al", methods=["POST"])
def geri_al():
    data = request.get_json()
    barkod = data.get("barkod")
    tip = data.get("tip")

    with db() as con:
        cur = con.cursor()
        cur.execute("SELECT id, adet FROM urun WHERE barkod=?", (barkod,))
        row = cur.fetchone()

        if not row:
            return jsonify({"ok":False})

        uid, adet = row

        if tip == "giris":
            adet -= 1
        else:
            adet += 1

        if adet < 0:
            adet = 0

        cur.execute("UPDATE urun SET adet=? WHERE id=?", (adet, uid))
        con.commit()

    return jsonify({"ok":True})

# KAMERA
@app.route("/kamera/<tip>")
def kamera(tip):
    return render_template_string("""
    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <video id="video" width="300"></video>
    <input id="kullanici" placeholder="İşlem yapan">

    <script>
    const codeReader = new ZXing.BrowserMultiFormatReader();

    codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {
        if (result) {
            fetch("/hizli_islem", {
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body: JSON.stringify({
                    barkod:result.text,
                    tip:"{{tip}}",
                    kullanici:document.getElementById("kullanici").value
                })
            });
        }
    });
    </script>
    """)

if __name__ == "__main__":
    app.run(debug=True)
