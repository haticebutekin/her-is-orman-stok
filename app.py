from flask import Flask, request, redirect, session, render_template_string, send_file
import sqlite3, os, datetime
from barcode import Code128
from barcode.writer import ImageWriter
from openpyxl import Workbook

app = Flask(__name__)
app.secret_key = "12345"

DB = "stok.db"
STATIC = "static"

if not os.path.exists(STATIC):
    os.makedirs(STATIC)

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
    s = cur.fetchone()[0] + 1
    return f"HER-{str(s).zfill(6)}"

def barkod_olustur(kod):
    path = f"{STATIC}/{kod}.png"
    if not os.path.exists(path):
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
            int(request.form["adet"]),
            request.form["depo"],
            str(datetime.datetime.now())
        )

        con = db()
        cur = con.cursor()
        cur.execute("INSERT INTO urunler VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?)", data)
        cur.execute("INSERT INTO hareketler VALUES(NULL,?,?,?,?)",
                    (barkod,"GİRİŞ",data[8],data[10]))
        con.commit()
        con.close()

    con = db()
    cur = con.cursor()
    urunler = cur.execute("SELECT * FROM urunler ORDER BY id DESC").fetchall()
    con.close()

    return render_template_string("""
    <h2>HER İŞ ORMAN STOK PRO</h2>

    <form method=post style="border:1px solid #ccc;padding:10px">
    <b>ÜRÜN EKLE</b><br><br>

    İsim <input name=isim required><br>
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
    Adet <input name=adet type=number required><br>

    Depo:
    <select name=depo>
    {% for d in depolar %}
        <option>{{d}}</option>
    {% endfor %}
    </select><br><br>

    <button>EKLE</button>
    </form>

    <hr>

    <a href="/kamera">📷 Kamera</a> |
    <a href="/excel">📊 Excel</a>

    <hr>

    <table border=1 cellpadding=5>
    <tr>
    <th>Barkod</th>
    <th>İsim</th>
    <th>Adet</th>
    <th>Depo</th>
    <th>İşlem</th>
    </tr>

    {% for u in urunler %}
    <tr>
        <td>
        {{u[1]}}<br>
        <img src="/static/{{u[1]}}.png" width=120>
        </td>
        <td>{{u[2]}}</td>
        <td>{{u[9]}}</td>
        <td>{{u[10]}}</td>
        <td>
            <a href="/arttir/{{u[1]}}">➕</a>
            <a href="/azalt/{{u[1]}}">➖</a>
        </td>
    </tr>
    {% endfor %}
    </table>
    """, urunler=urunler, depolar=DEPOLAR)

# ARTIR
@app.route("/arttir/<kod>")
def arttir(kod):
    con = db()
    cur = con.cursor()

    cur.execute("UPDATE urunler SET adet = adet + 1 WHERE barkod=?", (kod,))
    cur.execute("INSERT INTO hareketler VALUES(NULL,?,?,?,?)",
                (kod,"GİRİŞ",1,str(datetime.datetime.now())))
    con.commit()
    con.close()

    return redirect("/panel")

# AZALT
@app.route("/azalt/<kod>")
def azalt(kod):
    con = db()
    cur = con.cursor()

    cur.execute("SELECT adet FROM urunler WHERE barkod=?", (kod,))
    veri = cur.fetchone()

    if veri:
        yeni = max(veri[0]-1,0)
        cur.execute("UPDATE urunler SET adet=? WHERE barkod=?", (yeni,kod))
        cur.execute("INSERT INTO hareketler VALUES(NULL,?,?,?,?)",
                    (kod,"ÇIKIŞ",1,str(datetime.datetime.now())))
        con.commit()

    con.close()
    return redirect("/panel")

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
            window.location = "/azalt/" + result.text
        }
    })
    </script>
    """

# EXCEL
@app.route("/excel")
def excel():
    con = db()
    cur = con.cursor()
    data = cur.execute("SELECT * FROM urunler").fetchall()
    con.close()

    wb = Workbook()
    ws = wb.active

    for r in data:
        ws.append(r)

    file = "stok.xlsx"
    wb.save(file)
    return send_file(file, as_attachment=True)

# RUN
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
