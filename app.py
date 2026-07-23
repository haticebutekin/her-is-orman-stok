import sqlite3
import os
from datetime import datetime
import barcode
from barcode.writer import ImageWriter
from flask import Flask, request, redirect, session, render_template_string
import sqlite3
import os
from datetime import datetime


app = Flask(__name__)
app.secret_key = "her_is_orman_stok"



DB = "stok.db"


USERS = {
    "behic":"123",
    "ramazan":"123",
    "orhan":"123"
}



DEPOLAR = [
    "MDF SATIŞ DEPOSU",
    "LAMİNANT DEPOSU",
    "KAPI DEPOSU",
    "HGLOSS DEPOSU (MORAY YANI)",
    "SÜTÇÜ YANI",
    "HELVACI YANI",
    "RÖTBALANSÇI YANI",
    "KESİMHANE"
]



def baglan():

    con = sqlite3.connect(DB)

    con.execute("""
    CREATE TABLE IF NOT EXISTS urunler(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    barkod TEXT,

    isim TEXT,

    cins TEXT,

    ebat TEXT,

    kalinlik TEXT,

    sinif TEXT,

    yuzey TEXT,

    renk TEXT,

    adet INTEGER,

    depo TEXT,

    tarih TEXT

    )
    """)

    con.commit()

    return con




def barkod_uret():

    con=baglan()

    sayi=con.execute(
        "SELECT COUNT(*) FROM urunler"
    ).fetchone()[0]

    con.close()


    return "HERIS"+str(sayi+1).zfill(6)





@app.route("/",methods=["GET","POST"])
def login():


    if request.method=="POST":

        u=request.form["user"]
        p=request.form["pass"]


        if u in USERS and USERS[u]==p:

            session["user"]=u

            return redirect("/panel")



    return """

    <html>

    <body style="text-align:center;font-family:Arial">


    <h1>
    HER İŞ ORMAN ÜRÜNLERİ
    STOK TAKİBİ
    </h1>


    <form method="post">


    Kullanıcı

    <br>

    <input name="user">


    <br><br>


    Şifre

    <br>

    <input name="pass" type="password">


    <br><br>


    <button>

    GİRİŞ

    </button>


    </form>


    </body>

    </html>

    """






@app.route("/panel",methods=["GET","POST"])
def panel():


    if "user" not in session:

        return redirect("/")



    con=baglan()



    if request.method=="POST":


        barkod=barkod_uret()

def barkod_resmi(barkod):

    dosya = f"static/{barkod}"

    EAN = barcode.get(
        "code128",
        barkod,
        writer=ImageWriter()
    )

    yol = EAN.save(dosya)

    return yol

        con.execute("""

        INSERT INTO urunler

        VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?)

        """,

        (

        barkod,

        request.form["isim"],

        request.form["cins"],

        request.form["ebat"],

        request.form["kalinlik"],

        request.form["sinif"],

        request.form["yuzey"],

        request.form["renk"],

        request.form["adet"],

        request.form["depo"],

        datetime.now().strftime("%d.%m.%Y %H:%M")

        ))


        con.commit()



    urunler=con.execute(
        "SELECT * FROM urunler ORDER BY id DESC"
    ).fetchall()



    con.close()



    return render_template_string("""

<style>

body{

font-family:Arial;

background:#eef2f3;

padding:20px;

}


.kutu{

background:white;

padding:20px;

border-radius:15px;

}


input,select{

padding:8px;

margin:5px;

}


button{

padding:10px;

background:#0b63ce;

color:white;

border:0;

}


table{

width:100%;

border-collapse:collapse;

}


td,th{

border:1px solid #ccc;

padding:8px;

}


</style>



<div class="kutu">


<h1>
HER İŞ ORMAN ÜRÜNLERİ STOK TAKİBİ
</h1>


Personel:
{{user}}



<form method="post">


Ürün Adı

<input name="isim">


Mal Cinsi

<input name="cins">


Ebat

<input name="ebat">


Kalınlık

<input name="kalinlik">


Sınıf

<input name="sinif">


Yüzey

<select name="yuzey">

<option>HG</option>

<option>MAT</option>

</select>



Renk

<input name="renk">



Adet

<input name="adet" type="number">



Depo

<select name="depo">

{%for d in depolar%}

<option>{{d}}</option>

{%endfor%}

</select>


<br>


<button>

KAYDET

</button>


</form>



<hr>



<table>


<tr>

<th>Barkod</th>
<th>Ürün</th>
<th>Cins</th>
<th>Ebat</th>
<th>Renk</th>
<th>Adet</th>
<th>Depo</th>

</tr>


{%for x in urunler%}

<tr>

<td>{{x[1]}}</td>

<td>{{x[2]}}</td>

<td>{{x[3]}}</td>

<td>{{x[4]}}</td>

<td>{{x[8]}}</td>

<td>{{x[9]}}</td>

<td>{{x[10]}}</td>


</tr>


{%endfor%}


</table>


</div>


""",
user=session["user"],
urunler=urunler,
depolar=DEPOLAR)





if __name__=="__main__":

    app.run(

    host="0.0.0.0",

    port=int(os.environ.get("PORT",10000))

    )
