import sqlite3
import random
from flask import Flask, request, session, redirect

app = Flask(__name__)
app.secret_key = "HERIS2026"

DB = "stok.db"


def baglan():
    return sqlite3.connect(DB)


def kurulum():
    con = baglan()
    c = con.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS urun(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barkod TEXT,
        ad TEXT,
        cins TEXT,
        marka TEXT,
        ebat TEXT,
        tip TEXT,
        sinif TEXT,
        renk TEXT,
        yuzey TEXT,
        stok INTEGER,
        fiyat REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS satis(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        urun TEXT,
        fiyat REAL
    )
    """)

    con.commit()
    con.close()


kurulum()


def yeni_barkod():
    return str(random.randint(1000000000000,9999999999999))


style = """
<style>
body{
background:#07111f;
color:white;
font-family:Arial;
padding:20px;
}

input,select{
padding:10px;
margin:5px;
width:220px;
}

button{
padding:12px;
background:#16a34a;
color:white;
border:0;
border-radius:8px;
}

.card{
background:#111827;
padding:15px;
margin:10px;
border-radius:12px;
}

h1{
color:#22c55e;
}
</style>
"""


@app.route("/admin",methods=["GET","POST"])
def admin():

    if request.method=="POST":

        if request.form["sifre"]=="1234":
            session["admin"]=True
            return redirect("/panel")


    return style+"""
    <h1>HER-İŞ STOK PRO</h1>
    <h3>Admin Giriş</h3>

    <form method="post">

    <input type="password" name="sifre" placeholder="Şifre">

    <button>Giriş</button>

    </form>
    """



@app.route("/panel",methods=["GET","POST"])
def panel():

    if not session.get("admin"):
        return redirect("/admin")


    con=baglan()


    if request.method=="POST":

        con.execute("""
        INSERT INTO urun
        VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
        yeni_barkod(),
        request.form["ad"],
        request.form["cins"],
        request.form["marka"],
        request.form["ebat"],
        request.form["tip"],
        request.form["sinif"],
        request.form["renk"],
        request.form["yuzey"],
        request.form["stok"],
        request.form["fiyat"]
        ))

        con.commit()


    urunler=con.execute(
        "SELECT * FROM urun"
    ).fetchall()


    html=style+"""

<h1>ÜRÜN PANELİ</h1>


<form method="post">

<input name="ad" placeholder="Ürün adı">

<input name="cins" placeholder="Cins">

<input name="marka" placeholder="Marka">

<input name="ebat" placeholder="Ebat mm">


<select name="tip">

<option>HG</option>
<option>MAT</option>

</select>


<input name="sinif" placeholder="Sınıf">

<input name="renk" placeholder="Renk">

<input name="yuzey" placeholder="Yüzey">

<input name="stok" placeholder="Stok">

<input name="fiyat" placeholder="Satış fiyat">


<button>Kaydet</button>

</form>

<h2>Stok Listesi</h2>

"""


    for u in urunler:

        html += f"""

<div class="card">

<b>{u[2]}</b><br>

Barkod: {u[1]}<br>

Cins: {u[3]}<br>

Ebat: {u[5]}<br>

Tip: {u[6]}<br>

Sınıf: {u[7]}<br>

Renk: {u[8]}<br>

Stok: {u[10]}<br>

Fiyat: {u[11]} TL

</div>

"""


    con.close()

    return html




sepet=[]


@app.route("/")
@app.route("/pos",methods=["GET","POST"])
def pos():

    global sepet

    con=baglan()


    if request.method=="POST":

        barkod=request.form["barkod"]


        urun=con.execute(
        "SELECT * FROM urun WHERE barkod=?",
        (barkod,)
        ).fetchone()


        if urun:

            sepet.append(
            (urun[2],urun[11])
            )

            con.execute(
            "INSERT INTO satis VALUES(NULL,?,?)",
            (urun[2],urun[11])
            )

            con.commit()



    html=style+"""

<h1>🌲 ORMAN KASA PRO</h1>


<button onclick="kamera()">📷 Kamera Barkod Oku</button>

<div id="reader"></div>


<form method="post">

<input id="barkod"
name="barkod"
placeholder="Barkod okut">


<button>EKLE</button>

</form>


<h2>Sepet</h2>

"""


    toplam=0


    for s in sepet:

        html+=f"""

<div class="card">

{s[0]} - {s[1]} TL

</div>

"""

        toplam+=s[1]


    html+=f"""

<h1>TOPLAM: {toplam} TL</h1>


<script src="https://unpkg.com/html5-qrcode"></script>


<script>

function kamera(){


let scanner =
new Html5QrcodeScanner(
"reader",
{
fps:10,
qrbox:250
});


scanner.render(function(text){

document.getElementById("barkod").value=text;

scanner.clear();

});

}

</script>

"""


    con.close()

    return html



# Render burada app.run istemez
