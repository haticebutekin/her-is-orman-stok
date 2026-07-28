from flask import Flask, request, redirect, session, render_template_string, send_file
import sqlite3, os, datetime, shutil
from barcode import Code128
from barcode.writer import ImageWriter
from openpyxl import Workbook

app = Flask(__name__)
app.secret_key = "pro123"

DB = "stok.db"
STATIC = "static"

if not os.path.exists(STATIC):
    os.makedirs(STATIC)

DEPOLAR = ["MDF","LAMİNANT","KAPI","HGLOSS","SÜTÇÜ","HELVACI","KESİM"]

# DB
def db():
    return sqlite3.connect(DB)

def init():
    con = db()
    cur = con.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS urun(
    id INTEGER PRIMARY KEY,
    barkod TEXT,
    isim TEXT,
    adet INTEGER,
    depo TEXT,
    kritik INTEGER
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS hareket(
    id INTEGER PRIMARY KEY,
    barkod TEXT,
    tip TEXT,
    adet INTEGER,
    tarih TEXT
    )""")

    con.commit()
    con.close()

init()

# BARKOD
def barkod():
    con = db()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM urun")
    n = cur.fetchone()[0] + 1
    kod = f"HER-{str(n).zfill(6)}"
    path = f"{STATIC}/{kod}.png"
    Code128(kod, writer=ImageWriter()).write(open(path, "wb"))
    return kod

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["u"]=="admin" and request.form["p"]=="123":
            session["ok"]=1
            return redirect("/panel")

    return """
    <h2>STOK PRO</h2>
    <form method=post>
    <input name=u placeholder=Kullanıcı>
    <input name=p type=password placeholder=Şifre>
    <button>Giriş</button>
    </form>
    """

# PANEL
@app.route("/panel", methods=["GET","POST"])
def panel():
    if not session.get("ok"):
        return redirect("/")

    if request.method == "POST":
        kod = barkod()
        data = (
            kod,
            request.form["isim"],
            int(request.form["adet"]),
            request.form["depo"],
            int(request.form["kritik"])
        )

        con = db()
        cur = con.cursor()
        cur.execute("INSERT INTO urun VALUES(NULL,?,?,?,?,?)", data)
        cur.execute("INSERT INTO hareket VALUES(NULL,?,?,?,?)",
                    (kod,"GİRİŞ",data[2],str(datetime.datetime.now())))
        con.commit()
        con.close()

    con = db()
    cur = con.cursor()
    urunler = cur.execute("SELECT * FROM urun").fetchall()
    con.close()

    return render_template_string("""
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <h2>📦 STOK PRO LEVEL 3</h2>

    <form method=post>
    <input name=isim placeholder="Ürün">
    <input name=adet type=number placeholder="Adet">
    <input name=kritik type=number value=5>
    <select name=depo>
    {% for d in depolar %}
    <option>{{d}}</option>
    {% endfor %}
    </select>
    <button>EKLE</button>
    </form>

    <hr>

    <a href="/kamera">📷 Kamera</a>
    <a href="/rapor">📊 Rapor</a>
    <a href="/yedek">💾 Yedek</a>
    <a href="/etiket">🏷 Etiket</a>

    <hr>

    {% for u in urunler %}
    <div style="border:1px solid #ccc;padding:10px;margin:5px;
    background:{% if u[3]<=u[5] %}#ffdddd{% else %}#ddffdd{% endif %}">
    
    <b>{{u[2]}}</b><br>
    Barkod: {{u[1]}}<br>
    Adet: {{u[3]}}<br>
    Depo: {{u[4]}}<br>

    <img src="/static/{{u[1]}}.png" width=150><br>

    <a href="/islem/{{u[1]}}/giris">➕</a>
    <a href="/islem/{{u[1]}}/cikis">➖</a>
    <a href="/fis/{{u[1]}}">🖨 Fiş</a>

    </div>
    {% endfor %}
    """, urunler=urunler, depolar=DEPOLAR)

# İŞLEM
@app.route("/islem/<kod>/<tip>")
def islem(kod, tip):
    con = db()
    cur = con.cursor()

    cur.execute("SELECT adet FROM urun WHERE barkod=?", (kod,))
    a = cur.fetchone()[0]

    yeni = a+1 if tip=="giris" else max(a-1,0)

    cur.execute("UPDATE urun SET adet=? WHERE barkod=?", (yeni,kod))
    cur.execute("INSERT INTO hareket VALUES(NULL,?,?,?,?)",
                (kod,tip.upper(),1,str(datetime.datetime.now())))
    con.commit()
    con.close()

    return redirect("/panel")

# KAMERA
@app.route("/kamera")
def kamera():
    return """
    <button onclick="tip='giris'">GİRİŞ</button>
    <button onclick="tip='cikis'">ÇIKIŞ</button>
    <video id="v" width=300></video>

    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <script>
    let tip="cikis"
    const r = new ZXing.BrowserBarcodeReader()
    r.decodeFromVideoDevice(null,'v',(res,err)=>{
        if(res){
            window.location="/islem/"+res.text+"/"+tip
        }
    })
    </script>
    """

# FİŞ
@app.route("/fis/<kod>")
def fis(kod):
    return f"""
    <h3>FİŞ</h3>
    {kod}<br>
    <script>window.print()</script>
    """

# RAPOR
@app.route("/rapor")
def rapor():
    con = db()
    cur = con.cursor()
    toplam = cur.execute("SELECT SUM(adet) FROM urun").fetchone()[0]
    con.close()

    return f"<h2>Toplam Stok: {toplam}</h2>"

# YEDEK
@app.route("/yedek")
def yedek():
    shutil.copy(DB, "yedek.db")
    return send_file("yedek.db", as_attachment=True)

# ETİKET
@app.route("/etiket")
def etiket():
    con = db()
    cur = con.cursor()
    data = cur.execute("SELECT barkod FROM urun").fetchall()
    con.close()

    html = "<h3>Etiketler</h3>"

    for d in data:
        html += f"<img src='/static/{d[0]}.png' width=200>"

    return html

# RUN
if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
