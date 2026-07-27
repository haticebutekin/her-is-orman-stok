from flask import Flask, request, redirect, session, send_file, render_template_string
import sqlite3, os, datetime, uuid
import qrcode
from barcode import Code128
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = "12345"

DB = "stok.db"

# ----------------- SABİT DEPOLAR -----------------
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

# ----------------- DB -----------------
def db():
    return sqlite3.connect(DB)

def kur():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS urunler(
        id INTEGER PRIMARY KEY,
        barkod TEXT,
        ad TEXT,
        cins TEXT,
        ebat TEXT,
        kalinlik TEXT,
        sinif TEXT,
        yuzey TEXT,
        renk TEXT,
        adet INTEGER,
        depo TEXT
        )
        """)

        con.execute("""
        CREATE TABLE IF NOT EXISTS hareket(
        id INTEGER PRIMARY KEY,
        barkod TEXT,
        islem TEXT,
        adet INTEGER,
        kullanici TEXT,
        tarih TEXT
        )
        """)

kur()

# ----------------- BARKOD -----------------
def yeni_barkod():
    return "HER-" + str(uuid.uuid4().hex[:6]).upper()

def barkod_uret(kod):
    path = f"static/{kod}.png"
    Code128(kod, writer=ImageWriter()).write(open(path, "wb"))
    return path

def qr_uret(kod):
    path = f"static/{kod}_qr.png"
    img = qrcode.make(kod)
    img.save(path)
    return path

# ----------------- LOGIN -----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        k = request.form["k"]
        s = request.form["s"]

        if k == "admin" and s == "123":
            session["user"] = "admin"
            return redirect("/panel")

        if k == "depo" and s == "123":
            session["user"] = "depo"
            return redirect("/okut")

    return """
    <h2>GİRİŞ</h2>
    <form method=post>
    Kullanıcı: <input name=k><br>
    Şifre: <input name=s type=password><br>
    <button>GİR</button>
    </form>
    """

# ----------------- PANEL -----------------
@app.route("/panel")
def panel():
    if session.get("user") != "admin":
        return redirect("/")

    return """
    <h1>STOK PANEL</h1>
    <a href=/urun>Ekle</a><br>
    <a href=/stok>Stok</a><br>
    <a href=/hareket>Hareket</a><br>
    """

# ----------------- ÜRÜN EKLE -----------------
@app.route("/urun", methods=["GET","POST"])
def urun():
    if session.get("user") != "admin":
        return redirect("/")

    if request.method == "POST":
        kod = yeni_barkod()
        barkod_uret(kod)
        qr_uret(kod)

        data = (
            kod,
            request.form["ad"],
            request.form["cins"],
            request.form["ebat"],
            request.form["kalinlik"],
            request.form["sinif"],
            request.form["yuzey"],
            request.form["renk"],
            int(request.form["adet"]),
            request.form["depo"]
        )

        with db() as con:
            con.execute("""
            INSERT INTO urunler(
            barkod,ad,cins,ebat,kalinlik,sinif,yuzey,renk,adet,depo
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """, data)

        return f"OK <br><img src='/static/{kod}.png'><br><img src='/static/{kod}_qr.png'>"

    depo_html = "".join([f"<option>{d}</option>" for d in DEPOLAR])

    return f"""
    <h2>ÜRÜN KARTI</h2>
    <form method=post>
    Ad <input name=ad><br>
    Cins <input name=cins><br>
    Ebat <input name=ebat><br>
    Kalınlık <input name=kalinlik><br>
    Sınıf <input name=sinif><br>

    HG/MAT
    <select name=yuzey>
        <option>HG</option>
        <option>MAT</option>
    </select><br>

    Renk <input name=renk><br>
    Adet <input name=adet><br>

    Depo
    <select name=depo>{depo_html}</select><br>

    <button>EKLE</button>
    </form>
    """

# ----------------- STOK -----------------
@app.route("/stok")
def stok():
    with db() as con:
        urun = con.execute("SELECT * FROM urunler").fetchall()

    html = "<h2>STOK</h2>"
    for u in urun:
        html += f"{u[1]} | {u[2]} | {u[9]} adet<br>"

    return html

# ----------------- BARKOD OKUT -----------------
@app.route("/okut", methods=["GET","POST"])
def okut():
    if session.get("user") not in ["admin","depo"]:
        return redirect("/")

    if request.method == "POST":
        kod = request.form["kod"]

        with db() as con:
            u = con.execute("SELECT * FROM urunler WHERE barkod=?",(kod,)).fetchone()

        if not u:
            return "❌ Ürün yok!"

        return f"""
        <h3>{u[2]}</h3>
        Cins: {u[3]}<br>
        Ebat: {u[4]}<br>
        Yüzey: {u[6]}<br>
        Renk: {u[7]}<br>
        Depo: {u[9]}<br>

        <form action='/cikis' method=post>
        <input type=hidden name=kod value='{kod}'>
        Adet <input name=adet><br>
        <button>ÇIKIŞ YAP</button>
        </form>
        """

    return """
    <h2>BARKOD OKUT</h2>
    <form method=post>
    Barkod <input name=kod>
    <button>OKUT</button>
    </form>
    """

# ----------------- ÇIKIŞ -----------------
@app.route("/cikis", methods=["POST"])
def cikis():
    kod = request.form["kod"]
    adet = int(request.form["adet"])

    with db() as con:
        u = con.execute("SELECT adet FROM urunler WHERE barkod=?",(kod,)).fetchone()

        if not u:
            return "YOK"

        if u[0] < adet:
            return "YETERSİZ STOK"

        con.execute("UPDATE urunler SET adet=adet-? WHERE barkod=?", (adet,kod))

        con.execute("""
        INSERT INTO hareket(barkod,islem,adet,kullanici,tarih)
        VALUES(?,?,?,?,?)
        """,(kod,"ÇIKIŞ",adet,session.get("user"),datetime.datetime.now()))

    return "OK"

# ----------------- HAREKET -----------------
@app.route("/hareket")
def hareket():
    with db() as con:
        h = con.execute("SELECT * FROM hareket ORDER BY id DESC").fetchall()

    html = "<h2>HAREKET</h2>"
    for x in h:
        html += f"{x[1]} | {x[2]} | {x[3]} | {x[4]} | {x[5]}<br>"

    return html

# ----------------- RUN -----------------
if __name__ == "__main__":
    os.makedirs("static", exist_ok=True)
    app.run(debug=True)
