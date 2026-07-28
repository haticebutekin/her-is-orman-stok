from flask import Flask, request, redirect, render_template_string, jsonify
import sqlite3
import os
import barcode
import qrcode
from barcode.writer import ImageWriter


app = Flask(__name__)


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


DB = "db.sqlite"


def db():
    return sqlite3.connect(DB)


# TABLO OLUŞTUR
with db() as con:
    con.execute("""
    CREATE TABLE IF NOT EXISTS urun(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT,
        cins TEXT,
        ebat TEXT,
        kalinlik TEXT,
        yuzey TEXT,
        sinif TEXT,
        renk TEXT,
        adet INTEGER,
        depo TEXT,
        barkod TEXT UNIQUE
    )
    """)

with db() as con:

    con.execute("""
    CREATE TABLE IF NOT EXISTS hareket(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barkod TEXT,
        islem TEXT,
        adet INTEGER,
        tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)



# OTOMATİK BARKOD
def barkod_uret():

    with db() as con:
        sayi = con.execute(
            "SELECT COUNT(*) FROM urun"
        ).fetchone()[0] + 1

    return "URUN-" + str(sayi).zfill(5)



# BARKOD RESİM
def barkod_resim(kod):

    klasor = "static"

    if os.path.exists(klasor) and not os.path.isdir(klasor):
        os.remove(klasor)

    if not os.path.exists(klasor):
        os.mkdir(klasor)


    yol = os.path.join(klasor, kod)


    CODE128 = barcode.get_barcode_class("code128")

    img = CODE128(
        kod,
        writer=ImageWriter()
    )

    img.save(yol)

    return kod + ".png"



# QR
def qr_uret(kod):

    klasor="static"

    if os.path.exists(klasor) and not os.path.isdir(klasor):
        os.remove(klasor)

    if not os.path.exists(klasor):
        os.mkdir(klasor)


    img=qrcode.make(kod)

    img.save(
        os.path.join(
            klasor,
            kod+"_qr.png"
        )
    )

@app.route("/")
def index():

    return """

    <style>

    body{
    font-family:Arial;
    background:#f1f2f6;
    text-align:center;
    }

    .box{
    background:white;
    padding:25px;
    width:320px;
    margin:50px auto;
    border-radius:20px;
    }

    a{
    display:block;
    padding:15px;
    margin:10px;
    background:#16a085;
    color:white;
    text-decoration:none;
    border-radius:10px;
    }

    </style>


    <div class="box">

    <h2>📦 HER İŞ ORMAN STOK</h2>

    <a href="/ekle">➕ Ürün Ekle</a>

    <a href="/liste">📋 Liste</a>

    <a href="/kamera/giris">
    📥 Mal Giriş
    </a>

    <a href="/kamera/cikis">
    📤 Mal Çıkış
    </a>


    </div>

    """




@app.route("/ekle",methods=["GET","POST"])
def ekle():

    if request.method=="POST":


        barkod=request.form.get("barkod")


        if not barkod:
            barkod=barkod_uret()



        try:

            with db() as con:

                con.execute("""
                INSERT INTO urun
                (
                ad,
                cins,
                ebat,
                kalinlik,
                yuzey,
                sinif,
                renk,
                adet,
                depo,
                barkod
                )

                VALUES(?,?,?,?,?,?,?,?,?,?)

                """,

                (
                request.form["ad"],
                request.form["cins"],
                request.form["ebat"],
                request.form["kalinlik"],
                request.form["yuzey"],
                request.form["sinif"],
                request.form["renk"],
                int(request.form["adet"]),
                request.form["depo"],
                barkod
                ))

            barkod_resim(barkod)
            qr_uret(barkod)


        except Exception as e:

            return "HATA : "+str(e)


        return redirect("/liste")



    return render_template_string("""

<style>

body{
font-family:Arial;
background:#eee;
}


form{

background:white;
padding:20px;
width:350px;
margin:auto;
border-radius:15px;

}


input,select,button{

width:100%;
padding:12px;
margin:5px;

}


button{

background:#16a085;
color:white;
border:0;
border-radius:8px;

}


</style>


<form method="post">


<h2>
Ürün Kartı
</h2>


<input name="ad" placeholder="Malın Adı">

<input name="cins" placeholder="Malın Cinsi">


<input name="ebat" placeholder="Ebat mm">


<input name="kalinlik" placeholder="Kalınlık">


<select name="yuzey">

<option>HG</option>

<option>MAT</option>

<option>PARLAK</option>

</select>



<input name="sinif" placeholder="Sınıf">

<input name="renk" placeholder="Renk">


<input name="adet"
type="number"
placeholder="Adet">


<select name="depo">

{% for d in depolar %}

<option>{{d}}</option>

{% endfor %}

</select>


<input name="barkod"
placeholder="Barkod boş = otomatik">


<button>
KAYDET
</button>


</form>


""",depolar=DEPOLAR)




@app.route("/liste")
def liste():

    with db() as con:

        urunler=con.execute(
        "SELECT * FROM urun"
        ).fetchall()



    html="""

<h2 style="text-align:center">
STOK LİSTESİ
</h2>

"""


    for u in urunler:


        html+=f"""

<div style="
background:white;
margin:15px;
padding:15px;
border-radius:15px">


<b>{u[1]}</b><br>

Cins: {u[2]}<br>

Ebat: {u[3]}<br>

Kalınlık: {u[4]}<br>

Yüzey: {u[5]}<br>

Sınıf: {u[6]}<br>

Renk: {u[7]}<br>

Adet: {u[8]}<br>

Depo: {u[9]}<br>

Barkod:
{u[10]}

<br><br>


<a href="/etiket/{u[10]}">
Etiket
</a>


</div>

"""


    return html


@app.route("/etiket/<kod>")
def etiket(kod):

    barkod_resim(kod)
    qr_uret(kod)

    return f"""

    <html>
    <body style="text-align:center;font-family:Arial">

    <h2>
    {kod}
    </h2>

    <img src="/static/{kod}.png"
    width="300">

    <br><br>

    <img src="/static/{kod}_qr.png"
    width="150">


    <script>
    window.print()
    </script>


    </body>
    </html>

    """

@app.route("/hizli_islem",methods=["POST"])
@app.route("/hizli_islem",methods=["POST"])
def hizli():

    data=request.json

    barkod=data["barkod"]
    tip=data["tip"]


    with db() as con:


        urun=con.execute(
        """
        SELECT 
        ad,
        cins,
        ebat,
        kalinlik,
        yuzey,
        depo,
        adet
        FROM urun 
        WHERE barkod=?
        """,
        (barkod,)
        ).fetchone()



        if not urun:

            return jsonify({
            "ok":False
            })



        adet=urun[6]


        if tip=="cikis":

            if adet<=0:

                return jsonify({
                "ok":False
                })

            adet-=1

            islem="ÇIKIŞ"


        else:

            adet+=1

            islem="GİRİŞ"



        con.execute(
        """
        UPDATE urun 
        SET adet=?
        WHERE barkod=?
        """,
        (adet,barkod)
        )



        con.execute(
        """
        INSERT INTO hareket
        (barkod,islem,adet)
        VALUES(?,?,?)
        """,
        (
        barkod,
        islem,
        adet
        )
        )



    return jsonify({

    "ok":True,

    "ad":urun[0],

    "cins":urun[1],

    "ebat":urun[2],

    "kalinlik":urun[3],

    "yuzey":urun[4],

    "depo":urun[5],

    "adet":adet

    })

@app.route("/kamera/<tip>")
def kamera(tip):

    return render_template_string("""
    
<!DOCTYPE html>
<html>

<head>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>

body{
font-family:Arial;
text-align:center;
}

video{

width:90%;
max-width:400px;
border-radius:15px;

}

#sonuc{

font-size:22px;
margin-top:20px;

}

</style>

</head>


<body>


<h2>📷 Barkod Okutma</h2>


<video 
id="video"
autoplay
muted
playsinline
style="
width:90%;
max-width:400px;
border-radius:15px;">
</video>


<div id="sonuc">
Kamera açılıyor...
</div>



<script src="https://unpkg.com/@zxing/library@0.20.0"></script>

<script>

const video = document.getElementById("video");
const sonuc = document.getElementById("sonuc");


navigator.mediaDevices.getUserMedia({

    video:{
        facingMode:{
            ideal:"environment"
        },
        width:{
            ideal:1280
        },
        height:{
            ideal:720
        }
    }

})

.then(stream=>{


    video.srcObject = stream;

    video.play();


    const reader = new ZXing.BrowserMultiFormatReader();


    reader.decodeFromVideoElement(
        video,
        (result,error)=>{


            if(result){


                sonuc.innerHTML="Okundu: "+result.text;


                fetch("/hizli_islem",{

                    method:"POST",

                    headers:{
                    "Content-Type":"application/json"
                    },


                    body:JSON.stringify({

                    barkod:result.text,

                    tip:""" + tip + """

                    })

                })

                .then(r=>r.json())

                .then(data=>{


                    if(data.ok){

                    sonuc.innerHTML =
                    "✅ "+data.ad+
                    "<br>Stok: "+data.adet;


                    }
                    else{

                    sonuc.innerHTML=
                    "❌ Ürün bulunamadı";

                    }


                });


            }


        }
    );


})

.catch(err=>{

    sonuc.innerHTML=
    "Kamera hatası: "+err;

});

</script>


</body>

</html>

""")
if __name__=="__main__":

    app.run(
    host="0.0.0.0",
    port=5000
    )
