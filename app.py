from flask import Flask, request, redirect, render_template_string, jsonify
import sqlite3, os
import barcode, qrcode
from barcode.writer import ImageWriter

app = Flask(__name__)
DB = "stok.db"

# STATIC FIX
if os.path.exists("static") and not os.path.isdir("static"):
    os.remove("static")
if not os.path.exists("static"):
    os.makedirs("static")

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

# TABLO
with db() as con:
    con.execute("""
    CREATE TABLE IF NOT EXISTS urun(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad TEXT,cins TEXT,ebat TEXT,kalinlik TEXT,
    yuzey TEXT,sinif TEXT,renk TEXT,
    adet INTEGER,depo TEXT,barkod TEXT UNIQUE
    )
    """)
with db() as con:
    con.execute("""
    CREATE TABLE IF NOT EXISTS hareket(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    barkod TEXT,
    ad TEXT,
    tip TEXT,
    adet INTEGER,
    tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

# BARKOD
def barkod_uret():
    with db() as con:
        sayi = con.execute("SELECT COUNT(*) FROM urun").fetchone()[0] + 1
    return str(100000000000 + sayi)

def barkod_resim(kod):
    yol = os.path.join("static", kod)
    CODE128 = barcode.get_barcode_class("code128")
    img = CODE128(kod, writer=ImageWriter())
    img.save(yol)

def qr_uret(kod):
    img = qrcode.make(kod)
    img.save(os.path.join("static", kod+"_qr.png"))

# ANA
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
    <a href="/hareketler">📊 Hareketler</a>
    """

# EKLE
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method=="POST":

        barkod = request.form.get("barkod") or barkod_uret()

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

        return redirect("/liste")

    return render_template_string("""
    <style>
    body{font-family:Arial;background:#222;color:white}
    form{background:#333;padding:20px;border-radius:15px;width:350px;margin:auto}
    input,select{width:100%;padding:10px;margin:5px}
    button{background:#00b894;color:white;padding:10px;border:0}
    </style>
    <a href="/" style="
    display:inline-block;
    margin:10px;
    padding:10px;
    background:#00b894;
    color:white;
    border-radius:10px;
    text-decoration:none;
    ">🏠 Ana Sayfa</a>
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

# LİSTE (ESKİ HALİN FULL)
@app.route("/liste")
def liste():
    with db() as con:
        urunler = con.execute("SELECT * FROM urun").fetchall()

    html = """
<div style='text-align:center'>
<a href="/" style="padding:10px;background:#00b894;color:white;border-radius:10px;text-decoration:none">🏠 Ana Sayfa</a>
<h2>STOK</h2>
</div>
"""

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
    
@app.route("/hareketler")
def hareketler():
    with db() as con:
        rows = con.execute("SELECT barkod, ad, tip, adet, tarih FROM hareket ORDER BY id DESC LIMIT 50").fetchall()

    html = """
    <div style="text-align:center">
    <a href="/" style="padding:10px;background:#00b894;color:white;border-radius:10px;text-decoration:none">🏠 Ana Sayfa</a>
    <h2>📊 Son Hareketler</h2>
    </div>
    """

    for r in rows:
        try:
            barkod, ad, tip, adet, tarih = r
        except:
            continue

        renk = "green" if tip == "giris" else "red"

        html += f"""
        <div style="background:#222;color:white;margin:5px;padding:10px;border-left:5px solid {renk}">
        {tarih} | {ad} | {tip.upper()} | Stok: {adet}
        </div>
        """

    return html
    
# HIZLI İŞLEM (FIX)
@app.route("/hizli_islem", methods=["POST"])
def hizli_islem():
    data = request.get_json()
    barkod = str(data.get("barkod")).strip()
    tip = data.get("tip")

    with db() as con:
        cur = con.cursor()

        # ÜRÜNÜ BUL
        cur.execute("SELECT id, ad, adet FROM urun WHERE barkod=?", (barkod,))
        row = cur.fetchone()
        
        if not row:
            return jsonify({"ok": False, "mesaj": "ÜRÜN YOK"})


        urun_id, ad, adet = row

        # 🔥 ARTIR / AZALT
        if tip == "giris":
            adet += 1
        else:
            adet -= 1

        if adet < 0:
            adet = 0

        # GÜNCELLE
        cur.execute("UPDATE urun SET adet=? WHERE id=?", (adet, urun_id))
        cur.execute("""
        INSERT INTO hareket (barkod, ad, tip, adet)
        VALUES (?, ?, ?, ?)
        """, (barkod, ad, tip, adet))
        con.commit()

    return jsonify({
        "ok": True,
        "ad": ad,
        "adet": adet
    })
    
# KAMERA (KESİN ÇALIŞAN)
from flask import render_template

@app.route("/kamera/<tip>")
def kamera(tip):
    return render_template("kamera.html")


@app.route("/kamera_test")
def kamera_test():
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body>

<div id="sonuc"></div>

<script>

fetch("/hizli_islem", {{
    method: "POST",
    headers: {{
        "Content-Type": "application/json"
    }},
    body: JSON.stringify({{
        barkod: "123",
        tip: "giris"
    }})
}})
.then(res => res.json())
.then(data => {{

    if(data.ok){{

        document.getElementById("sonuc").innerText =
            data.ad + " | Stok: " + data.adet;

        // 🔊 SES BURADA
        let bip = new Audio();
        bip.src = "https://actions.google.com/sounds/v1/alarms/alarm_clock.ogg";
        bip.play();

    }} else {{

        document.getElementById("sonuc").innerText = "❌ HATALI ÜRÜN!";

    }}

}})
.catch(err => console.log(err));

</script>

</body>
</html>
"""
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
    
 
