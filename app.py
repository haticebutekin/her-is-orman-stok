from flask import Flask, request, redirect, session, render_template_string
import sqlite3
import os
from openpyxl import Workbook
from flask import send_file
from datetime import datetime
import barcode
from barcode.writer import ImageWriter


app = Flask(__name__)
app.config["PROPAGATE_EXCEPTIONS"] = True
app.secret_key = "her_is_orman_stok_pro"


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
"HGLOSS DEPOSU",
"SÜTÇÜ YANI",
"HELVACI YANI",
"RÖTBALANSÇI YANI",
"KESİMHANE"
]


if os.path.exists("static") and not os.path.isdir("static"):
    os.remove("static")

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



    con.execute("""
    CREATE TABLE IF NOT EXISTS hareketler(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    urun_id INTEGER,

    islem TEXT,

    adet INTEGER,

    tarih TEXT

    )
    """)



    con.commit()

    return con





def yeni_barkod():

    con=baglan()

    sayi=con.execute(
    "SELECT COUNT(*) FROM urunler"
    ).fetchone()[0]

    con.close()


    return "HER-"+str(sayi+1).zfill(6)





def barkod_olustur(kod):

    os.makedirs("static", exist_ok=True)

    yol=os.path.join("static", kod)

    img=barcode.get(
        "code128",
        kod,
        writer=ImageWriter()
    )

    img.save(yol)

@app.route("/",methods=["GET","POST"])
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

box-shadow:0 0 20px #000;

}


input{

width:90%;
padding:12px;
margin:8px;

}


button{

background:#2563eb;
color:white;
padding:12px;
width:95%;
border:0;
border-radius:10px;

}

</style>



<div class="login">


<h2>
HER İŞ ORMAN
<br>
STOK PRO
</h2>


<form method="post">


<input name="user" placeholder="Kullanıcı adı">


<input name="pass"
type="password"
placeholder="Şifre">



<button>
GİRİŞ
</button>


</form>


</div>


""")





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



    ara=request.args.get("ara","")



    if ara:


        urunler=con.execute("""

        SELECT *
        FROM urunler
        WHERE isim LIKE ?
        OR barkod LIKE ?

        ORDER BY id DESC

        """,

        (
        "%"+ara+"%",
        "%"+ara+"%"
        )).fetchall()


    else:


        urunler=con.execute("""

        SELECT *
        FROM urunler
        ORDER BY id DESC

        """).fetchall()



    con.close()



    return render_template_string("""

<style>

body{

font-family:Arial;
background:#eef2f7;
padding:20px;

}


.kutu{

background:white;
padding:25px;
border-radius:20px;

}


input,select{

padding:10px;
margin:5px;

}


button{

background:#16a34a;
color:white;
padding:10px;
border:0;
border-radius:8px;

}



table{

width:100%;
border-collapse:collapse;
margin-top:20px;

}


td,th{

border:1px solid #ccc;
padding:8px;
text-align:center;

}


th{

background:#2563eb;
color:white;

}


img{

width:130px;

}

</style>




<div class="kutu">


<h1>
HER İŞ ORMAN ÜRÜNLERİ STOK TAKİBİ
</h1>



<a href="/kamera">
📱 Barkod Oku
</a>

&nbsp;


<a href="/rapor">
📊 Rapor
</a>



<hr>



<form method="get">

<input name="ara"
placeholder="Barkod veya ürün ara">

<button>
ARA
</button>

</form>



<hr>



<h2>
Yeni Ürün
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

<option>{{d}}</option>

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
<th>Renk</th>
<th>Adet</th>
<th>Depo</th>
<th>İşlem</th>

</tr>



{%for x in urunler%}


<tr>


<td>{{x[1]}}</td>


<td>

<img src="/static/{{x[1]}}.png">

</td>


<td>{{x[2]}}</td>

<td>{{x[3]}}</td>

<td>{{x[4]}}</td>

<td>{{x[8]}}</td>

<td>{{x[9]}}</td>

<td>{{x[10]}}</td>
<td>

<a href="/stok/{{x[0]}}/arttir">
<button style="background:green">
+
</button>
</a>


<a href="/stok/{{x[0]}}/azalt">
<button style="background:red">
-
</button>
</a>


<a href="/sil/{{x[0]}}">
<button style="background:black">
SİL
</button>
</a>


</td>


</tr>


{%endfor%}


</table>


</div>


""",
urunler=urunler,
depolar=DEPOLAR)

@app.route("/stok/<int:id>/<islem>")
def stok(id,islem):

    if "user" not in session:
        return redirect("/")


    con=baglan()


    urun=con.execute(
        "SELECT adet,isim FROM urunler WHERE id=?",
        (id,)
    ).fetchone()



    if urun:

        eski=urun[0]


        if islem=="arttir":

            yeni=eski+1
            hareket="STOK GİRİŞ"


        elif islem=="azalt":

            yeni=max(0,eski-1)
            hareket="STOK ÇIKIŞ"


        con.execute(
        """
        UPDATE urunler
        SET adet=?
        WHERE id=?
        """,
        (
        yeni,
        id
        ))



        con.execute(
        """
        INSERT INTO hareketler
        VALUES(NULL,?,?,?,?)
        """,
        (
        id,
        hareket,
        1,
        datetime.now().strftime("%d.%m.%Y %H:%M")
        ))


        con.commit()



    con.close()


    return redirect("/panel")

    if "user" not in session:
        return redirect("/")


    con=baglan()


    urun=con.execute(
        "SELECT adet FROM urunler WHERE id=?",
        (id,)
    ).fetchone()


    if urun:

        mevcut=urun[0]


        if islem=="arttir":

            yeni=mevcut+1
            hareket="STOK GİRİŞ"


        else:

            yeni=max(0,mevcut-1)
            hareket="STOK ÇIKIŞ"



        con.execute(
        """
        UPDATE urunler
        SET adet=?
        WHERE id=?
        """,
        (
        yeni,
        id
        )
        )


        con.execute(
        """
        INSERT INTO hareketler
        VALUES(NULL,?,?,?,?)
        """,
        (
        id,
        hareket,
        1,
        datetime.now().strftime("%d.%m.%Y %H:%M")
        )
        )


        con.commit()


    con.close()


    return redirect("/panel")





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






@app.route("/rapor")
def rapor():


    if "user" not in session:
        return redirect("/")



    con=baglan()


    toplam=con.execute(
    "SELECT SUM(adet) FROM urunler"
    ).fetchone()[0]


    cesit=con.execute(
    "SELECT COUNT(*) FROM urunler"
    ).fetchone()[0]


    hareketler=con.execute(
    """
    SELECT *
    FROM hareketler
    ORDER BY id DESC
    """
    ).fetchall()



    con.close()



    return render_template_string("""

<h1>
HER İŞ STOK RAPOR
</h1>


<h2>
Ürün Çeşidi:
{{cesit}}
</h2>


<h2>
Toplam Stok:
{{toplam}}
</h2>


<hr>


<table border="1" width="100%">


<tr>

<th>Ürün ID</th>
<th>İşlem</th>
<th>Adet</th>
<th>Tarih</th>

</tr>


{%for h in hareketler%}

<tr>

<td>{{h[1]}}</td>

<td>{{h[2]}}</td>

<td>{{h[3]}}</td>

<td>{{h[4]}}</td>


</tr>


{%endfor%}


</table>


<br>

<a href="/panel">
Panele Dön
</a>


""",

cesit=cesit,

toplam=toplam or 0,

hareketler=hareketler

)





@app.route("/kamera")
def kamera():

    if "user" not in session:
        return redirect("/")


    return render_template_string("""

<!DOCTYPE html>

<html>

<head>

<meta name="viewport" content="width=device-width,initial-scale=1">


<script src="https://unpkg.com/html5-qrcode"></script>


</head>


<body>


<h2>
Telefon Barkod Okuyucu
</h2>


<div id="reader"></div>



<script>


let scanner =
new Html5QrcodeScanner(

"reader",

{
fps:10,
qrbox:250
}

);



scanner.render(

function(kod){

window.location="/barkod/"+kod;

}

);


</script>


</body>


</html>


""")





@app.route("/barkod/<kod>")
def barkod_bul(kod):


    if "user" not in session:
        return redirect("/")



    con=baglan()



    urun=con.execute(
    """
    SELECT *
    FROM urunler
    WHERE barkod=?

    """,
    (kod,)
    ).fetchone()



    con.close()



    if urun:


        return render_template_string("""

<h1>
ÜRÜN BULUNDU
</h1>


<h2>
{{u[2]}}
</h2>


<p>
Cins:
{{u[3]}}
</p>


<p>
Ebat:
{{u[4]}}
</p>


<p>
Kalınlık:
{{u[5]}}
</p>


<p>
Sınıf:
{{u[6]}}
</p>


<p>
Yüzey:
{{u[7]}}
</p>


<p>
Renk:
{{u[8]}}
</p>


<p>
Stok:
{{u[9]}}
</p>


<a href="/panel">
Panele dön
</a>

""",
u=urun)



    return """

<h2>
Barkod bulunamadı
</h2>


<a href="/kamera">
Tekrar dene
</a>

"""
@app.route("/depolar")
def depolar():

    if "user" not in session:
        return redirect("/")


    con=baglan()


    liste=[]


    for d in DEPOLAR:

        sonuc=con.execute(
        """
        SELECT SUM(adet)
        FROM urunler
        WHERE depo=?
        """,
        (d,)
        ).fetchone()[0]


        liste.append(
        (
        d,
        sonuc or 0
        )
        )


    con.close()



    return render_template_string("""

<h1>
DEPO STOK DURUMU
</h1>


<table border="1" width="100%">


<tr>
<th>Depo</th>
<th>Toplam Adet</th>
</tr>


{% for x in liste %}

<tr>

<td>{{x[0]}}</td>

<td>{{x[1]}}</td>

</tr>


{% endfor %}


</table>


<br>

<a href="/panel">
Panele Dön
</a>


""",
liste=liste)


@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")





@app.route("/")
def ana_kontrol():

    return redirect("/login")





if __name__=="__main__":


    app.run(

        host="0.0.0.0",

        port=int(
            os.environ.get(
                "PORT",
                10000
            )
        )

    )
    
