from flask import Flask, request, redirect, session, render_template_string, send_file
import sqlite3, os, datetime
from barcode import Code128
from barcode.writer import ImageWriter
from openpyxl import Workbook

app = Flask(__name__)
app.secret_key = "12345"

DB = "stok.db"
STATIC = "static"

# STATIC klasör fix
if not os.path.exists(STATIC):
    os.makedirs(STATIC)

# DEPOLAR
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

# DB
def db():
    return sqlite3.connect(DB)

def init_db():
    con = db()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS urunler (
        id INTEGER PRIMARY KEY,
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
    cur.execute("""
    CREATE TABLE IF NOT EXISTS hareketler (
        id INTEGER PRIMARY KEY,
        barkod TEXT,
        islem TEXT,
        adet INTEGER,
        tarih TEXT
    )
    """)
    con.commit()
    con.close()

init_db()

# BARKOD
def yeni_barkod():
    con = db()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM urunler")
    sayi = cur.fetchone()[0] + 1
    return f"HER-{str(sayi).zfill(6)}"

def barkod_olustur(kod):
    path = f"{STATIC}/{kod}.png"
    Code128(kod, writer=ImageWriter()).write(open(path, "wb"))
    return path

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["user"] == "admin" and request.form["pass"] == "123":
            session["login"] = True
            return redirect("/panel")
    return """
    <h2>HER İŞ ORMAN STOK PRO</h2>
    <form method=post>
    Kullanıcı: <input name=user><br>
    Şifre: <input name=pass type=password><br>
    <button>Giriş</button>
    </form>
    """

# PANEL
@app.route("/panel", methods=["GET","POST"])
def panel():
    if not session.get("login"):
        return redirect("/")

    if request.method == "POST":
        barkod = yeni_barkod()
        barkod_olustur(barkod)

        data = (
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
            str(datetime.datetime.now())
        )

        con = db()
        cur = con.cursor()
        cur.execute("INSERT INTO urunler VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?)", data)
        con.commit()
        con.close()

    con = db()
    cur = con.cursor()
    urunler = cur.execute("SELECT * FROM urunler").fetchall()
    con.close()

    return render_template_string("""
    <h2>STOK PANEL</h2>

    <form method=post>
    İsim <input name=isim><br>
    Cins <input name=cins><br>
    Ebat <input name=ebat><br>
    Kalınlık <input name=kalinlik><br>
    Sınıf <input name=sinif><br>

    Yüzey:
    <select name=yuzey>
        <option>HG</option>
        <option>MAT</option>
    </select><br>

    Renk <input name=renk><br>
    Adet <input name=adet type=number><br>

    Depo:
    <select name=depo>
    {% for d in depolar %}
        <option>{{d}}</option>
    {% endfor %}
    </select><br>

    <button>EKLE</button>
    </form>

    <hr>

    <a href="/kamera">📷 Kamera</a> |
    <a href="/excel">📊 Excel</a>

    <table border=1>
    <tr><th>Barkod</th><th>İsim</th><th>Adet</th><th>Depo</th></tr>
    {% for u in urunler %}
    <tr>
        <td>{{u[1]}}</td>
        <td>{{u[2]}}</td>
        <td>{{u[9]}}</td>
        <td>{{u[10]}}</td>
    </tr>
    {% endfor %}
    </table>
    """, urunler=urunler, depolar=DEPOLAR)

# KAMERA
@app.route("/kamera")
def kamera():
    return """
    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <video id="video" width="300"></video>

    <script>
    const codeReader = new ZXing.BrowserBarcodeReader()
    codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {
        if (result) {
            window.location = "/stok/" + result.text
        }
    })
    </script>
    """

# STOK DÜŞ
@app.route("/stok/<kod>")
def stok(kod):
    con = db()
    cur = con.cursor()

    cur.execute("SELECT adet FROM urunler WHERE barkod=?", (kod,))
    veri = cur.fetchone()

    if veri:
        yeni = veri[0] - 1
        if yeni < 0: yeni = 0

        cur.execute("UPDATE urunler SET adet=? WHERE barkod=?", (yeni, kod))

        cur.execute("INSERT INTO hareketler VALUES(NULL,?,?,?,?)",
                    (kod, "ÇIKIŞ", 1, str(datetime.datetime.now())))

        con.commit()

    con.close()
    return redirect("/panel")

# EXCEL
@app.route("/excel")
def excel():
    con = db()
    cur = con.cursor()
    data = cur.execute("SELECT * FROM urunler").fetchall()
    con.close()

    wb = Workbook()
    ws = wb.active

    for row in data:
        ws.append(row)

    file = "stok.xlsx"
    wb.save(file)
    return send_file(file, as_attachment=True)

# RUN (RENDER FIX)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
