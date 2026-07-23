from flask import Flask, request, redirect, session, send_file
import sqlite3, os
from datetime import datetime
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw

app = Flask(__name__)
app.secret_key = "1234"
DB = "stok.db"

# ---------------- ÜRÜN LİSTESİ ----------------
URUNLER = [
    {"marka":"VARIO","seri":"AİRLAM","model":"ATLANTİK ÇAM","yuzey":"MAT"},
    {"marka":"VARIO","seri":"AİRLAM","model":"BAMBU","yuzey":"MAT"},
    {"marka":"STRWD","seri":"MEGALAM","model":"AFRİKA","yuzey":"MAT"},
    {"marka":"STRWD","seri":"MEGALAM","model":"ATLAS","yuzey":"MAT"},
    {"marka":"STRWD","seri":"MEGALAM","model":"ANTRASİT GRİ","yuzey":"MAT"},
    {"marka":"VARIO","seri":"SMARTLAM","model":"KARBON GRİ","yuzey":"NATURAL"},
    {"marka":"VARIO","seri":"SMARTLAM","model":"TEAK","yuzey":"MAT"},
]

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, username TEXT, password TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS stok (
        id INTEGER PRIMARY KEY,
        barkod TEXT,
        urun TEXT,
        mm TEXT,
        ebat TEXT,
        yuzey TEXT,
        adet INTEGER)""")

    c.execute("""CREATE TABLE IF NOT EXISTS hareket (
        id INTEGER PRIMARY KEY,
        barkod TEXT,
        islem TEXT,
        adet INTEGER,
        personel TEXT,
        tarih TEXT)""")

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
def etiket_yap(kod, urun, mm, ebat, yuzey):
    barkod_path = barkod_png(kod)

    img = Image.new('RGB', (600,350), "white")
    draw = ImageDraw.Draw(img)

    draw.text((20,20), urun, fill="black")
    draw.text((20,70), f"{mm}mm  {ebat}", fill="black")
    draw.text((20,110), f"Yüzey: {yuzey}", fill="black")

    barkod_img = Image.open(barkod_path)
    img.paste(barkod_img.resize((450,130)), (70,180))

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
        if c.fetchone():
            session["user"] = u
            return redirect("/panel")

    return """
    <h2>Giriş</h2>
    <form method="post">
    Kullanıcı <input name=user><br>
    Şifre <input name=pass type=password><br>
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
    <h2>Stok Panel</h2>

    <button onclick="startScanner()">📷 Barkod Oku</button>
    <video id="reader" width="300"></video>

    <script src="https://unpkg.com/html5-qrcode"></script>
    <script>
    function startScanner(){
        const html5QrCode = new Html5Qrcode("reader");
        html5QrCode.start(
            { facingMode: "environment" },
            { fps: 10 },
            (decodedText) => {
                beep();
                window.location="/scan/"+decodedText;
            }
        );
    }

    function beep(){
        let ctx=new AudioContext();
        let o=ctx.createOscillator();
        o.connect(ctx.destination);
        o.start();
        o.stop(ctx.currentTime+0.1);
    }
    </script>

    <br><a href="/ekle">+ Ürün</a>
    <table border=1>
    <tr>
    <th>Barkod</th><th>Ürün</th><th>MM</th><th>Ebat</th><th>Yüzey</th><th>Adet</th><th>İşlem</th>
    </tr>
    """

    for d in data:
        html += f"""
        <tr>
        <td>{d[1]}</td>
        <td>{d[2]}</td>
        <td>{d[3]}</td>
        <td>{d[4]}</td>
        <td>{d[5]}</td>
        <td>{d[6]}</td>
        <td>
            <a href="/art/{d[1]}">+</a>
            <a href="/azal/{d[1]}">-</a>
            <a href="/etiket/{d[1]}">🧾 Etiket</a>
        </td>
        </tr>
        """

    html += "</table>"
    return html

# ---------------- ÜRÜN EKLE ----------------
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method == "POST":
        barkod = barkod_olustur()
        secilen = int(request.form["urun"])
        u = URUNLER[secilen]

        urun_ad = f"{u['marka']} {u['model']} ({u['seri']})"

        mm = "18"
        ebat = "210x280"
        adet = int(request.form["adet"])

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute("INSERT INTO stok VALUES(NULL,?,?,?,?,?,?)",
                  (barkod,urun_ad,mm,ebat,u["yuzey"],adet))

        conn.commit()
        conn.close()

        return redirect("/panel")

    html = "<h2>Ürün Ekle</h2><form method=post>"

    html += "<select name='urun'>"
    for i,u in enumerate(URUNLER):
        html += f"<option value='{i}'>{u['marka']} - {u['model']} ({u['seri']})</option>"
    html += "</select><br>"

    html += "Adet <input name=adet><br>"
    html += "<button>Ekle</button></form>"

    return html

# ---------------- STOK ----------------
def stok_degistir(kod, miktar):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("UPDATE stok SET adet = adet + ? WHERE barkod=?", (miktar,kod))
    c.execute("INSERT INTO hareket VALUES(NULL,?,?,?,?,?)",
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

# ---------------- SCAN ----------------
@app.route("/scan/<kod>")
def scan(kod):
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

    path = etiket_yap(kod,d[2],d[3],d[4],d[5])
    return send_file(path, as_attachment=True)

# ---------------- RUN ----------------
if __name__ == "__main__":
    os.makedirs("static", exist_ok=True)
    app.run(host="0.0.0.0", port=5000)
