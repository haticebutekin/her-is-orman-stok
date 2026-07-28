from flask import Flask, request, redirect, render_template_string, jsonify
import sqlite3, os
import barcode, qrcode
from barcode.writer import ImageWriter

app = Flask(__name__)

DB = "stok.db"

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

def db():
    return sqlite3.connect(DB)

# TABLOLAR
with db() as con:
    con.execute("""
    CREATE TABLE IF NOT EXISTS urun(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad TEXT,cins TEXT,ebat TEXT,kalinlik TEXT,
    yuzey TEXT,sinif TEXT,renk TEXT,
    adet INTEGER,depo TEXT,barkod TEXT UNIQUE
    )
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS hareket(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barkod TEXT,islem TEXT,adet INTEGER,
    tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

# NUMERİK BARKOD (DAHA HIZLI OKUNUR)
def barkod_uret():
    with db() as con:
        sayi = con.execute("SELECT COUNT(*) FROM urun").fetchone()[0] + 1
    return str(100000000000 + sayi)

# BARKOD RESİM
def barkod_resim(kod):

    klasor = "static"

    # Eğer static dosya ise sil
    if os.path.exists(klasor) and not os.path.isdir(klasor):
        os.remove(klasor)

    # klasör yoksa oluştur
    if not os.path.exists(klasor):
        os.makedirs(klasor)


    yol = os.path.join(klasor, kod)

    CODE128 = barcode.get_barcode_class("code128")

    img = CODE128(kod, writer=ImageWriter())

    img.save(
        yol,
        options={
            "module_width":0.6,
            "module_height":40,
            "font_size":20,
            "quiet_zone":10
        }
    )

# QR
def qr_uret(kod):
    if not os.path.exists("static"):
        os.mkdir("static")

    img = qrcode.make(kod)
    img.save("static/"+kod+"_qr.png")

# ANA SAYFA
@app.route("/")
def index():
    return """
    <style>
    body{font-family:Arial;background:#111;color:white;text-align:center}
    a{display:block;margin:15px;padding:15px;background:#00b894;color:white;border-radius:10px;text-decoration:none}
    </style>

    <h1>📦 HER İŞ ORMAN STOK PRO</h1>

    <a href="/ekle">➕ Ürün Ekle</a>
    <a href="/liste">📋 Liste</a>
    <a href="/kamera/giris">📥 Mal Giriş</a>
    <a href="/kamera/cikis">📤 Mal Çıkış</a>
    """

# ÜRÜN EKLE
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method=="POST":

        barkod = request.form.get("barkod")
        if not barkod:
            barkod = barkod_uret()

        try:
            with db() as con:
                con.execute("""
                INSERT INTO urun(ad,cins,ebat,kalinlik,yuzey,sinif,renk,adet,depo,barkod)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                """,(
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
            return "HATA: "+str(e)

        return redirect("/liste")

    return render_template_string("""
    <style>
    body{font-family:Arial;background:#222;color:white}
    form{background:#333;padding:20px;border-radius:15px;width:350px;margin:auto}
    input,select{width:100%;padding:10px;margin:5px}
    button{background:#00b894;color:white;padding:10px;border:0}
    </style>

    <form method="post">
    <h2>Ürün Kartı</h2>

    <input name="ad" placeholder="Malın Adı">
    <input name="cins" placeholder="Cinsi">
    <input name="ebat" placeholder="Ebat mm">
    <input name="kalinlik" placeholder="Kalınlık">

    <select name="yuzey">
    <option>HG</option><option>MAT</option><option>PARLAK</option>
    </select>

    <input name="sinif" placeholder="Sınıf">
    <input name="renk" placeholder="Renk">
    <input name="adet" type="number" placeholder="Adet">

    <select name="depo">
    {% for d in depolar %}
    <option>{{d}}</option>
    {% endfor %}
    </select>

    <input name="barkod" placeholder="Boş = otomatik">

    <button>KAYDET</button>
    </form>
    """, depolar=DEPOLAR)

# LİSTE
@app.route("/liste")
def liste():
    with db() as con:
        urunler = con.execute("SELECT * FROM urun").fetchall()

    html = "<h2 style='text-align:center'>STOK</h2>"

    for u in urunler:
        html += f"""
        <div style="background:#eee;margin:10px;padding:10px;border-radius:10px">
        <b>{u[1]}</b><br>
        {u[2]} - {u[3]} - {u[4]}<br>
        {u[5]} / {u[6]} / {u[7]}<br>
        Stok: {u[8]}<br>
        Depo: {u[9]}<br>

        <img src="/static/{u[10]}_qr.png" width="120"><br>
        <img src="/static/{u[10]}.png" width="250"><br>

        <a href="/etiket/{u[10]}">Etiket Yazdır</a>
        </div>
        """

    return html

# ETİKET
@app.route("/etiket/<kod>")
def etiket(kod):
    return f"""
    <h2>{kod}</h2>
    <img src="/static/{kod}_qr.png" width="200"><br>
    <img src="/static/{kod}.png" width="400">
    <script>window.print()</script>
    """

# HIZLI İŞLEM
@app.route("/hizli_islem", methods=["POST"])
def hizli():
    data = request.json
    barkod = data["barkod"]
    tip = data["tip"]

    with db() as con:
        urun = con.execute("SELECT ad,adet FROM urun WHERE barkod=?", (barkod,)).fetchone()

        if not urun:
            return jsonify({"ok":False})

        adet = urun[1]

        if tip=="cikis":
            if adet<=0:
                return jsonify({"ok":False})
            adet -= 1
            islem="ÇIKIŞ"
        else:
            adet += 1
            islem="GİRİŞ"

        con.execute("UPDATE urun SET adet=? WHERE barkod=?", (adet,barkod))
        con.execute("INSERT INTO hareket(barkod,islem,adet) VALUES(?,?,?)",(barkod,islem,adet))

    return jsonify({"ok":True,"ad":urun[0],"adet":adet})

# KAMERA (QR + BARKOD)
@app.route("/kamera/<tip>")
def kamera(tip):
    return render_template_string(f"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body{{background:#000;color:white;text-align:center;font-family:Arial}}
video{{width:90%;border-radius:15px}}
</style>

</head>

<body>

<h2>📷 Okut</h2>

<video id="video" autoplay muted playsinline></video>

<div id="sonuc">Kamera açılıyor...</div>

<script src="https://unpkg.com/@zxing/library@0.20.0"></script>

<script>

const video=document.getElementById("video");
const sonuc=document.getElementById("sonuc");

navigator.mediaDevices.getUserMedia({{
video:{{facingMode:"environment"}}
}})

.then(stream=>{{
video.srcObject=stream;
video.play();

const hints=new Map();
hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS,[
ZXing.BarcodeFormat.QR_CODE,
ZXing.BarcodeFormat.CODE_128
]);

const reader=new ZXing.BrowserMultiFormatReader(hints);

reader.decodeFromVideoElement(video,(result,err)=>{{

if(result){{
navigator.vibrate(200);

fetch("/hizli_islem",{{
method:"POST",
headers:{{"Content-Type":"application/json"}},
body:JSON.stringify({{
barkod:result.text,
tip:"{tip}"
}})
}})
.then(r=>r.json())
.then(data=>{{

if(data.ok){{
sonuc.innerHTML="✅ "+data.ad+"<br>Stok:"+data.adet;
}}else{{
sonuc.innerHTML="❌ Ürün yok";
}}

}});

}}

}});

}})

.catch(err=>{{
sonuc.innerHTML="Kamera hatası:"+err;
}});

</script>

</body>
</html>
""")

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000)
