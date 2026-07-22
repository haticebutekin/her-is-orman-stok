from flask import Flask, request, redirect
import sqlite3
import barcode
from barcode.writer import ImageWriter
import os

app = Flask(__name__)

# DATABASE
conn = sqlite3.connect("db.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS urun(
id INTEGER PRIMARY KEY AUTOINCREMENT,
barkod TEXT,
ad TEXT,
cins TEXT,
ebat TEXT,
sinif TEXT,
renk TEXT,
yuzey TEXT,
adet INTEGER,
fiyat REAL
)
""")
conn.commit()

sepet = []

# ✅ BARKOD FONKSİYONU (DIŞARIDA OLACAK!)
def barkod_resim_olustur(kod):
    if not os.path.exists("static/barcodes"):
        os.makedirs("static/barcodes")

    CODE128 = barcode.get_barcode_class('code128')
    barkod_obj = CODE128(kod, writer=ImageWriter())
    barkod_obj.save(f"static/barcodes/{kod}")

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form["k"]=="admin" and request.form["s"]=="1234":
            return redirect("/pos")

    return """
    <h2>🌲 ORMAN KASA PRO</h2>
    <form method="post">
    <input name="k" placeholder="Kullanıcı"><br>
    <input name="s" type="password" placeholder="Şifre"><br>
    <button>Giriş</button>
    </form>
    """

# POS
@app.route("/pos", methods=["GET","POST"])
def pos():
    global sepet

    if request.method=="POST":
        barkod = request.form["barkod"]

        # ✅ barkod resmi oluştur
        barkod_resim_olustur(barkod)

        urun = c.execute(
        "SELECT * FROM urun WHERE barkod=?",
        (barkod,)
        ).fetchone()

        if urun:
            sepet.append({
            "ad":urun[2],
            "cins":urun[3],
            "ebat":urun[4],
            "sinif":urun[5],
            "renk":urun[6],
            "yuzey":urun[7],
            "fiyat":urun[9]
            })

            c.execute(
            "UPDATE urun SET adet=adet-1 WHERE id=?",
            (urun[0],)
            )
            conn.commit()

    liste=""
    toplam=0

    for u in sepet:
        toplam+=u["fiyat"]

        liste+=f"""
        <div class='kart'>
        <h3>{u['ad']}</h3>
        {u['cins']} - {u['ebat']} mm - {u['sinif']}<br>
        {u['renk']} - {u['yuzey']}<br>
        {u['fiyat']} TL
        </div>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>

<script src="https://unpkg.com/html5-qrcode"></script>

<style>
body {{
background:#020617;
color:white;
font-family:Arial;
padding:20px;
}}

input,button {{
width:100%;
padding:15px;
margin:5px;
border-radius:10px;
border:0;
font-size:18px;
}}

button {{
background:#22c55e;
}}

.kart {{
background:#1e293b;
padding:15px;
margin:10px;
border-radius:10px;
}}
</style>

</head>

<body>

<h2>🌲 ORMAN KASA PRO</h2>

<form method="post">
<input id="barkod" name="barkod" placeholder="Barkod okut">
</form>

<button onclick="kameraAc()" type="button">
📷 KAMERA
</button>

<a href="/ekle">
<button type="button">➕ ÜRÜN EKLE</button>
</a>

<div id="kamera"></div>

{liste}

<h2>TOPLAM: {toplam} TL</h2>

<script>

function kameraAc(){{

let scanner = new Html5QrcodeScanner(
"kamera",
{{fps:10, qrbox:250}}
);

scanner.render(function(text){{

document.getElementById("barkod").value = text;

scanner.clear();

document.forms[0].submit();

}});

}}

</script>

</body>
</html>
"""

# ÜRÜN EKLE
@app.route("/ekle", methods=["GET","POST"])
def ekle():

    if request.method=="POST":

        barkod = request.form["b"]

        # ✅ burada da barkod oluştur
        barkod_resim_olustur(barkod)

        c.execute("""
        INSERT INTO urun
        (barkod,ad,cins,ebat,sinif,renk,yuzey,adet,fiyat)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,(
        barkod,
        request.form["a"],
        request.form["c"],
        request.form["e"],
        request.form["s"],
        request.form["r"],
        request.form["y"],
        request.form["adet"],
        request.form["f"]
        ))

        conn.commit()
        return redirect("/pos")

    return """
    <body style="background:#020617;color:white;font-family:Arial;padding:20px">

    <h2>ÜRÜN EKLE</h2>

    <form method="post">

    <input name="b" placeholder="Barkod"><br>
    <input name="a" placeholder="Ad"><br>
    <input name="c" placeholder="Cins"><br>
    <input name="e" placeholder="Ebat"><br>
    <input name="s" placeholder="Sınıf"><br>
    <input name="r" placeholder="Renk"><br>

    <select name="y">
    <option value="MAT">MAT</option>
    <option value="HG">HG</option>
    </select><br>

    <input name="adet" placeholder="Adet"><br>
    <input name="f" placeholder="Fiyat"><br>

    <button>KAYDET</button>

    </form>

    </body>
    """

# RUN
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
