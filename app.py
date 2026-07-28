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

    CREATE TABLE log (
id INTEGER PRIMARY KEY,
kullanici TEXT,
barkod TEXT,
islem TEXT,
tarih TEXT
);

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

    cur.execute("""
INSERT INTO log (kullanici,barkod,islem,tarih)
VALUES (?,?,?,datetime('now'))
""", (session["user"], barkod, tip))

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
    users = {
        "admin": {"pass":"1234","role":"admin"},
        "depo": {"pass":"1234","role":"depo"}
}
    
    return """
    <h2>STOK SİSTEMİ</h2>
    <form method=post>
    <input name=u placeholder=Kullanıcı>
    <input name=p type=password placeholder=Şifre>
    <button>Giriş</button>
    </form>
    """
@app.route("/log")
def log():
    cur.execute("SELECT * FROM log ORDER BY id DESC")
    data = cur.fetchall()

    return render_template_string("""
    <h2>İşlem Geçmişi</h2>
    {% for l in data %}
    <p>{{l[1]}} → {{l[3]}} → {{l[2]}} ({{l[4]}})</p>
    {% endfor %}
    """, data=data)

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

        yuzey = request.form["yuzey"]

        cur.execute("""
                     INSERT INTO urun 
                     (barkod,isim,cins,ebat,kalinlik,sinif,renk,yuzey,adet,kritik)
                     VALUES (?,?,?,?,?,?,?,?,?,?)
                    """, (barkod,isim,cins,ebat,kalinlik,sinif,renk,yuzey,adet,kritik))

        con.commit()
        con.close()

    con = db()
    cur = con.cursor()
    urunler = cur.execute("SELECT * FROM urun").fetchall()
    con.close()

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body {
    font-family: Arial;
    margin:0;
    background:#f5f6fa;
}

.topbar {
    background:#2f3640;
    color:white;
    padding:15px;
    position:sticky;
    top:0;
}

.container {
    padding:10px;
}

.card {
    background:white;
    padding:15px;
    margin-bottom:10px;
    border-radius:10px;
    box-shadow:0 2px 6px rgba(0,0,0,0.1);
}

.kritik {
    border-left:6px solid red;
    background:#ffe6e6;
}

.ok {
    border-left:6px solid green;
}

.btn {
    padding:8px 12px;
    text-decoration:none;
    border-radius:6px;
    color:white;
    font-size:14px;
}

.giris { background:green; }
.cikis { background:red; }

input, select {
    width:100%;
    padding:8px;
    margin:5px 0;
}

button {
    width:100%;
    padding:10px;
    background:#273c75;
    color:white;
    border:none;
    border-radius:6px;
}

.search {
    padding:10px;
    margin-bottom:10px;
}
</style>
</head>

<body>

<div class="topbar">
    📦 STOK PRO
</div>

<div class="container">

<input class="search" id="search" placeholder="🔍 Ürün ara..." onkeyup="ara()">

<form method=post>
<b>Yeni Ürün</b>
<input name=isim placeholder="İsim" required>
<input name=cins placeholder="Cins">
<input name=ebat placeholder="Ebat">
<input name=kalinlik placeholder="Kalınlık">
<input name=sinif placeholder="Sınıf">
<input name=renk placeholder="Renk">
<input name=adet type=number placeholder="Adet" required>
<input name=kritik type=number value=5 placeholder="Kritik">
<button>➕ EKLE</button>
</form>

<select name="yuzey">
  <option value="HG">HG</option>
  <option value="MAT">MAT</option>
</select>

<hr>

<div id="urunler">

{% for u in urunler %}
<div class="card {% if u[8] <= u[9] %}kritik{% else %}ok{% endif %}">

<b class="isim">{{u[2]}}</b><br>

<small>
Cins: {{u[3]}} |
Ebat: {{u[4]}} |
Kalınlık: {{u[5]}}<br>
Sınıf: {{u[6]}} |
Renk: {{u[7]}}
</small>

<br><br>

<b>Adet: {{u[8]}}</b><br>

<img src="/static/{{u[1]}}.png" width=120><br><br>

<a class="btn giris" href="/islem/{{u[1]}}/giris">➕ Giriş</a>
<a class="btn cikis" href="/islem/{{u[1]}}/cikis">➖ Çıkış</a>

</div>
{% endfor %}

</div>

</div>

<script>
function ara(){
    let input = document.getElementById("search").value.toLowerCase();
    let cards = document.getElementsByClassName("card");

    for (let i = 0; i < cards.length; i++) {
        let name = cards[i].innerText.toLowerCase();
        cards[i].style.display = name.includes(input) ? "" : "none";
    }
}
</script>

</body>
</html>
""", urunler=urunler)

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["u"]
        p = request.form["p"]

        if u in users and users[u]["pass"] == p:
            session["user"] = u
            session["role"] = users[u]["role"]
            return redirect("/panel")

    return '''
    <form method=post>
    Kullanıcı: <input name=u><br>
    Şifre: <input name=p type=password><br>
    <button>Giriş</button>
    </form>
    '''

@app.route("/islem/<barkod>/<tip>")
def islem(barkod, tip):

    if session.get("role") == "depo" and tip != "cikis":
        return "❌ Yetkin yok!"

@app.route("/etiket/<barkod>")
def etiket(barkod):
    return render_template_string("""
    <h3>{{barkod}}</h3>
    <img src="/static/{{barkod}}.png" width=200>
    <script>
        window.print()
    </script>
    """, barkod=barkod)
    @app.route("/scan/<islem>", methods=["POST"])
def scan(islem):
    barkod = request.form["barkod"]

    cur.execute("SELECT * FROM urun WHERE barkod=?", (barkod,))
    urun = cur.fetchone()

    if not urun:
        return "❌ Bu ürün sistemde yok!"

    if islem == "cikis" and urun[9] <= 0:
        return "❌ Stok yok!"

    if islem == "giris":
        cur.execute("UPDATE urun SET adet = adet + 1 WHERE barkod=?", (barkod,))
    else:
        cur.execute("UPDATE urun SET adet = adet - 1 WHERE barkod=?", (barkod,))

    db.commit()

    return redirect("/panel")

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
