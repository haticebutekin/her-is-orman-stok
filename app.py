from flask import Flask, request, redirect, session, render_template_string, send_file
import sqlite3, os, datetime
from barcode import Code128
from barcode.writer import ImageWriter
from openpyxl import Workbook

app = Flask(__name__)
app.secret_key = "12345"

DB = "stok.db"

# ---------------- DB ----------------
def db():
    return sqlite3.connect(DB)

def init_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS urunler(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        con.execute("""
        CREATE TABLE IF NOT EXISTS hareketler(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barkod TEXT,
            islem TEXT,
            adet INTEGER,
            tarih TEXT
        )
        """)

init_db()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["k"] == "admin" and request.form["s"] == "1234":
            session["ok"] = True
            return redirect("/panel")
    return """
    <h2>HER İŞ ORMAN STOK PRO</h2>
    <form method="post">
    Kullanıcı: <input name="k"><br>
    Şifre: <input name="s" type="password"><br>
    <button>Giriş</button>
    </form>
    """

# ---------------- PANEL ----------------
@app.route("/panel", methods=["GET","POST"])
def panel():
    if not session.get("ok"):
        return redirect("/")

    if request.method == "POST":
        barkod = "HER-" + str(int(datetime.datetime.now().timestamp()))
        isim = request.form["isim"]
        cins = request.form["cins"]
        ebat = request.form["ebat"]
        kalinlik = request.form["kalinlik"]
        sinif = request.form["sinif"]
        yuzey = request.form["yuzey"]
        renk = request.form["renk"]
        adet = int(request.form["adet"])
        depo = request.form["depo"]

        # barkod üret
        Code128(barkod, writer=ImageWriter()).save("static/" + barkod)

        with db() as con:
            con.execute("""
            INSERT INTO urunler(barkod,isim,cins,ebat,kalinlik,sinif,yuzey,renk,adet,depo,tarih)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,(barkod,isim,cins,ebat,kalinlik,sinif,yuzey,renk,adet,depo,str(datetime.datetime.now())))

        return redirect("/panel")

    urunler = db().execute("SELECT * FROM urunler ORDER BY id DESC").fetchall()

    return render_template_string("""
    <h1>HER İŞ ORMAN ÜRÜNLERİ STOK TAKİBİ</h1>

    <form method="post">
    İsim <input name="isim">
    Cins <input name="cins">
    Ebat(mm) <input name="ebat">
    Kalınlık <input name="kalinlik">
    Sınıf <input name="sinif">
    Yüzey 
    <select name="yuzey">
        <option>HG</option>
        <option>MAT</option>
        <option>PARLAK</option>
    </select>
    Renk <input name="renk">
    Adet <input name="adet" type="number">
    Depo 
    <select name="depo">
        <option>MDF SATIŞ DEPOSU</option>
        <option>LAMİNANT DEPOSU</option>
        <option>KAPI DEPOSU</option>
        <option>HGLOSS DEPOSU</option>
        <option>SÜTÇÜ YANI</option>
        <option>HELVACI YANI</option>
        <option>RÖTBALANSÇI YANI</option>
        <option>KESİMHANE</option>
    </select>
    <button>EKLE</button>
    </form>

    <hr>

    <a href="/kamera">📷 Barkod Oku</a> |
    <a href="/excel">📊 Excel</a>

    <table border=1>
    <tr>
    <th>Barkod</th><th>İsim</th><th>Adet</th><th>Depo</th><th>İşlem</th>
    </tr>

    {% for u in urunler %}
    <tr>
    <td>{{u[1]}}</td>
    <td>{{u[2]}}</td>
    <td>{{u[9]}}</td>
    <td>{{u[10]}}</td>
    <td>
    <a href="/dus/{{u[1]}}">-1</a>
    <a href="/etiket/{{u[1]}}">Etiket</a>
    </td>
    </tr>
    {% endfor %}
    </table>
    """ , urunler=urunler)

# ---------------- STOK DÜŞ ----------------
@app.route("/dus/<kod>")
def dus(kod):
    with db() as con:
        con.execute("UPDATE urunler SET adet = adet - 1 WHERE barkod=?",(kod,))
        con.execute("INSERT INTO hareketler(barkod,islem,adet,tarih) VALUES(?,?,?,?)",
                    (kod,"ÇIKIŞ",1,str(datetime.datetime.now())))
    return redirect("/panel")

# ---------------- KAMERA ----------------
@app.route("/kamera")
def kamera():
    return """
    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <video id="v" width="300"></video>
    <script>
    let codeReader = new ZXing.BrowserBarcodeReader()
    codeReader.decodeFromVideoDevice(null, 'v', (result, err) => {
        if(result){
            window.location="/dus/"+result.text
        }
    })
    </script>
    """

# ---------------- ETİKET ----------------
@app.route("/etiket/<kod>")
def etiket(kod):
    return f"""
    <h2>{kod}</h2>
    <img src="/static/{kod}.png">
    <br><button onclick="window.print()">Yazdır</button>
    """

# ---------------- EXCEL ----------------
@app.route("/excel")
def excel():
    wb = Workbook()
    ws = wb.active
    ws.append(["Barkod","İsim","Adet","Depo"])

    data = db().execute("SELECT barkod,isim,adet,depo FROM urunler").fetchall()
    for d in data:
        ws.append(d)

    file = "rapor.xlsx"
    wb.save(file)
    return send_file(file, as_attachment=True)

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
