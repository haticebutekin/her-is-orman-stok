from flask import Flask, request, redirect, session, render_template_string, send_file
import sqlite3, os, datetime
from barcode import Code128
from barcode.writer import ImageWriter
from openpyxl import Workbook

app = Flask(__name__)
app.secret_key = "secret123"

DB = "stok.db"
STATIC = "static"

if not os.path.exists(STATIC):
    os.makedirs(STATIC)

DEPOLAR = [
"MDF SATIŞ DEPOSU","LAMİNANT","KAPI","HGLOSS",
"SÜTÇÜ","HELVACI","RÖTBALANSÇI","KESİMHANE"
]

# DB
def db():
    return sqlite3.connect(DB)

def init():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT,
        role TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS urunler(
        id INTEGER PRIMARY KEY,
        barkod TEXT,
        isim TEXT,
        adet INTEGER,
        depo TEXT,
        kritik INTEGER,
        tarih TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS hareket(
        id INTEGER PRIMARY KEY,
        barkod TEXT,
        tip TEXT,
        adet INTEGER,
        tarih TEXT
    )
    """)

    # admin yoksa oluştur
    cur.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users VALUES(NULL,'admin','123','admin')")

    con.commit()
    con.close()

init()

# BARKOD
def barkod_uret():
    con = db()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM urunler")
    n = cur.fetchone()[0] + 1
    kod = f"HER-{str(n).zfill(6)}"
    path = f"{STATIC}/{kod}.png"
    Code128(kod, writer=ImageWriter()).write(open(path, "wb"))
    return kod

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["user"]
        p = request.form["pass"]

        con = db()
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        user = cur.fetchone()
        con.close()

        if user:
            session["user"] = u
            session["role"] = user[3]
            return redirect("/panel")

    return """
    <h2>GİRİŞ</h2>
    <form method=post>
    Kullanıcı <input name=user><br>
    Şifre <input name=pass type=password><br>
    <button>Giriş</button>
    </form>
    """

# PANEL
@app.route("/panel", methods=["GET","POST"])
def panel():
    if not session.get("user"):
        return redirect("/")

    if request.method == "POST":
        barkod = barkod_uret()
        data = (
            barkod,
            request.form["isim"],
            int(request.form["adet"]),
            request.form["depo"],
            int(request.form["kritik"]),
            str(datetime.datetime.now())
        )

        con = db()
        cur = con.cursor()
        cur.execute("INSERT INTO urunler VALUES(NULL,?,?,?,?,?,?)", data)
        cur.execute("INSERT INTO hareket VALUES(NULL,?,?,?,?)",
                    (barkod,"GİRİŞ",data[2],data[5]))
        con.commit()
        con.close()

    depo_filtre = request.args.get("depo")

    con = db()
    cur = con.cursor()

    if depo_filtre:
        urunler = cur.execute("SELECT * FROM urunler WHERE depo=?", (depo_filtre,)).fetchall()
    else:
        urunler = cur.execute("SELECT * FROM urunler").fetchall()

    con.close()

    return render_template_string("""
    <h2>STOK PANEL</h2>

    <form method=post>
    İsim <input name=isim required>
    Adet <input name=adet type=number required>
    Kritik <input name=kritik type=number value=5>
    Depo <select name=depo>
    {% for d in depolar %}
        <option>{{d}}</option>
    {% endfor %}
    </select>
    <button>EKLE</button>
    </form>

    <hr>

    <a href="/kamera">📷 Kamera</a> |
    <a href="/hareket">📊 Hareket</a> |
    <a href="/excel">Excel</a>

    <hr>

    Filtre:
    {% for d in depolar %}
        <a href="/panel?depo={{d}}">{{d}}</a> |
    {% endfor %}
    <a href="/panel">Hepsi</a>

    <hr>

    <table border=1>
    <tr><th>Barkod</th><th>İsim</th><th>Adet</th><th>Durum</th><th>İşlem</th></tr>

    {% for u in urunler %}
    <tr>
        <td>{{u[1]}}<br><img src="/static/{{u[1]}}.png" width=100></td>
        <td>{{u[2]}}</td>
        <td>{{u[3]}}</td>

        <td>
        {% if u[3] <= u[5] %}
            ⚠ KRİTİK
        {% else %}
            OK
        {% endif %}
        </td>

        <td>
        <a href="/islem/{{u[1]}}/giris">➕</a>
        <a href="/islem/{{u[1]}}/cikis">➖</a>
        </td>
    </tr>
    {% endfor %}
    </table>
    """, urunler=urunler, depolar=DEPOLAR)

# İŞLEM
@app.route("/islem/<kod>/<tip>")
def islem(kod, tip):
    con = db()
    cur = con.cursor()

    cur.execute("SELECT adet FROM urunler WHERE barkod=?", (kod,))
    a = cur.fetchone()[0]

    if tip == "giris":
        yeni = a + 1
    else:
        yeni = max(a-1, 0)

    cur.execute("UPDATE urunler SET adet=? WHERE barkod=?", (yeni,kod))
    cur.execute("INSERT INTO hareket VALUES(NULL,?,?,?,?)",
                (kod,tip.upper(),1,str(datetime.datetime.now())))
    con.commit()
    con.close()

    return redirect("/panel")

# KAMERA
@app.route("/kamera")
def kamera():
    return """
    <h3>Kamera</h3>
    <button onclick="tip='giris'">GİRİŞ</button>
    <button onclick="tip='cikis'">ÇIKIŞ</button>
    <video id="video" width="300"></video>

    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <script>
    let tip = "cikis";
    const codeReader = new ZXing.BrowserBarcodeReader()
    codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {
        if (result) {
            window.location = "/islem/" + result.text + "/" + tip
        }
    })
    </script>
    """

# HAREKET
@app.route("/hareket")
def hareket():
    con = db()
    cur = con.cursor()
    data = cur.execute("SELECT * FROM hareket ORDER BY id DESC").fetchall()
    con.close()

    return render_template_string("""
    <h2>HAREKETLER</h2>
    <a href="/excel_hareket">Excel indir</a>
    <table border=1>
    <tr><th>Barkod</th><th>Tip</th><th>Adet</th><th>Tarih</th></tr>
    {% for h in data %}
    <tr>
        <td>{{h[1]}}</td>
        <td>{{h[2]}}</td>
        <td>{{h[3]}}</td>
        <td>{{h[4]}}</td>
    </tr>
    {% endfor %}
    </table>
    """, data=data)

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

@app.route("/excel_hareket")
def excel_hareket():
    con = db()
    cur = con.cursor()
    data = cur.execute("SELECT * FROM hareket").fetchall()
    con.close()

    wb = Workbook()
    ws = wb.active

    for r in data:
        ws.append(r)

    file = "hareket.xlsx"
    wb.save(file)
    return send_file(file, as_attachment=True)

# RUN
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
