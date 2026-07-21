from flask import Flask, request, redirect
import sqlite3

app = Flask(__name__)

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

sepet=[]


@app.route("/", methods=["GET","POST"])
def login():

    if request.method=="POST":
        if request.form["k"]=="admin" and request.form["s"]=="1234":
            return redirect("/pos")

    return """
    <h2>🌲 ORMAN KASA PRO</h2>

    <form method="post">
    <input name="k" placeholder="Kullanıcı">
    <input name="s" type="password" placeholder="Şifre">
    <button>Giriş</button>
    </form>
    """


@app.route("/pos", methods=["GET","POST"])
def pos():

    global sepet

    if request.method=="POST":

        barkod=request.form["barkod"]

        urun=c.execute(
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
            "adet":urun[8],
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
        <div class="kart">
        <h3>{u['ad']}</h3>
        Cins: {u['cins']}<br>
        Ebat: {u['ebat']} mm<br>
        Sınıf: {u['sinif']}<br>
        Renk: {u['renk']}<br>
        Yüzey: {u['yuzey']}<br>
        Fiyat: {u['fiyat']} TL
        </div>
        """


    return f"""
<!DOCTYPE html>
<html>

<head>

<script src="https://unpkg.com/html5-qrcode"></script>

<style>

body{{
background:#020617;
color:white;
font-family:Arial;
padding:20px;
}}

input,button{{
width:100%;
padding:18px;
margin:5px;
font-size:18px;
border-radius:10px;
border:0;
}}

button{{
background:#22c55e;
}}

.kart{{
background:#1e293b;
padding:15px;
margin:10px;
border-radius:15px;
}}

</style>

</head>

<body>

<h2>🌲 ORMAN KASA PRO</h2>

<form method="post">

<input id="barkod" name="barkod" placeholder="Barkod okut">

</form>

<button onclick="kameraAc()" type="button">
📷 KAMERA İLE BARKOD OKU
</button>

<a href="/ekle">
<button type="button">
➕ ÜRÜN EKLE
</button>
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

document.getElementById("barkod").value=text;

scanner.clear();

document.forms[0].submit();

}});

}}

</script>


</body>
</html>
"""
