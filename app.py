import sqlite3
import random
from flask import Flask, request, redirect, session

app = Flask(__name__)
app.secret_key = "HERIS2026"

DB = "stok.db"


def db():
    return sqlite3.connect(DB)


def setup():

    con=db()
    c=con.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS urun(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barkod TEXT,
        ad TEXT,
        cins TEXT,
        ebat TEXT,
        tip TEXT,
        sinif TEXT,
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


setup()


def barkod():
    return str(random.randint(1000000000000,9999999999999))


CSS="""
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
background:#22c55e;
border:0;
color:white;
border-radius:8px;
}

.card{
background:#111827;
padding:15px;
margin:10px;
border-radius:10px;
}

</style>
"""


@app.route("/admin",methods=["GET","POST"])
def admin():

    if request.method=="POST":

        if request.form["sifre"]=="1234":

            session["admin"]=True
            return redirect("/panel")


    return CSS+"""
    <h1>🌲 HER-İŞ STOK PRO</h1>

    <form method="post">

    <input type="password"
    name="sifre"
    placeholder="Şifre">

    <button>Giriş</button>

    </form>
    """



@app.route("/panel",methods=["GET","POST"])
def panel():

    if not session.get("admin"):
        return redirect("/admin")


    con=db()


    if request.method=="POST":

        con.execute("""
        INSERT INTO urun
        VALUES(NULL,?,?,?,?,?,?,?,?)
        """,
        (
        barkod(),
        request.form["ad"],
        request.form["cins"],
        request.form["ebat"],
        request.form["tip"],
        request.form["sinif"],
        request.form["stok"],
        request.form["fiyat"]
        ))

        con.commit()



    urunler=con.execute(
        "SELECT * FROM urun"
    ).fetchall()


    html=CSS+"""

<h1>ÜRÜN EKLE</h1>


<form method="post">

<input name="ad" placeholder="Ürün adı">

<input name="cins" placeholder="Cins">

<input name="ebat" placeholder="Ebat mm">

<select name="tip">
<option>HG</option>
<option>MAT</option>
</select>

<input name="sinif" placeholder="Sınıf">

<input name="stok" placeholder="Stok">

<input name="fiyat" placeholder="Fiyat">


<button>KAYDET</button>

</form>


<h2>STOK</h2>

"""


    for u in urunler:

        html+=f"""

<div class="card">

<b>{u[2]}</b><br>

Barkod: {u[1]}<br>

Cins: {u[3]}<br>

Ebat: {u[4]}<br>

Tip: {u[5]}<br>

Sınıf: {u[6]}<br>

Stok: {u[7]}<br>

Fiyat: {u[8]} TL

</div>

"""


    con.close()

    return html



sepet=[]


@app.route("/")
@app.route("/pos",methods=["GET","POST"])
def pos():

    global sepet

    con=db()


    if request.method=="POST":

        b=request.form["barkod"]


        u=con.execute(
        "SELECT * FROM urun WHERE barkod=?",
        (b,)
        ).fetchone()


        if u:

            sepet.append(
            (u[2],u[8])
            )

            con.execute(
            "INSERT INTO satis VALUES(NULL,?,?)",
            (u[2],u[8])
            )

            con.commit()



    html=CSS+"""

<h1>🌲 ORMAN KASA PRO</h1>


<form method="post">

<input autofocus
name="barkod"
placeholder="Barkod okut">

<button>EKLE</button>

</form>


<h2>SEPET</h2>

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

<h1>TOPLAM {toplam} TL</h1>

"""


    con.close()

    return html
