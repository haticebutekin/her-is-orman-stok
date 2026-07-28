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



# OTOMATİK BARKOD
def barkod_uret():

    with db() as con:
        sayi = con.execute(
            "SELECT COUNT(*) FROM urun"
        ).fetchone()[0] + 1

    return "URUN-" + str(sayi).zfill(5)



# BARKOD RESİM
def barkod_resim(kod):

    os.makedirs("static",exist_ok=True)

    yol="static/"+kod

    CODE128 = barcode.get_barcode_class("code128")

    img = CODE128(
        kod,
        writer=ImageWriter()
    )

    img.save(yol)

    return kod+".png"



# QR
def qr_uret(kod):

    os.makedirs("static",exist_ok=True)

    img=qrcode.make(kod)

    img.save(
        "static/"+kod+"_qr.png"
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

<h2>
{k od}
</h2>

<img src="/static/{kod}.png">

<br>

<img src="/static/{kod}_qr.png">


<script>
window.print()
</script>

"""





@app.route("/hizli_islem",methods=["POST"])
def hizli():

    data=request.json


    barkod=data["barkod"]
    tip=data["tip"]



    with db() as con:

        u=con.execute(
        "SELECT ad,adet FROM urun WHERE barkod=?",
        (barkod,)
        ).fetchone()



        if not u:

            return jsonify(
            {"ok":False}
            )


        adet=u[1]


        if tip=="cikis":

            adet-=1

        else:

            adet+=1



        con.execute(
        "UPDATE urun SET adet=? WHERE barkod=?",
        (adet,barkod)
        )


    return jsonify(
    {
    "ok":True,
    "ad":u[0],
    "adet":adet
    }
    )





@app.route("/kamera/<tip>")
def kamera(tip):


    return f"""

<video id="video"
width="350"
autoplay>
</video>


<h2 id="sonuc">
Hazır
</h2>


<script src="
https://unpkg.com/@zxing/library@latest">
</script>


<script>


let reader =
new ZXing.BrowserBarcodeReader();



reader.decodeFromVideoDevice(
null,
"video",

(result,error)=>{{


if(result){{


fetch("/hizli_islem",
{{

method:"POST",

headers:
{{
"Content-Type":"application/json"
}},

body:JSON.stringify(
{{
barkod:result.text,
tip:"{tip}"
}}
)

}}

)

.then(x=>x.json())

.then(data=>{{

sonuc.innerHTML=
data.ad+" Kalan:"+data.adet;


}})


}}


})


</script>


"""




if __name__=="__main__":

    app.run(
    host="0.0.0.0",
    port=5000
    )
