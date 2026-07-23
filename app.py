from flask import Flask, request, session, redirect
import sqlite3
import pandas as pd
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "1234"

PERSONELLER = {
    "BEHİÇ": "123",
    "RAMAZAN": "123",
    "ORHAN": "123"
}

def db():
    return sqlite3.connect("stok.db")

# DB oluştur
def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS urun(
        barkod TEXT PRIMARY KEY,
        ad TEXT,
        cins TEXT,
        ebat TEXT,
        sinif TEXT,
        renk TEXT,
        yuzey TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS hareket(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barkod TEXT,
        personel TEXT,
        depo TEXT,
        miktar INTEGER
    )""")

    con.commit()
    con.close()

init_db()

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = request.form["user"]
        sifre = request.form["sifre"]

        if user in PERSONELLER and PERSONELLER[user] == sifre:
            session["user"] = user
            return redirect("/panel")
        return "HATALI GİRİŞ"

    return """
    <h2>Personel Giriş</h2>
    <form method="post">
    Kullanıcı: <select name="user">
    <option>BEHİÇ</option>
    <option>RAMAZAN</option>
    <option>ORHAN</option>
    </select><br>
    Şifre: <input type="password" name="sifre"><br>
    <button>Giriş</button>
    </form>
    """

# PANEL
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    return """
    <h2>Stok Panel</h2>

    <form method="post" action="/ekle">
    Barkod: <input name="barkod"><br>
    Ad: <input name="ad"><br>
    Cins: <input name="cins"><br>
    Ebat: <input name="ebat"><br>
    Sınıf: <input name="sinif"><br>
    Renk: <input name="renk"><br>
    Yüzey(mm/hg/mat): <input name="yuzey"><br>
    <button>Ürün Ekle</button>
    </form>

    <hr>

    <form method="post" action="/stok">
    Barkod: <input name="barkod" id="barkod"><br>
    Depo:
    <select name="depo">
    <option>ANA DEPO</option>
    <option>ŞANTİYE</option>
    </select><br>
    Miktar: <input name="miktar"><br>
    <button>Stok Hareketi</button>
    </form>

    <hr>

    <video id="video" width="300" height="200" autoplay></video>

    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <script>
    const codeReader = new ZXing.BrowserBarcodeReader();
    codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {
        if (result) {
            document.getElementById('barkod').value = result.text;
        }
    });
    </script>

    <hr>
    <a href="/rapor">Excel Rapor</a>
    """

# ÜRÜN EKLE
@app.route("/ekle", methods=["POST"])
def ekle():
    con = db()
    con.execute("INSERT INTO urun VALUES (?,?,?,?,?,?,?)", (
        request.form["barkod"],
        request.form["ad"],
        request.form["cins"],
        request.form["ebat"],
        request.form["sinif"],
        request.form["renk"],
        request.form["yuzey"]
    ))
    con.commit()
    return "ÜRÜN EKLENDİ"

# STOK HAREKET
@app.route("/stok", methods=["POST"])
def stok():
    if "user" not in session:
        return redirect("/")

    barkod = request.form["barkod"]
    miktar = request.form["miktar"]
    depo = request.form["depo"]
    personel = session["user"]

    con = db()
    urun = con.execute("SELECT * FROM urun WHERE barkod=?", (barkod,)).fetchone()

    if not urun:
        return "BU BARKOD YOK!"

    con.execute("INSERT INTO hareket (barkod,personel,depo,miktar) VALUES (?,?,?,?)",
                (barkod,personel,depo,miktar))
    con.commit()

    return f"OK -> {urun[1]} | {personel}"

# PDF ETİKET
@app.route("/etiket/<barkod>")
def etiket(barkod):
    con = db()
    urun = con.execute("SELECT * FROM urun WHERE barkod=?", (barkod,)).fetchone()

    if not urun:
        return "ÜRÜN YOK"

    dosya = f"{barkod}.pdf"
    doc = SimpleDocTemplate(dosya)
    styles = getSampleStyleSheet()

    content = []
    for i in urun:
        content.append(Paragraph(str(i), styles["Normal"]))

    doc.build(content)

    return f"PDF oluşturuldu: {dosya}"

# EXCEL RAPOR
@app.route("/rapor")
def rapor():
    con = db()
    data = con.execute("SELECT * FROM hareket").fetchall()

    df = pd.DataFrame(data, columns=["ID","Barkod","Personel","Depo","Miktar"])
    df.to_excel("rapor.xlsx", index=False)

    return "Excel hazır: rapor.xlsx"

app.run(debug=True)
