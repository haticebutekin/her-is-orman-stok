from flask import Flask, request, redirect
import sqlite3, os, random, datetime
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)

# DB PATH (Render uyumlu)
BASE_DIR = "/opt/render/project/src"
DB_PATH = os.path.join(BASE_DIR, "db.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

# TABLOLAR
c.execute("""
CREATE TABLE IF NOT EXISTS urun(
id INTEGER PRIMARY KEY AUTOINCREMENT,
barkod TEXT,
ad TEXT,
cins TEXT,
ebat TEXT,
sinif TEXT,
renk TEXT,
yuzey TEXT,
adet INTEGER,
fiyat REAL
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS satis(
id INTEGER PRIMARY KEY AUTOINCREMENT,
urun TEXT,
fiyat REAL,
tarih TEXT
)
""")

conn.commit()

sepet = []

# BARKOD
def barkod_uret():
    return str(random.randint(100000000000,999999999999))

def barkod_resim(kod):
    if not os.path.exists("static/barcodes"):
        os.makedirs("static/barcodes")

    CODE128 = barcode.get_barcode_class('code128')
    CODE128(kod, writer=ImageWriter()).save(f"static/barcodes/{kod}")

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form["k"]=="admin" and request.form["s"]=="1234":
            return redirect("/pos")

    return """
    <h2>🌲 ORMAN KASA PRO</h2>
    <form method="post">
    <input name="k" placeholder="Kullanıcı"><br>
    <input name="s" type="password" placeholder="Şifre"><br>
    <button>Giriş</button>
    </form>
    """

# POS
@app.route("/pos", methods=["GET","POST"])
def pos():
    global sepet

    if request.method=="POST":
        barkod = request.form["barkod"]

        urun = c.execute("SELECT * FROM urun WHERE barkod=?", (barkod,)).fetchone()

        if urun:
            sepet.append({
                "ad":urun[2],
                "barkod":urun[1],
                "fiyat":urun[9]
            })

            c.execute("UPDATE urun SET adet=adet-1 WHERE id=?", (urun[0],))
            conn.commit()

    liste=""
    toplam=0

    for u in sepet:
        toplam+=u["fiyat"]

        liste+=f"""
        <div class='kart'>
        <h3>{u['ad']}</h3>
        {u['fiyat']} TL<br>
        <img src="/static/barcodes/{u['barkod']}.png" width="200">
        </div>
        """

    return f"""
<html>
<head>
<script src="https://unpkg.com/html5-qrcode"></script>
<style>
body{{background:#020617;color:white;font-family:Arial;padding:20px}}
input,button{{width:100%;padding:15px;margin:5px;border-radius:10px;border:0}}
button{{background:#22c55e}}
.kart{{background:#1e293b;padding:10px;margin:10px;border-radius:10px}}
</style>
</head>

<body>

<h2>🌲 ORMAN KASA PRO</h2>

<form method="post">
<input id="barkod" name="barkod" placeholder="Barkod okut">
</form>

<button onclick="kamera()">📷 Kamera</button>

<a href="/ekle"><button type="button">➕ Ürün</button></a>
<a href="/rapor"><button type="button">📊 Rapor</button></a>
<a href="/stok"><button type="button">📦 Stok</button></a>
<a href="/fis"><button type="button">🧾 Satışı Bitir</button></a>

<div id="kamera"></div>

{liste}

<h2>TOPLAM: {toplam} TL</h2>

<script>
function kamera(){{
let s = new Html5QrcodeScanner("kamera",{{fps:10}});
s.render(function(t){{
document.getElementById("barkod").value=t;
s.clear();
document.forms[0].submit();
}});
}}
</script>

</body>
</html>
"""

# SATIŞ TAMAMLA
@app.route("/fis")
def fis():
    global sepet

    for u in sepet:
        c.execute("INSERT INTO satis (urun,fiyat,tarih) VALUES (?,?,?)",
        (u["ad"], u["fiyat"], str(datetime.datetime.now())))

    conn.commit()
    sepet = []
    return redirect("/pos")

# ÜRÜN EKLE
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method=="POST":

        barkod = request.form["b"]

        if barkod == "":
            barkod = barkod_uret()

        barkod_resim(barkod)

        c.execute("""
        INSERT INTO urun
        (barkod,ad,cins,ebat,sinif,renk,yuzey,adet,fiyat)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,(
        barkod,
        request.form["a"],
        request.form["c"],
        request.form["e"],
        request.form["s"],
        request.form["r"],
        request.form["y"],
        request.form["adet"],
        request.form["f"]
        ))

        conn.commit()
        return redirect("/pos")

    return """
    <body style="background:#020617;color:white;padding:20px">

    <h2>ÜRÜN EKLE</h2>

    <form method="post">

    <input name="b" placeholder="Barkod (boş bırak otomatik)">
    <input name="a" placeholder="Ad">
    <input name="c" placeholder="Cins">
    <input name="e" placeholder="Ebat">
    <input name="s" placeholder="Sınıf">
    <input name="r" placeholder="Renk">

    <select name="y">
    <option>MAT</option>
    <option>HG</option>
    </select>

    <input name="adet" placeholder="Adet">
    <input name="f" placeholder="Fiyat">

    <button>KAYDET</button>
    </form>
    </body>
    """

# RAPOR
@app.route("/rapor")
def rapor():
    data = c.execute("SELECT * FROM satis").fetchall()
    html="<h2>RAPOR</h2>"
    toplam=0
    for d in data:
        html+=f"{d[1]} - {d[2]} TL - {d[3]}<br>"
        toplam+=d[2]
    html+=f"<h2>TOPLAM: {toplam} TL</h2>"
    return html

# STOK
@app.route("/stok")
def stok():
    data = c.execute("SELECT * FROM urun").fetchall()
    html="<h2>STOK</h2>"
    for d in data:
        html+=f"{d[2]} - {d[8]} adet<br>"
    return html

if __name__ == "__main__":
    app.run()
