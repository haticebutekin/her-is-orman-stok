from flask import Flask, request, redirect, session, render_template_string
import sqlite3, os, datetime
from barcode import Code128
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = "fix123"

DB = "stok.db"
STATIC = "static"

if not os.path.exists(STATIC):
    os.makedirs(STATIC)

def db():
    return sqlite3.connect(DB)

def init():
    con = db()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS urun(
        id INTEGER PRIMARY KEY,
        barkod TEXT,
        isim TEXT,
        cins TEXT,
        ebat TEXT,
        kalinlik TEXT,
        sinif TEXT,
        renk TEXT,
        adet INTEGER,
        kritik INTEGER
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
        if request.form["u"] == "admin" and request.form["p"] == "123":
            session["ok"] = True
            return redirect("/panel")

    return """
    <h2>STOK SİSTEMİ</h2>
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
            request.form["cins"],
            request.form["ebat"],
            request.form["kalinlik"],
            request.form["sinif"],
            request.form["renk"],
            int(request.form["adet"]),
            int(request.form["kritik"])
        )

        con = db()
        cur = con.cursor()
        cur.execute("INSERT INTO urun VALUES(NULL,?,?,?,?,?,?,?,?,?)", data)
        cur.execute("INSERT INTO hareket VALUES(NULL,?,?,?,?)",
                    (kod,"GİRİŞ",data[7],str(datetime.datetime.now())))
        con.commit()
        con.close()

    con = db()
    cur = con.cursor()
    urunler = cur.execute("SELECT * FROM urun").fetchall()
    con.close()

    return render_template_string("""
    <h2>📦 STOK PANEL</h2>

    <form method=post>
    İsim <input name=isim required><br>
    Cins <input name=cins><br>
    Ebat <input name=ebat><br>
    Kalınlık <input name=kalinlik><br>
    Sınıf <input name=sinif><br>
    Renk <input name=renk><br>
    Adet <input name=adet type=number required><br>
    Kritik <input name=kritik type=number value=5><br>
    <button>EKLE</button>
    </form>

    <hr>

    <a href="/kamera">📷 Kamera</a>

    <hr>

    {% for u in urunler %}
    <div style="border:1px solid #ccc;padding:10px;margin:5px;
    background:{% if u[9]<=u[10] %}#ffdddd{% else %}#ddffdd{% endif %}">

    <b>{{u[2]}}</b><br>
    Barkod: {{u[1]}}<br>

    Cins: {{u[3]}}<br>
    Ebat: {{u[4]}}<br>
    Kalınlık: {{u[5]}}<br>
    Sınıf: {{u[6]}}<br>
    Renk: {{u[7]}}<br>

    Adet: {{u[8]}}<br>

    <img src="/static/{{u[1]}}.png" width=150><br>

    <a href="/islem/{{u[1]}}/giris">➕ Giriş</a>
    <a href="/islem/{{u[1]}}/cikis">➖ Çıkış</a>

    </div>
    {% endfor %}
    """, urunler=urunler)

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

# RUN
if __name__ == "__main__":
    port = int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0", port=port)
