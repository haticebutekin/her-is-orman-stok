from flask import Flask, request, redirect, render_template_string, jsonify
import sqlite3, os
import barcode, qrcode
from barcode.writer import ImageWriter

app = Flask(name)
DB = "stok.db"

STATIC FIX
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

TABLO
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
kullanici TEXT,
tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

BARKOD
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

ANA
@app.route("/")
def index():
return """
<style>
body{font-family;background:#111;color;text-align}
a{display;margin:15px;padding:15px;background:#00b894;color;border-radius:10px;text-decoration}
</style>

<h1>📦 HER İŞ ORMAN STOK PRO</h1>

<a href="/ekle">➕ Ürün Ekle</a>
<a href="/liste">📋 Liste</a>
<a href="/kamera/giris">📥 Mal Giriş</a>
<a href="/kamera/cikis">📤 Mal Çıkış</a>
<a href="/hareketler">📊 Hareketler</a>
"""

EKLE
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

<a href="/" style="padding:10px;background:#00b894;color:white;border-radius:10px;text-decoration:none">🏠 Ana Sayfa</a>

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

LİSTE
@app.route("/liste")
def liste():
with db() as con:
urunler = con.execute("SELECT * FROM urun").fetchall()

html = "<h2>STOK</h2>"
    for u in urunler:
        html += f"<div>{u[1]} - {u[8]}</div>"
    return html

html = "<h2 style='text-align:center;color:white'>STOK</h2>"

for u in urunler:
    html += f"""
    <div style="background:#eee;margin:10px;padding:10px;border-radius:10px">
    <b>{u[1]}</b><br>
    Stok: {u[8]}<br>
    <img src="/static/{u[10]}_qr.png" width="120"><br>
    <img src="/static/{u[10]}.png" width="250"><br>
    </div>
    """
return html

HAREKET
@app.route("/hareketler")
def hareketler():
with db() as con:
rows = con.execute("SELECT barkod, ad, tip, adet,kullanici tarih FROM hareket ORDER BY id DESC").fetchall()

  html = "<h2>Hareketler</h2>"
    for r in rows:
        html += f"<div>{r}</div>"
    return html

html = "<h2 style='text-align:center;color:white'>Hareketler</h2>"

for r in rows:
    renk = "green" if r[2]=="giris" else "red"
    html += f"<div style='color:white;background:#222;margin:5px;padding:10px;border-left:5px solid {renk}'>{r}</div>"
return html

HIZLI İŞLEM
@app.route("/hizli_islem", methods=["POST"])
def hizli_islem():
    data = request.get_json()
    barkod = data.get("barkod")
    tip = data.get("tip")
    kullanici = data.get("kullanici", "Kamera")

with db() as con:
    cur = con.cursor()
    cur.execute("SELECT id, ad, adet FROM urun WHERE barkod=?", (barkod,))
    row = cur.fetchone()

    if not row:
        return jsonify({"ok":False})

    uid, ad, adet = row

    if tip=="cikis" and adet <= 0:
            return jsonify({"ok":False, "msg":"Stok bitti"})

    if tip=="giris":
        adet+=1
    else:
        adet-=1
  
    if adet<0: adet=0

    cur.execute("UPDATE urun SET adet=? WHERE id=?", (adet,uid))
    
    cur.execute("""
    INSERT INTO hareket (barkod,ad,tip,adet,kullanici) 
    VALUES (?,?,?,?,?)"
    """,(barkod,ad,tip,adet,kullanici))
    
    con.commit()

return jsonify({"ok":True,"ad":ad,"adet":adet})

GERİ AL
@app.route("/geri_al", methods=["POST"])
def geri_al():
    data = request.get_json()
    barkod = data.get("barkod")
    tip = data.get("tip")

with db() as con:
    cur = con.cursor()
    cur.execute("SELECT id, adet FROM urun WHERE barkod=?", (barkod,))
    row = cur.fetchone()

    if not row:
        return jsonify({"ok":False})

    uid, adet = row

    if tip=="giris":
        adet-=1
    else:
        adet+=1

    if adet<0: adet=0

    cur.execute("UPDATE urun SET adet=? WHERE id=?", (adet,uid))
    con.commit()

return jsonify({"ok":True})

KAMERA
@app.route("/kamera/<tip>")
def kamera(tip):
    return render_template_string("""
<script src="https://unpkg.com/@zxing/library@latest"></script>
<body style="background:#000;color:white;text-align:center">
<h2>KAMERA</h2>
<video id="video" width="300"></video>
<h1 id="sonuc">Hazır</h1>

<input id="kullanici" placeholder="İşlem yapan">

<script>
const codeReader = new ZXing.BrowserMultiFormatReader();
let tip = "{{tip}}";

codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {
    if (result) {
        let kod = result.text;
        let kullanici = document.getElementById("kullanici").value;

        fetch("/hizli_islem", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body: JSON.stringify({barkod:kod, tip:tip, kullanici:kullanici})
        })
        .then(r=>r.json())
        .then(d=>{
            if(!d.ok){ alert("HATA"); return; }
            document.getElementById("sonuc").innerText = d.ad + " | " + d.adet;
        })
    }
});
</script>
""", tip=tip)

if name == "main":
app.run(debug=True)


