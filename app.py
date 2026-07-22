from flask import Flask, render_template_string, request, redirect, session, send_file
import sqlite3, os
from datetime import datetime
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw

app = Flask(__name__)
app.secret_key = "secret123"

DB = "stok.db"

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS stok (
        id INTEGER PRIMARY KEY,
        barkod TEXT,
        cins TEXT,
        mm TEXT,
        ebat TEXT,
        yuzey TEXT,
        adet INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS hareket (
        id INTEGER PRIMARY KEY,
        barkod TEXT,
        islem TEXT,
        adet INTEGER,
        personel TEXT,
        tarih TEXT
    )
    """)

    # default user
    c.execute("INSERT OR IGNORE INTO users VALUES (1,'admin','1234')")
    conn.commit()
    conn.close()

init_db()

# ---------------- BARKOD ----------------
def barkod_olustur():
    return str(int(datetime.now().timestamp()))

def barkod_png(kod):
    ean = barcode.get('code128', kod, writer=ImageWriter())
    path = f"static/{kod}"
    ean.save(path)
    return path + ".png"

# ---------------- ETIKET ----------------
def etiket_olustur(kod, cins, mm, ebat, yuzey):
    img = Image.new('RGB', (400,200), "white")
    draw = ImageDraw.Draw(img)

    draw.text((10,10), f"{cins}", fill="black")
    draw.text((10,40), f"{mm}mm - {ebat}", fill="black")
    draw.text((10,70), f"{yuzey}", fill="black")
    draw.text((10,120), f"Barkod: {kod}", fill="black")

    path = f"static/etiket_{kod}.png"
    img.save(path)
    return path

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["user"]
        p = request.form["pass"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = u
            return redirect("/panel")

    return """
    <h2>Giriş</h2>
    <form method="post">
        Kullanıcı: <input name="user"><br>
        Şifre: <input name="pass" type="password"><br>
        <button>Giriş</button>
    </form>
    """

# ---------------- PANEL ----------------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM stok")
    data = c.fetchall()
    conn.close()

    html = """
    <h2>Stok Paneli</h2>
    <a href="/ekle">+ Ürün Ekle</a>
    <table border=1>
    <tr>
    <th>Barkod</th><th>Cins</th><th>MM</th><th>Ebat</th><th>Yüzey</th><th>Adet</th><th>İşlem</th>
    </tr>
    """

    for d in data:
        uyari = "❗" if d[6] <= 0 else ""
        html += f"""
        <tr>
        <td>{d[1]}</td>
        <td>{d[2]}</td>
        <td>{d[3]}</td>
        <td>{d[4]}</td>
        <td>{d[5]}</td>
        <td>{d[6]} {uyari}</td>
        <td>
            <a href="/art/{d[1]}">+</a>
            <a href="/azal/{d[1]}">-</a>
            <a href="/etiket/{d[1]}">Etiket</a>
        </td>
        </tr>
        """

    html += "</table>"
    return html

# ---------------- EKLE ----------------
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method == "POST":
        cins = request.form["cins"]
        mm = request.form["mm"]
        ebat = request.form["ebat"]
        yuzey = request.form["yuzey"]
        adet = int(request.form["adet"])

        barkod = barkod_olustur()
        barkod_png(barkod)

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO stok VALUES (NULL,?,?,?,?,?,?)",
                  (barkod,cins,mm,ebat,yuzey,adet))
        conn.commit()
        conn.close()

        return redirect("/panel")

    return """
    <h2>Ürün Ekle</h2>
    <form method="post">
    Cins:
    <select name="cins">
        <option>Glosslak</option>
        <option>Vario</option>
        <option>Kapı</option>
        <option>MDF Lam</option>
        <option>Ham MDF</option>
        <option>Arkalık</option>
    </select><br>

    MM: <input name="mm"><br>
    Ebat: <input name="ebat"><br>

    Yüzey:
    <select name="yuzey">
        <option>HG</option>
        <option>Mat</option>
    </select><br>

    Adet: <input name="adet"><br>

    <button>Ekle</button>
    </form>
    """

# ---------------- ART / AZAL ----------------
def stok_degistir(kod, miktar):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("UPDATE stok SET adet = adet + ? WHERE barkod=?", (miktar,kod))
    c.execute("INSERT INTO hareket VALUES (NULL,?,?,?,?,?)",
              (kod,"degisim",miktar,session["user"],str(datetime.now())))
    conn.commit()
    conn.close()

@app.route("/art/<kod>")
def art(kod):
    stok_degistir(kod,1)
    return redirect("/panel")

@app.route("/azal/<kod>")
def azal(kod):
    stok_degistir(kod,-1)
    return redirect("/panel")

# ---------------- ETIKET ----------------
@app.route("/etiket/<kod>")
def etiket(kod):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM stok WHERE barkod=?", (kod,))
    d = c.fetchone()
    conn.close()

    path = etiket_olustur(kod,d[2],d[3],d[4],d[5])
    return send_file(path, as_attachment=True)

# ---------------- RUN ----------------
if __name__ == "__main__":
    os.makedirs("static", exist_ok=True)
    app.run(host="0.0.0.0", port=5000)
