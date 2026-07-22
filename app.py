import sqlite3
import random
from flask import Flask, render_template_string, request, redirect, session
from escpos.printer import Usb

app = Flask(__name__)
app.secret_key = "1234"

# -------- DATABASE --------
conn = sqlite3.connect("kasa.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS urun (
id INTEGER PRIMARY KEY,
ad TEXT,
marka TEXT,
sinif TEXT,
fiyat REAL,
barkod TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS satis (
id INTEGER PRIMARY KEY,
urun TEXT,
fiyat REAL
)""")
conn.commit()


# -------- BARKOD --------
def barkod_uret():
    return str(random.randint(1000000000000, 9999999999999))


# -------- FİŞ YAZDIR --------
def fis_yaz(urunler):
    try:
        p = Usb(0x04b8, 0x0202)  # USB yazıcı ID (gerekirse değiştir)
        p.text("=== SATIS FISI ===\n")
        toplam = 0

        for u in urunler:
            p.text(f"{u[0]} - {u[1]} TL\n")
            toplam += u[1]

        p.text("-------------------\n")
        p.text(f"TOPLAM: {toplam} TL\n")
        p.cut()
    except:
        print("Yazıcı bağlanamadı")


# -------- ADMIN --------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form["sifre"] == "1234":
            session["admin"] = True
            return redirect("/panel")

    return """
    <h2>Admin Giriş</h2>
    <form method="post">
    Şifre: <input type="password" name="sifre">
    <button>Giriş</button>
    </form>
    """


# -------- PANEL --------
@app.route("/panel", methods=["GET", "POST"])
def panel():
    if not session.get("admin"):
        return redirect("/admin")

    if request.method == "POST":
        barkod = barkod_uret()

        c.execute("INSERT INTO urun VALUES (NULL,?,?,?,?,?)", (
            request.form["ad"],
            request.form["marka"],
            request.form["sinif"],
            request.form["fiyat"],
            barkod
        ))
        conn.commit()

    urunler = c.execute("SELECT * FROM urun").fetchall()

    html = """
    <h2>ÜRÜN EKLE</h2>
    <form method="post">
    Ad: <input name="ad"><br>
    Marka: <input name="marka"><br>
    Sınıf: <input name="sinif"><br>
    Fiyat: <input name="fiyat"><br>
    <button>Ekle</button>
    </form>

    <h3>ÜRÜNLER</h3>
    """

    for u in urunler:
        html += f"{u[1]} | {u[2]} | {u[3]} | {u[4]} TL | Barkod: {u[5]}<br>"

    return html


# -------- KASA --------
sepet = []

@app.route("/", methods=["GET", "POST"])
def kasa():
    global sepet

    if request.method == "POST":
        barkod = request.form["barkod"]

        urun = c.execute("SELECT * FROM urun WHERE barkod=?", (barkod,)).fetchone()

        if urun:
            sepet.append((urun[1], urun[4]))
            c.execute("INSERT INTO satis VALUES (NULL,?,?)", (urun[1], urun[4]))
            conn.commit()

    html = """
    <h1>KASA</h1>

    <form method="post">
    Barkod: <input name="barkod" autofocus>
    <button>EKLE</button>
    </form>

    <h3>SEPET</h3>
    """

    toplam = 0
    for s in sepet:
        html += f"{s[0]} - {s[1]} TL<br>"
        toplam += s[1]

    html += f"<h2>TOPLAM: {toplam} TL</h2>"

    html += """
    <form action="/odeme">
    <button>SATIŞ TAMAMLA</button>
    </form>
    """

    return html


# -------- ÖDEME --------
@app.route("/odeme")
def odeme():
    global sepet
    fis_yaz(sepet)
    sepet = []
    return "<h2>Satış Tamamlandı</h2><a href='/'>Geri</a>"


# -------- RAPOR --------
@app.route("/rapor")
def rapor():
    data = c.execute("SELECT urun, COUNT(*) FROM satis GROUP BY urun").fetchall()

    html = "<h2>Satış Raporu</h2>"

    for d in data:
        html += f"{d[0]} : {d[1]} adet<br>"

    return html


# -------- RUN --------
app.run(host="0.0.0.0", port=5000)
