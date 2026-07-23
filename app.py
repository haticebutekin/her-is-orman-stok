from flask import Flask, request, redirect, session, render_template_string
import sqlite3
import os
from datetime import datetime
import barcode
from barcode.writer import ImageWriter


app = Flask(__name__)
app.secret_key = "her_is_orman_stok"


DB = "stok.db"


USERS = {
    "behic": "123",
    "ramazan": "123",
    "orhan": "123"
}


DEPOLAR = [
    "MDF SATIŞ DEPOSU",
    "LAMİNANT DEPOSU",
    "KAPI DEPOSU",
    "HGLOSS DEPOSU",
    "SÜTÇÜ YANI",
    "HELVACI YANI",
    "RÖTBALANSÇI YANI",
    "KESİMHANE"
]


if not os.path.exists("static"):
    os.mkdir("static")



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

    con = baglan()

    sayi = con.execute(
        "SELECT COUNT(*) FROM urunler"
    ).fetchone()[0]

    con.close()

    return "HIS-" + str(sayi+1).zfill(6)



def barkod_resmi(kod):

    yol = "static/" + kod

    img = barcode.get(
        "code128",
        kod,
        writer=ImageWriter()
    )

    img.save(yol)




@app.route("/", methods=["GET","POST"])
def login():


    if request.method=="POST":

        kullanici=request.form["user"]

        sifre=request.form["pass"]


        if kullanici in USERS and USERS[kullanici]==sifre:

            session["user"]=kullanici

            return redirect("/panel")



    return render_template_string("""
    
    <style>

    body{
    background:#111827;
    font-family:Arial;
    }

    .login{

    width:350px;
    margin:120px auto;
    background:white;
    padding:30px;
    border-radius:20px;
    text-align:center;

    }

    input{

    width:90%;
    padding:12px;
    margin:10px;

    }


    button{

    width:95%;
    padding:12px;
    background:#2563eb;
    color:white;
    border:0;
    border-radius:10px;

    }

    </style>


    <div class="login">

    <h2>
    HER İŞ ORMAN
    <br>
    STOK SİSTEMİ
    </h2>


    <form method="post">

    <input name="user" placeholder="Kullanıcı">

    <input name="pass" type="password" placeholder="Şifre">

    <button>
    GİRİŞ
    </button>

    </form>

    </div>

    """)

@app.route("/panel", methods=["GET","POST"])
def panel():

    if "user" not in session:
        return redirect("/")


    con=baglan()


    if request.method=="POST":

        kod=barkod_uret()

        barkod_resmi(kod)


        con.execute("""

        INSERT INTO urunler
        (
        barkod,
        isim,
        cins,
        ebat,
        kalinlik,
        sinif,
        yuzey,
        renk,
        adet,
        depo,
        tarih
        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?)

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



    arama=request.args.get("ara","")


    if arama:


        urunler=con.execute(
        """
        SELECT *
        FROM urunler
        WHERE isim LIKE ?
        OR barkod LIKE ?
        ORDER BY id DESC
        """,
        (
        "%"+arama+"%",
        "%"+arama+"%"
        )

        ).fetchall()


    else:


        urunler=con.execute(
        """
        SELECT *
        FROM urunler
        ORDER BY id DESC
        """
        ).fetchall()



    con.close()



    return render_template_string("""

<style>

body{

font-family:Arial;
background:#eef2f7;
padding:15px;

}


.kutu{

background:white;
padding:25px;
border-radius:20px;

box-shadow:0 5px 20px #ccc;

}



input,select{

padding:10px;
margin:5px;

border-radius:8px;

border:1px solid #ccc;

}


button{

padding:10px 20px;

background:#16a34a;

color:white;

border:0;

border-radius:8px;

cursor:pointer;

}


table{

width:100%;

border-collapse:collapse;

margin-top:20px;

}


th{

background:#1d4ed8;

color:white;

}


td,th{

padding:10px;

border:1px solid #ddd;

text-align:center;

}



img{

width:130px;

}



.ust{

display:flex;

justify-content:space-between;

}


a{

color:red;

}

</style>



<div class="kutu">


<div class="ust">

<h1>
HER İŞ ORMAN
<br>
STOK TAKİP PANELİ
</h1>


<a href="/logout">
ÇIKIŞ
</a>


</div>



<form method="get">


<input 
name="ara"
placeholder="Barkod veya ürün ara"
>


<button>
ARA
</button>


</form>



<hr>



<h2>
Yeni Ürün Ekle
</h2>


<form method="post">


<input name="isim" placeholder="Malın adı">


<input name="cins" placeholder="Malın cinsi">


<input name="ebat" placeholder="Ebat mm">


<input name="kalinlik" placeholder="Kalınlık">


<input name="sinif" placeholder="Sınıf">


<select name="yuzey">

<option>HG</option>

<option>MAT</option>

<option>PARLAK</option>

</select>



<input name="renk" placeholder="Renk">


<input name="adet" placeholder="Adet">


<select name="depo">

{% for d in depolar %}

<option>
{{d}}
</option>

{% endfor %}

</select>



<button>
KAYDET
</button>


</form>



<table>


<tr>

<th>Barkod</th>

<th>Etiket</th>

<th>Ürün</th>

<th>Cins</th>

<th>Ebat</th>

<th>Sınıf</th>

<th>Yüzey</th>

<th>Renk</th>

<th>Adet</th>

<th>Depo</th>

</tr>



{% for x in urunler %}


<tr>


<td>

{{x[1]}}

</td>



<td>

<img src="/static/{{x[1]}}.png">

</td>



<td>

{{x[2]}}

</td>


<td>

{{x[3]}}

</td>


<td>

{{x[4]}}

</td>


<td>

{{x[6]}}

</td>


<td>

{{x[7]}}

</td>


<td>

{{x[8]}}

</td>


<td>

{{x[9]}}

</td>


<td>

{{x[10]}}

</td>



</tr>


{% endfor %}



</table>


</div>


""",

urunler=urunler,
depolar=DEPOLAR

)

@app.route("/sil/<int:id>")
def sil(id):

    if "user" not in session:
        return redirect("/")


    con=baglan()

    con.execute(
        "DELETE FROM urunler WHERE id=?",
        (id,)
    )

    con.commit()

    con.close()


    return redirect("/panel")





@app.route("/stok/<int:id>/<islem>")
def stok(id,islem):

    if "user" not in session:
        return redirect("/")


    con=baglan()


    urun=con.execute(
        "SELECT adet FROM urunler WHERE id=?",
        (id,)
    ).fetchone()



    if urun:


        adet=urun[0]


        if islem=="arttir":

            adet+=1


        elif islem=="azalt" and adet>0:

            adet-=1



        con.execute(
        """
        UPDATE urunler
        SET adet=?
        WHERE id=?
        """,
        (
        adet,
        id
        )
        )


        con.commit()



    con.close()


    return redirect("/panel")





@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")





if __name__=="__main__":

    app.run(

    host="0.0.0.0",

    port=int(
    os.environ.get(
    "PORT",
    10000
    ))

    )
