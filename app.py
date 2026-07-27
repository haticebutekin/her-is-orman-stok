from flask import Flask, request, redirect, session, render_template_string, send_file
import sqlite3, os, datetime
import barcode
from barcode.writer import ImageWriter
from openpyxl import Workbook

app = Flask(__name__)
app.secret_key = "pro123"

# ---------------- DB ----------------
def db():
    return sqlite3.connect("stok.db")

def init_db():
    with db() as con:
        # ürün
        con.execute("""
        CREATE TABLE IF NOT EXISTS urunler(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barkod TEXT,
            isim TEXT,
            adet INTEGER,
            depo TEXT
        )
        """)

        # kullanıcı
        con.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT,
            role TEXT
        )
        """)

        # log
        con.execute("""
        CREATE TABLE IF NOT EXISTS log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            islem TEXT,
            barkod TEXT,
            tarih TEXT
        )
        """)

        # default kullanıcılar
        u = con.execute("SELECT * FROM users").fetchall()
        if not u:
            con.execute("INSERT INTO users VALUES (NULL,'admin','123','admin')")
            con.execute("INSERT INTO users VALUES (NULL,'depo','123','depo')")
            con.execute("INSERT INTO users VALUES (NULL,'satis','123','satis')")

init_db()

# ---------------- LOG ----------------
def log_yaz(user, islem, barkod):
    with db() as con:
        con.execute("INSERT INTO log (user,islem,barkod,tarih) VALUES (?,?,?,?)",
                    (user, islem, barkod, str(datetime.datetime.now())))

# ---------------- BARKOD ----------------
def yeni_barkod():
    with db() as con:
        say = con.execute("SELECT COUNT(*) FROM urunler").fetchone()[0]
    return f"HER-{str(say+1).zfill(6)}"

def barkod_olustur(kod):
    os.makedirs("static", exist_ok=True)
    Code128 = barcode.get_barcode_class('code128')
    return Code128(kod, writer=ImageWriter()).save(f"static/{kod}")

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        k = request.form["k"]
        s = request.form["s"]

        with db() as con:
            u = con.execute("SELECT * FROM users WHERE username=? AND password=?", (k,s)).fetchone()

        if u:
            session["g"] = True
            session["user"] = u[1]
            session["role"] = u[3]
            return redirect("/panel")

    return """
    <h2>Giriş</h2>
    <form method="post">
    <input name="k" placeholder="kullanıcı"><br>
    <input name="s" type="password"><br>
    <button>Giriş</button>
    </form>
    """

# ---------------- PANEL ----------------
@app.route("/panel", methods=["GET","POST"])
def panel():
    if not session.get("g"): return redirect("/")

    # EKLE (SADECE ADMIN)
    if request.method == "POST" and session["role"] == "admin":
        kod = yeni_barkod()
        barkod_olustur(kod)

        with db() as con:
            con.execute("INSERT INTO urunler (barkod,isim,adet,depo) VALUES (?,?,?,?)",
                        (kod,
                         request.form["isim"],
                         int(request.form["adet"]),
                         request.form["depo"]))
        log_yaz(session["user"], "URUN_EKLE", kod)

    with db() as con:
        urunler = con.execute("SELECT * FROM urunler ORDER BY id DESC").fetchall()

    return render_template_string("""
    <h2>PANEL ({{session['role']}})</h2>

    {% if session["role"] == "admin" %}
    <form method="post">
    <input name="isim" placeholder="ürün">
    <input name="adet" placeholder="adet">
    <input name="depo" placeholder="depo">
    <button>EKLE</button>
    </form>
    {% endif %}

    <hr>

    {% for u in urunler %}
    <div style="border:1px solid;padding:5px;margin:5px">
    {{u[2]}} | Adet: {{u[3]}} | {{u[4]}} <br>

    {% if u[3] <= 5 %}
    <b style="color:red">DÜŞÜK STOK</b><br>
    {% endif %}

    <a href="/sat/{{u[1]}}">SAT</a>
    </div>
    {% endfor %}

    <a href="/log">LOG</a>
    """, urunler=urunler)

# ---------------- SAT ----------------
@app.route("/sat/<kod>")
def sat(kod):
    if not session.get("g"): return redirect("/")

    with db() as con:
        stok = con.execute("SELECT adet FROM urunler WHERE barkod=?", (kod,)).fetchone()

        if stok and stok[0] > 0:
            con.execute("UPDATE urunler SET adet = adet-1 WHERE barkod=?", (kod,))
            log_yaz(session["user"], "SATIS", kod)

    return redirect("/panel")

# ---------------- LOG SAYFA ----------------
@app.route("/log")
def log():
    with db() as con:
        data = con.execute("SELECT * FROM log ORDER BY id DESC").fetchall()

    return render_template_string("""
    <h2>İŞLEM GEÇMİŞİ</h2>
    {% for l in data %}
    <div>
    {{l[1]}} → {{l[2]}} → {{l[3]}} → {{l[4]}}
    </div>
    {% endfor %}
    """, data=data)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
