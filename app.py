from flask import Flask, request, redirect, render_template_string, session
import sqlite3, random

app = Flask(__name__)
app.secret_key = "123"

def db():
    return sqlite3.connect("db.db")

# TABLO
with db() as conn:
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS urun(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barkod TEXT,
        ad TEXT,
        cins TEXT,
        ebat TEXT,
        renk TEXT,
        yuzey TEXT,
        sinif TEXT,
        adet INTEGER,
        fiyat REAL
    )
    """)

# 🧾 PRO KASA
@app.route("/", methods=["GET","POST"])
def pos():
    if "sepet" not in session:
        session["sepet"] = []

    if request.method == "POST":
        barkod = request.form["barkod"]

        with db() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM urun WHERE barkod=?", (barkod,))
            urun = c.fetchone()

            if urun:
                sepet = session["sepet"]
                sepet.append({
                    "ad": urun[2],
                    "fiyat": urun[9],
                    "marka": urun[7],
                    "yuzey": urun[6]
                })
                session["sepet"] = sepet

    toplam = sum(i["fiyat"] for i in session["sepet"])

    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{
    background:#020617;
    color:white;
    font-family:Arial;
    margin:0;
}

.header{
    background:#0f172a;
    padding:20px;
    font-size:28px;
    text-align:center;
    font-weight:bold;
}

.container{
    display:flex;
}

.left{
    width:60%;
    padding:20px;
}

.right{
    width:40%;
    background:#020617;
    border-left:2px solid #1e293b;
    padding:20px;
}

input{
    width:70%;
    padding:15px;
    font-size:20px;
    border-radius:10px;
    border:none;
}

button{
    padding:15px;
    font-size:18px;
    border:none;
    border-radius:10px;
    background:#22c55e;
    color:white;
    cursor:pointer;
}

.card{
    background:#0f172a;
    padding:15px;
    margin:10px 0;
    border-radius:10px;
    font-size:18px;
}

.total{
    font-size:28px;
    color:#22c55e;
    margin-top:20px;
}

.menu a{
    display:block;
    background:#1e293b;
    padding:15px;
    margin-top:10px;
    border-radius:10px;
    text-decoration:none;
    color:white;
    text-align:center;
}
</style>
</head>

<body>

<div class="header">🌲 ORMAN KASA PRO</div>

<div class="container">

<div class="left">

<form method="post">
<input name="barkod" id="barkod" placeholder="Barkod okut / yaz">
<button>Ekle</button>
</form>

<br>
<button onclick="kamera()">📷 Kamera</button>
<div id="reader"></div>

</div>

<div class="right">

<h2>Sepet</h2>

{% for i in sepet %}
<div class="card">
<b>{{i.ad}}</b><br>
{{i.marka}} | {{i.yuzey}}<br>
{{i.fiyat}} ₺
</div>
{% endfor %}

<div class="total">
TOPLAM: {{toplam}} ₺
</div>

<div class="menu">
<a href="/fis">🧾 Fiş Yazdır</a>
<a href="/temizle">🧹 Temizle</a>
<a href="/liste">📦 Ürünler</a>
<a href="/ekle">➕ Ürün Ekle</a>
</div>

</div>

</div>

<script src="https://unpkg.com/html5-qrcode"></script>
<script>
function kamera(){
    let q = new Html5Qrcode("reader");
    q.start({ facingMode: "environment" }, { fps: 10 }, (text)=>{
        document.getElementById("barkod").value = text;
        q.stop();
    });
}
</script>

</body>
</html>
""", sepet=session["sepet"], toplam=toplam)

# 🧾 FİŞ
@app.route("/fis")
def fis():
    sepet = session.get("sepet", [])
    toplam = sum(i["fiyat"] for i in sepet)

    text = "ORMAN KASA PRO\n\n"
    for i in sepet:
        text += f"{i['ad']} - {i['fiyat']} TL\n"
    text += f"\nTOPLAM: {toplam} TL"

    return f"<pre>{text}</pre><script>window.print()</script>"

# 🧹 TEMİZLE
@app.route("/temizle")
def temizle():
    session["sepet"] = []
    return redirect("/")

# 📦 ÜRÜNLER
@app.route("/liste")
def liste():
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM urun")
        data = c.fetchall()

    html = "<h1 style='color:white;background:#020617'>ÜRÜNLER</h1>"

    for i in data:
        html += f"""
        <div style='background:#0f172a;color:white;padding:15px;margin:10px;border-radius:10px'>
        <b>{i[2]}</b><br>
        Barkod: {i[1]}<br>
        <img src='https://barcode.tec-it.com/barcode.ashx?data={i[1]}&code=EAN13'><br>
        Marka: {i[7]}<br>
        Yüzey: {i[6]}<br>
        Fiyat: {i[9]} ₺
        </div>
        """

    html += "<a href='/'>Kasa</a>"
    return html

# ➕ ÜRÜN EKLE
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method == "POST":
        barkod = "20" + str(random.randint(100000000,999999999))

        data = (
            barkod,
            request.form["ad"],
            request.form["cins"],
            request.form["ebat"],
            request.form["renk"],
            request.form["yuzey"],
            request.form["sinif"],
            request.form["adet"],
            request.form["fiyat"]
        )

        with db() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO urun VALUES (NULL,?,?,?,?,?,?,?,?,?)", data)

        return f"<h2 style='color:white'>KAYDEDİLDİ</h2><h1 style='color:white'>{barkod}</h1><a href='/'>Kasa</a>"

    return """
    <h1>Ürün Ekle</h1>
    <form method="post">
    Ad: <input name="ad"><br>
    Cins: <input name="cins"><br>
    Ebat: <input name="ebat"><br>
    Renk: <input name="renk"><br>

    Yüzey:
    <select name="yuzey">
    <option>HG</option>
    <option>MAT</option>
    </select><br>

    Marka:
    <input name="sinif"><br>

    Adet: <input name="adet"><br>
    Fiyat: <input name="fiyat"><br>

    <button>Kaydet</button>
    </form>
    """

if __name__ == "__main__":
    app.run()
