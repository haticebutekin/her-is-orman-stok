from flask import Flask,request,redirect,session,render_template_string,send_from_directory
import sqlite3
import os
from datetime import datetime
import barcode
from barcode.writer import ImageWriter


app=Flask(__name__)
app.secret_key="her_is_orman_stok"


DB="stok.db"


USERS={
"behic":"123",
"ramazan":"123",
"orhan":"123"
}


DEPOLAR=[
"MDF SATIŞ DEPOSU",
"LAMİNANT DEPOSU",
"KAPI DEPOSU",
"HGLOSS DEPOSU (MORAY YANI)",
"SÜTÇÜ YANI",
"HELVACI YANI",
"RÖTBALANSÇI YANI",
"KESİMHANE"
]


if not os.path.exists("static"):
    os.mkdir("static")



def baglan():

    con=sqlite3.connect(DB)

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



def yeni_barkod():

    con=baglan()

    adet=con.execute(
    "select count(*) from urunler"
    ).fetchone()[0]

    con.close()

    return "HIS-"+str(adet+1).zfill(6)



def barkod_olustur(kod):

    yol="static/"+kod

    code=barcode.get(
        "code128",
        kod,
        writer=ImageWriter()
    )

    code.save(yol)





@app.route("/",methods=["GET","POST"])
def login():

    if request.method=="POST":

        u=request.form["user"]
        p=request.form["pass"]


        if u in USERS and USERS[u]==p:

            session["user"]=u

            return redirect("/panel")


    return """

    <h1 style="text-align:center">
    HER İŞ ORMAN ÜRÜNLERİ
    STOK TAKİBİ
    </h1>


    <form method="post" style="text-align:center">

    Kullanıcı<br>
    <input name="user">

    <br><br>

    Şifre<br>
    <input name="pass" type="password">

    <br><br>

    <button>GİRİŞ</button>

    </form>

    """





@app.route("/panel",methods=["GET","POST"])
def panel():

    if "user" not in session:
        return redirect("/")


    con=baglan()


    if request.method=="POST":


        kod=yeni_barkod()

        barkod_olustur(kod)


        con.execute("""

        INSERT INTO urunler

        VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?)

        """,

        (

        kod,

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
    "select * from urunler order by id desc"
    ).fetchall()


    con.close()



    return render_template_string("""

<style>

body{
font-family:Arial;
background:#f2f2f2;
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

background:#0066cc;
color:white;
padding:10px;
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


<form method="post">


Ürün:
<input name="isim">


Cins:
<input name="cins">


Ebat:
<input name="ebat">


Kalınlık:
<input name="kalinlik">


Sınıf:
<input name="sinif">


Yüzey:

<select name="yuzey">
<option>HG</option>
<option>MAT</option>
</select>


Renk:
<input name="renk">


Adet:
<input name="adet">


Depo:

<select name="depo">

{%for d in depolar%}
<option>{{d}}</option>
{%endfor%}

</select>


<button>KAYDET</button>

</form>


<hr>


<table>

<tr>
<th>Barkod</th>
<th>Etiket</th>
<th>Ürün</th>
<th>Depo</th>
</tr>


{%for x in urunler%}

<tr>

<td>{{x[1]}}</td>

<td>
<img width="160"
src="/static/{{x[1]}}.png">
</td>

<td>{{x[2]}}</td>

<td>{{x[10]}}</td>

</tr>

{%endfor%}


</table>


</div>

""",
urunler=urunler,
depolar=DEPOLAR)



@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")



if __name__=="__main__":

    app.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT",10000))
    )
