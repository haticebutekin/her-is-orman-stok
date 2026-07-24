from flask import Flask, request, redirect, session
import sqlite3
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "HERIS_STOK_PRO_SECRET"

# =====================
# DB
# =====================

def db():
    return sqlite3.connect("stok.db")


def init_db():
    con = db()
    c = con.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS depots(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        type TEXT,
        size TEXT,
        class_name TEXT,
        surface TEXT,
        color TEXT,
        barcode TEXT,
        stock INTEGER,
        depot TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS stock_moves(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        product_id INTEGER,
        product_name TEXT,
        depot TEXT,
        quantity INTEGER,
        date TEXT
    )
    """)

    # kullanıcı
    if c.execute("SELECT * FROM users").fetchone() is None:
        c.execute("INSERT INTO users VALUES(NULL,'admin','1234','admin')")
        c.execute("INSERT INTO users VALUES(NULL,'depocu','1234','depo')")

    # depolar
    depolar = [
        "MDF SATIŞ DEPOSU",
        "LAMİNANT DEPOSU",
        "KAPI DEPOSU",
        "HGLOSS DEPOSU",
        "KESİMHANE"
    ]

    for d in depolar:
        kontrol = c.execute("SELECT * FROM depots WHERE name=?", (d,)).fetchone()
        if kontrol is None:
            c.execute("INSERT INTO depots(name) VALUES(?)", (d,))

    con.commit()
    con.close()

init_db()

# =====================
# YARDIMCI
# =====================

def barkod():
    return str(random.randint(100000000000, 999999999999))


def stok_log(product_id, name, depot, adet, action):
    con = db()
    con.execute("""
    INSERT INTO stock_moves
    (username, action, product_id, product_name, depot, quantity, date)
    VALUES(?,?,?,?,?,?,?)
    """, (
        session.get("user"),
        action,
        product_id,
        name,
        depot,
        adet,
        datetime.now().strftime("%d.%m.%Y %H:%M")
    ))
    con.commit()
    con.close()

# =====================
# LOGIN
# =====================

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        con = db()
        user = con.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (request.form["username"], request.form["password"])
        ).fetchone()
        con.close()

        if user:
            session["user"] = user[1]
            return redirect("/panel")

    return """
    <h2>GİRİŞ</h2>
    <form method="post">
    Kullanıcı: <input name="username"><br><br>
    Şifre: <input name="password" type="password"><br><br>
    <button>GİRİŞ</button>
    </form>
    """

# =====================
# PANEL
# =====================

@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    return """
    <h2>PANEL</h2>
    <a href="/urun">Ürün Ekle</a><br><br>
    <a href="/liste">Liste</a><br><br>
    <a href="/cikis">Depo Çıkış</a>
    """

# =====================
# ÜRÜN EKLE
# =====================

@app.route("/urun", methods=["GET", "POST"])
def urun():
    con = db()
    depolar = con.execute("SELECT name FROM depots").fetchall()

    if request.method == "POST":
        yeni = barkod()

        con.execute("""
        INSERT INTO products
        (name,type,size,class_name,surface,color,barcode,stock,depot)
        VALUES(?,?,?,?,?,?,?,?,?)
        """, (
            request.form["name"],
            request.form["type"],
            request.form["size"],
            request.form["class_name"],
            request.form["surface"],
            request.form["color"],
            yeni,
            request.form["stock"],
            request.form["depot"]
        ))

        con.commit()
        con.close()

        return f"Barkod: {yeni} <br><a href='/panel'>Panel</a>"

    secenek = ""
    for d in depolar:
        secenek += f"<option>{d[0]}</option>"

    return f"""
    <form method="post">
    Ad: <input name="name"><br>
    Cins: <input name="type"><br>
    Ebat: <input name="size"><br>
    Sınıf: <input name="class_name"><br>
    Renk: <input name="color"><br>
    Adet: <input name="stock"><br>
    Depo:
    <select name="depot">{secenek}</select><br><br>
    <button>KAYDET</button>
    </form>
    """

# =====================
# LİSTE
# =====================

@app.route("/liste")
def liste():
    con = db()
    urunler = con.execute("SELECT * FROM products").fetchall()
    con.close()

    html = "<h2>STOK</h2>"
    for u in urunler:
        html += f"<hr>{u[1]} - {u[8]} adet - {u[9]}"

    return html

# =====================
# ÇIKIŞ
# =====================

@app.route("/cikis", methods=["GET", "POST"])
def cikis():
    if request.method == "POST":
        bark = request.form["barcode"]
        adet = int(request.form["adet"])

        con = db()
        urun = con.execute("SELECT * FROM products WHERE barcode=?", (bark,)).fetchone()

        if not urun:
            return "Yok"

        if urun[8] < adet:
            return "Stok yetmez"

        con.execute("UPDATE products SET stock=stock-? WHERE id=?", (adet, urun[0]))
        con.commit()
        con.close()

        stok_log(urun[0], urun[1], urun[9], adet, "ÇIKIŞ")

        return "Çıkış yapıldı <a href='/panel'>Panel</a>"

    return """
    <form method="post">
    Barkod: <input name="barcode"><br>
    Adet: <input name="adet"><br>
    <button>Çıkış</button>
    </form>
    """

# =====================
# RUN
# =====================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
