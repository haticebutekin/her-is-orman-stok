from flask import Flask, request, redirect, session, render_template_string, send_file
import sqlite3, os, datetime, qrcode

app = Flask(__name__)
app.secret_key = "secret123"

# 📦 DEPOLAR
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

# 📁 DB
def db():
    return sqlite3.connect("market.db")

def kur():
    conn = db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT,
        role TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY,
        name TEXT,
        cins TEXT,
        ebat TEXT,
        sinif TEXT,
        hg TEXT,
        renk TEXT,
        adet INTEGER,
        depo TEXT,
        barcode TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS hareket(
        id INTEGER PRIMARY KEY,
        user TEXT,
        islem TEXT,
        urun TEXT,
        adet INTEGER,
        depo TEXT,
        saat TEXT
    )""")

    # admin + depocu
    if c.execute("SELECT * FROM users").fetchall() == []:
        c.execute("INSERT INTO users VALUES(NULL,'admin','1234','admin')")
        c.execute("INSERT INTO users VALUES(NULL,'depocu','1234','depocu')")

    conn.commit()
    conn.close()

kur()

# 🔑 LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["u"]
        p = request.form["p"]

        conn = db()
        c = conn.cursor()
        user = c.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p)).fetchone()
        conn.close()

        if user:
            session["user"] = u
            session["role"] = user[3]
            return redirect("/panel")

    return """
    <h2>GİRİŞ</h2>
    <form method=post>
    Kullanıcı: <input name=u><br>
    Şifre: <input name=p type=password><br>
    <button>GİR</button>
    </form>
    """

# 🧠 PANEL
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    if session["role"] == "admin":
        return """
        <h2>YÖNETİCİ PANEL</h2>
        <a href='/ekle'>Ürün Ekle</a><br>
        <a href='/liste'>Stok</a><br>
        <a href='/hareket'>Hareketler</a><br>
        <a href='/cikis'>Çıkış</a>
        """
    else:
        return """
        <h2>DEPOCU PANEL</h2>
        <a href='/okut'>Barkod Okut</a><br>
        <a href='/cikis'>Çıkış</a>
        """

# ➕ ÜRÜN EKLE
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if session.get("role") != "admin":
        return "Yetki yok"

    if request.method == "POST":
        data = request.form

        barkod = str(int(datetime.datetime.now().timestamp()))

        conn = db()
        c = conn.cursor()
        c.execute("""INSERT INTO products 
        VALUES(NULL,?,?,?,?,?,?,?,?,?)""",(
            data["name"], data["cins"], data["ebat"],
            data["sinif"], data["hg"], data["renk"],
            data["adet"], data["depo"], barkod
        ))

        conn.commit()
        conn.close()

        # QR üret
        img = qrcode.make(barkod)
        path = f"{barkod}.png"
        img.save(path)

        return f"BARKOD: {barkod}<br><a href='/qr/{barkod}'>QR indir</a>"

    depo_options = "".join([f"<option>{d}</option>" for d in DEPOLAR])

    return f"""
    <h2>ÜRÜN EKLE</h2>
    <form method=post>
    Ad: <input name=name><br>
    Cins: <input name=cins><br>
    Ebat(mm): <input name=ebat><br>
    Sınıf: <input name=sinif><br>
    HG/MAT: <input name=hg><br>
    Renk: <input name=renk><br>
    Adet: <input name=adet><br>
    Depo: <select name=depo>{depo_options}</select><br>
    <button>KAYDET</button>
    </form>
    """

# 📷 QR
@app.route("/qr/<barkod>")
def qr(barkod):
    return send_file(f"{barkod}.png", mimetype='image/png')

# 📦 LİSTE
@app.route("/liste")
def liste():
    conn = db()
    c = conn.cursor()
    data = c.execute("SELECT * FROM products").fetchall()
    conn.close()

    html = "<h2>STOK</h2>"
    for i in data:
        html += f"{i[1]} | {i[2]} | {i[3]}mm | {i[5]} | {i[6]} | {i[7]} adet | {i[8]}<br>"
    return html

# 📱 BARKOD OKUT
@app.route("/okut", methods=["GET","POST"])
def okut():
    if session.get("role") != "depocu":
        return "Yetki yok"

    if request.method == "POST":
        barkod = request.form["barkod"]
        adet = int(request.form["adet"])

        conn = db()
        c = conn.cursor()
        urun = c.execute("SELECT * FROM products WHERE barcode=?", (barkod,)).fetchone()

        if not urun:
            return "❌ Ürün bulunamadı"

        if urun[7] < adet:
            return "❌ Yetersiz stok"

        yeni = urun[7] - adet

        c.execute("UPDATE products SET adet=? WHERE barcode=?", (yeni, barkod))

        c.execute("""INSERT INTO hareket VALUES(NULL,?,?,?,?,?,?)""",(
            session["user"], "ÇIKIŞ", urun[1], adet, urun[8],
            datetime.datetime.now().strftime("%H:%M:%S")
        ))

        conn.commit()
        conn.close()

        return f"✅ Çıkış yapıldı | Kalan: {yeni}"

    return """
    <h2>BARKOD OKUT</h2>
    <form method=post>
    Barkod: <input name=barkod><br>
    Adet: <input name=adet><br>
    <button>ÇIKIŞ YAP</button>
    </form>
    """

# 📋 HAREKET
@app.route("/hareket")
def hareket():
    conn = db()
    c = conn.cursor()
    data = c.execute("SELECT * FROM hareket").fetchall()
    conn.close()

    html = "<h2>HAREKET</h2>"
    for i in data:
        html += f"{i[1]} | {i[2]} | {i[3]} | {i[4]} adet | {i[5]} | {i[6]}<br>"
    return html

# 🚪 ÇIKIŞ
@app.route("/cikis")
def cikis():
    session.clear()
    return redirect("/")

# 🚀 RUN
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
