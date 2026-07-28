from flask import Flask, render_template_string, request, redirect, session
import sqlite3, os, uuid
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = "secret123"

STATIC = "static"
if not os.path.exists(STATIC):
    os.makedirs(STATIC)

# DB
db = sqlite3.connect("stok.db", check_same_thread=False)
cur = db.cursor()

# TABLOLAR
cur.execute("""
CREATE TABLE IF NOT EXISTS urun (
id INTEGER PRIMARY KEY,
barkod TEXT,
isim TEXT,
cins TEXT,
ebat TEXT,
kalinlik TEXT,
sinif TEXT,
renk TEXT,
yuzey TEXT,
adet INTEGER,
kritik INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS log (
id INTEGER PRIMARY KEY,
kullanici TEXT,
barkod TEXT,
islem TEXT,
tarih TEXT
)
""")

db.commit()

# KULLANICILAR
users = {
    "admin": {"pass":"1234","role":"admin"},
    "depo": {"pass":"1234","role":"depo"}
}

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["u"]
        p = request.form["p"]

        if u in users and users[u]["pass"] == p:
            session["user"] = u
            session["role"] = users[u]["role"]
            return redirect("/panel")

    return """
    <h2>Giriş</h2>
    <form method=post>
    Kullanıcı: <input name=u><br>
    Şifre: <input name=p type=password><br>
    <button>Giriş</button>
    </form>
    """

@app.route("/kamera/<tip>")
def kamera(tip):
    return render_template_string("""
    <h2>Kamera ile Barkod Oku</h2>

    <video id="video" width="300" height="200" autoplay></video>
    <canvas id="canvas" hidden></canvas>

    <script src="https://unpkg.com/@zxing/library@latest"></script>

    <script>
    const codeReader = new ZXing.BrowserBarcodeReader()

    codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {
        if (result) {
            let barkod = result.text
            window.location.href = "/islem/" + barkod + "/{{tip}}"
        }
    })
    </script>
    """, tip=tip)

@app.route("/kontrol/<barkod>")
def kontrol(barkod):
    cur.execute("SELECT barkod FROM urun WHERE barkod=?", (barkod,))
    urun = cur.fetchone()

    if urun:
        return {"ok": True}
    else:
        return {"ok": False}
        
# PANEL
@app.route("/panel", methods=["GET","POST"])
def panel():

    if "user" not in session:
        return redirect("/")

    if request.method == "POST":

        barkod = str(uuid.uuid4())[:12]
        isim = request.form["isim"]
        cins = request.form["cins"]
        ebat = request.form["ebat"]
        kalinlik = request.form["kalinlik"]
        sinif = request.form["sinif"]
        renk = request.form["renk"]
        yuzey = request.form["yuzey"]
        adet = int(request.form["adet"])
        kritik = int(request.form["kritik"])

        # barkod oluştur
        code = barcode.get("code128", barkod, writer=ImageWriter())
        code.save(f"{STATIC}/{barkod}")

        cur.execute("""
        INSERT INTO urun
        (barkod,isim,cins,ebat,kalinlik,sinif,renk,yuzey,adet,kritik)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (barkod,isim,cins,ebat,kalinlik,sinif,renk,yuzey,adet,kritik))

        db.commit()

    cur.execute("SELECT * FROM urun")
    urunler = cur.fetchall()

    return render_template_string("""
    <h2>📦 Stok</h2>

    <form method=post>
    <input name=isim placeholder="İsim" required>
    <input name=cins placeholder="Cins">
    <input name=ebat placeholder="Ebat">
    <input name=kalinlik placeholder="Kalınlık">
    <input name=sinif placeholder="Sınıf">
    <input name=renk placeholder="Renk">

    <a href="/kamera/cikis">📷 Kamera ile Çıkış</a>
    <a href="/kamera/giris">📷 Kamera ile Giriş</a>

    <select name=yuzey>
        <option value="HG">HG</option>
        <option value="MAT">MAT</option>
    </select>

    <input name=adet type=number placeholder="Adet" required>
    <input name=kritik type=number value=5 placeholder="Kritik">

    <button>EKLE</button>
    </form>

    <hr>

    {% for u in urunler %}
    <div style="border:1px solid #ccc; margin:10px; padding:10px;
    {% if u[9] <= u[10] %}background:#ffe6e6{% endif %}">

    <b>{{u[2]}}</b><br>
    Cins: {{u[3]}} | Ebat: {{u[4]}}<br>
    Kalınlık: {{u[5]}} | Sınıf: {{u[6]}}<br>
    Renk: {{u[7]}} | Yüzey: {{u[8]}}<br><br>

    <b>Adet: {{u[9]}}</b><br>

    <img src="/static/{{u[1]}}.png" width=120><br><br>

    <a href="/islem/{{u[1]}}/giris">➕ Giriş</a>
    <a href="/islem/{{u[1]}}/cikis">➖ Çıkış</a>
    <a href="/etiket/{{u[1]}}">🖨 Etiket</a>

    </div>
    {% endfor %}

    <a href="/log">📜 Log</a>
    """, urunler=urunler)

# İŞLEM
@app.route("/islem/<barkod>/<tip>")
def islem(barkod, tip):

    if session.get("role") == "depo" and tip != "cikis":
        return "❌ Yetkin yok"

    cur.execute("SELECT adet FROM urun WHERE barkod=?", (barkod,))
    veri = cur.fetchone()

    if not veri:
        return "Ürün yok"

    adet = veri[0]

    if tip == "cikis":
        if adet <= 0:
            return "❌ Stok yok"
        cur.execute("UPDATE urun SET adet = adet - 1 WHERE barkod=?", (barkod,))
    else:
        cur.execute("UPDATE urun SET adet = adet + 1 WHERE barkod=?", (barkod,))

    navigator.vibrate(200);
    new Audio("https://actions.google.com/sounds/v1/cartoon/wood_plank_flicks.ogg").play();

    cur.execute("""
    INSERT INTO log (kullanici,barkod,islem,tarih)
    VALUES (?,?,?,datetime('now'))
    """, (session["user"], barkod, tip))

    db.commit()

    return redirect("/panel")

# ETİKET
@app.route("/etiket/<barkod>")
def etiket(barkod):
    return f"""
    <h3>{barkod}</h3>
    <img src="/static/{barkod}.png" width=200>
    <script>window.print()</script>
    """

# LOG
@app.route("/log")
def log():
    cur.execute("SELECT * FROM log ORDER BY id DESC")
    data = cur.fetchall()

    return render_template_string("""
    <h2>Log</h2>
    {% for l in data %}
    <p>{{l[1]}} → {{l[3]}} → {{l[2]}} ({{l[4]}})</p>
    {% endfor %}
    """, data=data)

# RUN
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
