from flask import Flask, request, redirect, session, render_template_string, send_file
import sqlite3, os, datetime, io
import qrcode
from barcode import Code128
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = "herisorman"

DB = "stok.db"
STATIC = "static"
if not os.path.exists(STATIC):
    os.makedirs(STATIC)

# ---------------- DEPOLAR ----------------
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

# ---------------- DB ----------------
def db():
    return sqlite3.connect(DB)

def init_db():
    conn = db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS urunler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barkod TEXT,
        isim TEXT,
        cins TEXT,
        ebat TEXT,
        kalinlik TEXT,
        sinif TEXT,
        yuzey TEXT,
        renk TEXT,
        adet INTEGER,
        depo TEXT,
        tarih TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS hareket (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barkod TEXT,
        islem TEXT,
        adet INTEGER,
        depo TEXT,
        kullanici TEXT,
        tarih TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- BARKOD ----------------
def yeni_barkod():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM urunler")
    say = c.fetchone()[0] + 1
    conn.close()
    return f"HER-{str(say).zfill(6)}"

def barkod_olustur(kod):
    path = f"{STATIC}/{kod}"
    Code128(kod, writer=ImageWriter()).write(open(path + ".png", "wb"))
    return path + ".png"

def qr_olustur(kod):
    path = f"{STATIC}/{kod}_qr.png"
    img = qrcode.make(kod)
    img.save(path)
    return path

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = request.form["user"]
        if user == "admin":
            session["user"] = "admin"
        else:
            session["user"] = "depocu"
        return redirect("/panel")

    return """
    <h2>Giriş</h2>
    <form method="post">
    Kullanıcı: <input name="user"><br><br>
    <button>GİR</button>
    </form>
    """

# ---------------- PANEL ----------------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    return f"""
    <h1>📦 STOK PANEL</h1>

    <a href='/ekle'>➕ ÜRÜN EKLE</a><br><br>
    <a href='/kamera'>📷 OKUT</a><br><br>
    <a href='/stok'>📊 STOK</a><br><br>
    <a href='/hareket'>📋 HAREKET</a><br><br>
    <a href='/logout'>ÇIKIŞ</a>
    """

# ---------------- ÜRÜN EKLE ----------------
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if session.get("user") != "admin":
        return "Yetki yok"

    if request.method == "POST":
        barkod = yeni_barkod()

        barkod_olustur(barkod)
        qr_olustur(barkod)

        conn = db()
        c = conn.cursor()

        c.execute("""
        INSERT INTO urunler
        (barkod,isim,cins,ebat,kalinlik,sinif,yuzey,renk,adet,depo,tarih)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            barkod,
            request.form["isim"],
            request.form["cins"],
            request.form["ebat"],
            request.form["kalinlik"],
            request.form["sinif"],
            request.form["yuzey"],
            request.form["renk"],
            request.form["adet"],
            request.form["depo"],
            datetime.datetime.now()
        ))

        conn.commit()
        conn.close()

        return f"""
        <h2>✅ Ürün eklendi</h2>
        Barkod: {barkod}<br><br>
        <img src='/static/{barkod}.png'><br>
        <img src='/static/{barkod}_qr.png'><br><br>
        <a href='/panel'>GERİ</a>
        """

    depo_ops = "".join([f"<option>{d}</option>" for d in DEPOLAR])

    return f"""
    <h2>ÜRÜN EKLE</h2>
    <form method="post">

    Adı: <input name="isim"><br>
    Cinsi: <input name="cins"><br>
    Ebat: <input name="ebat"><br>
    Kalınlık: <input name="kalinlik"><br>
    Sınıf: <input name="sinif"><br>

    Yüzey:
    <select name="yuzey">
        <option>HG</option>
        <option>MAT</option>
    </select><br>

    Renk: <input name="renk"><br>
    Adet: <input name="adet"><br>

    Depo:
    <select name="depo">
    {depo_ops}
    </select><br><br>

    <button>KAYDET</button>
    </form>
    """

# ---------------- KAMERA ----------------
@app.route("/kamera")
def kamera():
    return """
    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <video id="v" width="300"></video>

    <script>
    const codeReader = new ZXing.BrowserBarcodeReader()
    codeReader.decodeFromVideoDevice(null, 'v', (result) => {
        if(result){
            window.location = "/cikis/" + result.text
        }
    })
    </script>
    """

# ---------------- ÇIKIŞ ----------------
@app.route("/cikis/<kod>", methods=["GET","POST"])
def cikis(kod):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM urunler WHERE barkod=?", (kod,))
    urun = c.fetchone()

    if not urun:
        return "❌ Ürün yok"

    if request.method == "POST":
        adet = int(request.form["adet"])

        c.execute("UPDATE urunler SET adet = adet - ? WHERE barkod=?", (adet,kod))

        c.execute("""
        INSERT INTO hareket (barkod,islem,adet,depo,kullanici,tarih)
        VALUES (?,?,?,?,?,?)
        """, (
            kod,
            "ÇIKIŞ",
            adet,
            urun[10],
            session["user"],
            datetime.datetime.now()
        ))

        conn.commit()
        conn.close()

        return "✅ Stok düştü <br><a href='/panel'>GERİ</a>"

    return f"""
    <h2>ÜRÜN BULUNDU</h2>
    {urun[2]} - {urun[3]} - {urun[4]} mm<br>
    {urun[7]} - {urun[8]}<br><br>

    <form method="post">
    Adet: <input name="adet"><br><br>
    <button>ÇIKIŞ YAP</button>
    </form>
    """

# ---------------- STOK ----------------
@app.route("/stok")
def stok():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM urunler")
    data = c.fetchall()

    html = "<h2>STOK</h2>"

    for d in data:
        html += f"{d[1]} | {d[2]} | {d[9]} adet | {d[10]}<br>"

    return html + "<br><a href='/panel'>GERİ</a>"

# ---------------- HAREKET ----------------
@app.route("/hareket")
def hareket():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM hareket ORDER BY id DESC")
    data = c.fetchall()

    html = "<h2>HAREKET</h2>"

    for h in data:
        html += f"{h[1]} | {h[2]} | {h[3]} adet | {h[4]} | {h[5]} | {h[6]}<br>"

    return html + "<br><a href='/panel'>GERİ</a>"

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
