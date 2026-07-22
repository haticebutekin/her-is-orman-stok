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

# 🔥 GEÇİCİ SEPET
sepet = []

# 🔥 BARKOD
def barkod_uret():
    return str(random.randint(100000000000,999999999999))

# 🔥 FİŞ
def fis_yazdir():
    try:
        p = Usb(0x04b8, 0x0202)
        p.text("=== ORMAN KASA PRO ===\n")
        toplam = 0
        for u in sepet:
            p.text(f"{u['ad']} x{u['adet']} = {u['toplam']} TL\n")
            toplam += u["toplam"]
        p.text("----------------------\n")
        p.text(f"TOPLAM: {toplam} TL\n")
        p.cut()
    except:
        print("Yazıcı yok")

# 🔐 GİRİŞ
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["sifre"] == "1234":
            session["login"] = True
            return redirect("/pos")
    return '''
    <h2>🔐 ORMAN KASA GİRİŞ</h2>
    <form method="post">
    Şifre: <input type="password" name="sifre">
    <button>Giriş</button>
    </form>
    '''

# 🛒 KASA
@app.route("/pos", methods=["GET","POST"])
def pos():
    if "login" not in session:
        return redirect("/")

    global sepet

    if request.method == "POST":
        barkod = request.form["barkod"]
        adet = int(request.form["adet"])

        urun = c.execute("SELECT * FROM urun WHERE barkod=?", (barkod,)).fetchone()

        if urun:
            toplam = adet * urun[8]

            sepet.append({
                "ad": urun[2],
                "marka": urun[3],
                "ebat": urun[4],
                "yuzey": urun[5],
                "renk": urun[6],
                "adet": adet,
                "toplam": toplam
            })

    toplam_genel = sum([u["toplam"] for u in sepet])

    return render_template_string("""
<html>
<head>
<style>
body{background:#020617;color:white;font-family:Arial}
.grid{display:grid;grid-template-columns:2fr 1fr}
.box{background:#111827;padding:20px;border-radius:10px;margin:10px}
input,button,select{padding:12px;font-size:18px;margin:5px;width:90%}
.big{font-size:28px}
</style>
</head>

<body>

<h1>🌲 ORMAN KASA PRO</h1>

<div class="grid">

<div class="box">
<h2>Satış</h2>

<form method="post">
<input id="barkod" name="barkod" placeholder="Barkod">
<input name="adet" value="1">
<button>➕ Sepete Ekle</button>
</form>

<button onclick="kamera()">📷 Kamera</button>
<div id="kamera"></div>

<h2>Ürün Ekle</h2>
<form action="/ekle" method="post">
<input name="ad" placeholder="Ad">
<input name="marka" placeholder="Marka">
<input name="ebat" placeholder="Ebat">
<select name="yuzey">
<option>HG</option>
<option>MAT</option>
</select>
<input name="renk" placeholder="Renk">
<input name="adet" placeholder="Stok">
<input name="fiyat" placeholder="Fiyat">
<button>Kaydet</button>
</form>

</div>

<div class="box">
<h2>🧾 Fiş</h2>

{% for u in sepet %}
<div>
<b>{{u.ad}}</b><br>
{{u.marka}} | {{u.ebat}} | {{u.yuzey}} | {{u.renk}}<br>
{{u.adet}} x = {{u.toplam}} TL
<hr>
</div>
{% endfor %}

<h1 class="big">TOPLAM: {{toplam}} TL</h1>

<form action="/odeme">
<button class="big">💳 ÖDE</button>
</form>

</div>

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
""", sepet=sepet, toplam=toplam_genel)

# 💳 ÖDEME
@app.route("/odeme")
def odeme():
    global sepet
    fis_yazdir()
    sepet = []
    return redirect("/pos")

# ➕ EKLE
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

app.run(debug=True)
