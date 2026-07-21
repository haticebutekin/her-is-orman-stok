from flask import Flask, request, redirect
import sqlite3

app = Flask(__name__)
print("YENI KOD CALISIYOR")

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


    toplam=0
    liste=""


    for u in sepet:

        toplam += u["fiyat"]

        liste += f"""
        <tr>
        <td>

        <b>{u['ad']}</b><br>
        Cins: {u['cins']}<br>
        Ebat: {u['ebat']} mm<br>
        Sınıf: {u['sinif']}<br>
        Renk: {u['renk']}<br>
        Yüzey: {u['yuzey']}<br>
        Stok: {u['adet']}

        </td>

        <td>
        {u['fiyat']} TL
        </td>

        </tr>
        """


    return f"""

<html>

<head>

<script src="https://unpkg.com/html5-qrcode"></script>

<style>

body{{
background:#0f172a;
color:white;
font-family:Arial;
padding:20px;
}}

input,button{{
width:100%;
padding:18px;
font-size:20px;
margin:5px;
}}

button{{
background:#22c55e;
border:0;
border-radius:10px;
}}

</style>

</head>


<body>


<h2>🌲 ORMAN KASA PRO</h2>


<form method="post">

<input id="barkod"
name="barkod"
placeholder="Barkod okut">

</form>


<button type="button" onclick="kameraAc()">
📷 KAMERA İLE BARKOD OKU
</button>


<div id="kamera"></div>


<table border="1" width="100%">

{liste}

</table>


<h1>
TOPLAM: {toplam} TL
</h1>



<script>

function kameraAc(){{

let scanner = new Html5QrcodeScanner(
"kamera",
{{fps:10,qrbox:250}}
);


scanner.render(

function(text){{

document.getElementById("barkod").value=text;

scanner.clear();

document.forms[0].submit();

}}

);

}}

</script>


</body>

</html>

"""


@app.route("/ekle", methods=["GET","POST"])
def ekle():

    if request.method=="POST":

        c.execute("""
        INSERT INTO urun
        (barkod,ad,cins,ebat,sinif,renk,yuzey,adet,fiyat)
        VALUES (?,?,?,?,?,?,?,?,?)
        """,
        (
        request.form["b"],
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

<h2>Ürün Ekle</h2>

<form method="post">

<input name="b" placeholder="Barkod">

<input name="a" placeholder="Ürün Adı">

<input name="c" placeholder="Cins">

<input name="e" placeholder="Ebat mm">

<input name="s" placeholder="Sınıf">

<input name="r" placeholder="Renk">

<input name="y" placeholder="MAT / HG">

<input name="adet" placeholder="Adet">

<input name="f" placeholder="Fiyat">

<button>Kaydet</button>

</form>

"""


@app.route("/rapor")
def rapor():

    data=c.execute("SELECT * FROM urun").fetchall()

    html=""

    for u in data:

        html+=f"""
        <tr>
        <td>{u[2]}</td>
        <td>{u[7]}</td>
        <td>{u[8]}</td>
        <td>{u[9]}</td>
        </tr>
        """


    return f"""
    <h2>STOK</h2>

    <table border="1">
    {html}
    </table>

    <a href="/pos">Geri</a>
    """


@app.route("/odeme")
def odeme():

    global sepet

    sepet.clear()

    return """
    <h2>Satış tamamlandı</h2>
    <a href="/pos">Geri</a>
    """


if __name__=="__main__":
    app.run(host="0.0.0.0",port=5000)
