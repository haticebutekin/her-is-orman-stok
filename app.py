from flask import Flask, request, redirect, render_template_string, session
import sqlite3
import random
from escpos.printer import Usb

app = Flask(__name__)
app.secret_key = "1234"

db = sqlite3.connect("db.db", check_same_thread=False)
c = db.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS urun(
id INTEGER PRIMARY KEY AUTOINCREMENT,
barkod TEXT,
ad TEXT,
marka TEXT,
ebat TEXT,
yuzey TEXT,
renk TEXT,
adet INTEGER,
fiyat REAL
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS satis(
id INTEGER PRIMARY KEY AUTOINCREMENT,
urun TEXT,
adet INTEGER,
toplam REAL
)
""")

# 🔥 OTOMATİK BARKOD
def barkod_uret():
    return str(random.randint(100000000000,999999999999))

# 🔥 FİŞ YAZDIR
def fis_yazdir(urun, adet, toplam):
    try:
        p = Usb(0x04b8, 0x0202)  # USB ID değişebilir
        p.text("ORMAN KASA PRO\n")
        p.text("------------------\n")
        p.text(f"{urun} x{adet}\n")
        p.text(f"TOPLAM: {toplam} TL\n")
        p.text("------------------\n")
        p.cut()
    except:
        print("Yazıcı bağlı değil")

# 🔐 GİRİŞ
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["sifre"] == "1234":
            session["login"] = True
            return redirect("/pos")
    return '''
    <h2>Giriş</h2>
    <form method="post">
    Şifre: <input type="password" name="sifre">
    <button>Giriş</button>
    </form>
    '''

# 🧠 ADMIN PANEL
@app.route("/admin")
def admin():
    if "login" not in session:
        return redirect("/")
    urunler = c.execute("SELECT * FROM urun").fetchall()
    return render_template_string("""
    <h2>Admin Panel</h2>
    <a href="/pos">Kasaya dön</a>
    <table border=1>
    <tr><th>Ad</th><th>Marka</th><th>Barkod</th><th>Stok</th></tr>
    {% for u in urunler %}
    <tr><td>{{u[2]}}</td><td>{{u[3]}}</td><td>{{u[1]}}</td><td>{{u[7]}}</td></tr>
    {% endfor %}
    </table>
    """, urunler=urunler)

# 🛒 KASA
@app.route("/pos", methods=["GET","POST"])
def pos():
    if "login" not in session:
        return redirect("/")

    sonuc = ""

    if request.method == "POST":
        barkod = request.form["barkod"]
        adet = int(request.form["adet"])

        urun = c.execute("SELECT * FROM urun WHERE barkod=?", (barkod,)).fetchone()

        if urun:
            toplam = adet * urun[8]
            sonuc = f"{urun[2]} - {toplam} TL"

            c.execute("INSERT INTO satis (urun,adet,toplam) VALUES (?,?,?)",
                      (urun[2], adet, toplam))
            db.commit()

            fis_yazdir(urun[2], adet, toplam)

    return render_template_string("""
    <html>
    <head>
    <style>
    body{background:#020617;color:white;font-family:Arial}
    input,select,button{padding:10px;margin:5px;font-size:18px}
    .box{background:#111827;padding:20px;border-radius:10px}
    </style>
    </head>

    <body>

    <h1>🔥 ORMAN KASA PRO</h1>

    <a href="/admin">Admin</a>

    <div class="box">
    <h2>Satış</h2>
    <form method="post">
    Barkod: <input id="barkod" name="barkod">
    Adet: <input name="adet" value="1">
    <button>Sat</button>
    </form>

    <button onclick="kamera()">📷 Kamera</button>
    <div id="kamera"></div>

    <h3>{{sonuc}}</h3>
    </div>

    <div class="box">
    <h2>Ürün Ekle</h2>
    <form action="/ekle" method="post">
    Ad: <input name="ad">
    Marka: <input name="marka">
    Ebat: <input name="ebat">
    Yüzey:
    <select name="yuzey">
    <option>HG</option>
    <option>MAT</option>
    </select>
    Renk: <input name="renk">
    Stok: <input name="adet">
    Fiyat: <input name="fiyat">
    <button>Ekle</button>
    </form>
    </div>

<script src="https://unpkg.com/html5-qrcode"></script>
<script>
function kamera(){
    const scanner = new Html5Qrcode("kamera");
    scanner.start({ facingMode: "environment" }, {}, (text)=>{
        document.getElementById("barkod").value = text;
        scanner.stop();
    });
}
</script>

    </body>
    </html>
    """, sonuc=sonuc)

# ➕ ÜRÜN EKLE
@app.route("/ekle", methods=["POST"])
def ekle():
    barkod = barkod_uret()

    c.execute("""INSERT INTO urun
    (barkod,ad,marka,ebat,yuzey,renk,adet,fiyat)
    VALUES (?,?,?,?,?,?,?,?)""",
    (
        barkod,
        request.form["ad"],
        request.form["marka"],
        request.form["ebat"],
        request.form["yuzey"],
        request.form["renk"],
        request.form["adet"],
        request.form["fiyat"]
    ))

    db.commit()
    return redirect("/pos")

# 📊 RAPOR
@app.route("/rapor")
def rapor():
    data = c.execute("SELECT urun, SUM(toplam) FROM satis GROUP BY urun").fetchall()
    return str(data)

app.run(debug=True)
