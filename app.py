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
        kullanici TEXT,
        tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

# BARKOD
def barkod_uret():
    import random
    while True:
        kod = str(random.randint(100000000000,999999999999))

        with db() as con:
            var = con.execute(
                "SELECT barkod FROM urun WHERE barkod=?",
                (kod,)
            ).fetchone()

        if not var:
            return kod

def barkod_resim(kod):
    yol = os.path.join("static", kod)

    CODE128 = barcode.get_barcode_class("code128")

    img = CODE128(
        kod,
        writer=ImageWriter()
    )

    img.save(
        os.path.join("static", kod)
    )

def qr_uret(kod):
    img = qrcode.make(kod)
    img.save(os.path.join("static", kod+"_qr.png"))

# ANA
@app.route("/")
def index():
    return """
    <html>
    <head>
    <style>
    body {
        background: #111;
        font-family: Arial;
        text-align: center;
        color: white;
    }

    h1 {
        margin-top: 20px;
    }

    .btn {
        display: block;
        width: 80%;
        margin: 15px auto;
        padding: 20px;
        font-size: 22px;
        border-radius: 10px;
        text-decoration: none;
        color: white;
        font-weight: bold;
    }

    .mavi { background: linear-gradient(to right, #2196F3, #00BCD4); }
    .yesil { background: linear-gradient(to right, #00C853, #64DD17); }
    .turuncu { background: linear-gradient(to right, #FF6F00, #FF9800); }
    .mor { background: linear-gradient(to right, #5E35B1, #7E57C2); }
    .kirmizi { background: linear-gradient(to right, #D50000, #FF1744); }

    </style>
    </head>

    <body>

    <h1>📦 STOK PANEL</h1>

    <a href="/ekle" class="btn mavi">➕ ÜRÜN EKLE</a>
    <a href="/kamera/giris" class="btn yesil">⬆ GİRİŞ</a>
    <a href="/kamera/cikis" class="btn turuncu">📷 OKUT</a>
    <a href="/liste" class="btn mor">📦 STOK</a>
    <a href="/hareketler" class="btn kirmizi">📊 HAREKET</a>

    </body>
    </html>
    """

# EKLE
@app.route("/ekle", methods=["GET","POST"])
def ekle2():

    if request.method == "POST":

        barkod = request.form.get("barkod")

        if not barkod:
            barkod = barkod_uret()

        with db() as con:
            con.execute("""
            INSERT INTO urun(
            ad,cins,ebat,kalinlik,yuzey,sinif,renk,adet,depo,barkod
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

        return f"""
        <h2>✅ Ürün Kaydedildi</h2>

        <b>{request.form["ad"]}</b><br><br>

        📦 Barkod: {barkod}<br><br>

        <img src="/static/{barkod}.png" width="300"><br><br>

        <img src="/static/{barkod}_qr.png" width="150"><br><br>

        <a href="/liste">📦 Stok Listesine Git</a><br><br>

        <a href="/ekle">➕ Yeni Ürün Ekle</a>
        """

    return render_template_string("""
    
<form method="post">
<a href="/" style="
display:inline-block;
padding:10px 20px;
background:#2196F3;
color:white;
text-decoration:none;
border-radius:8px;
margin-bottom:10px;
">
Ana Sayfa
</a>

<h3>Ürün Bilgisi</h3>

<input name="barkod" placeholder="Boş bırak = otomatik barkod"><br><br>

<input name="ad" placeholder="Ürün Adı" required><br><br>

<input name="cins" placeholder="Cins"><br><br>

<input name="ebat" placeholder="Ebat"><br><br>

<input name="kalinlik" placeholder="Kalınlık"><br><br>

<label>Yüzey</label><br>

<select name="yuzey" required>
<option value="">Seçiniz</option>
<option value="HG">HG</option>
<option value="MAT">MAT</option>
</select><br><br>

<input name="sinif" placeholder="Sınıf"><br><br>

<input name="renk" placeholder="Renk"><br><br>

<input name="adet" type="number" placeholder="Adet" required><br><br>

<label>Depo</label><br>

<select name="depo">
{% for d in depolar %}
<option>{{d}}</option>
{% endfor %}
</select>

<br><br>

<button>Kaydet</button>

</form>
""", depolar=DEPOLAR)

# LİSTE
@app.route("/liste")
def liste():
    with db() as con:
        urunler = con.execute("SELECT * FROM urun").fetchall()

    html = "<h2>STOK</h2>"
    for u in urunler:
        html += f"""
<div style='border:1px solid gray; padding:10px; margin:10px'>
<b>{u[1]}</b><br>
Cins: {u[2]}<br>
Ebat: {u[3]}<br>
Kalınlık: {u[4]}<br>
Yüzey: {u[5]}<br>
Sınıf: {u[6]}<br>
Renk: {u[7]}<br>
Adet: {u[8]}<br>
Depo: {u[9]}<br>
Barkod: {u[10]}<br>
<img src="/static/{u[10]}.png" width="200"><br>
<img src="/static/{u[10]}_qr.png" width="100">
</div>
"""
    return html

# HAREKET
@app.route("/hareketler")
def hareketler():
    with db() as con:
        rows = con.execute("""
        SELECT barkod, ad, tip, adet, kullanici, tarih 
        FROM hareket ORDER BY id DESC
        """).fetchall()

    html = "<h2>Hareketler</h2>"
    for r in rows:
        html += f"{r}<br>"
    return html
    
@app.route("/kullanici_ozet/<kullanici>")
def kullanici_ozet(kullanici):
    with db() as con:
        rows = con.execute("""
        SELECT tip, SUM(adet) 
        FROM hareket 
        WHERE kullanici=? 
        GROUP BY tip
        """, (kullanici,)).fetchall()

    html = f"<h2>{kullanici} Özeti</h2>"

    for r in rows:
        html += f"{r[0]}: {r[1]} adet<br>"

    return html

# HIZLI İŞLEM
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
            return jsonify({"ok": False})

        uid, ad, adet = row

        # STOK KONTROL
        if tip == "cikis" and adet <= 0:
            return jsonify({"ok": False, "msg": "Stok yok"})

        if tip == "giris":
            adet += 1
        else:
            adet -= 1

        if adet < 0:
            adet = 0

        cur.execute("UPDATE urun SET adet=? WHERE id=?", (adet, uid))

        # HAREKET KAYIT
        cur.execute("""
        INSERT INTO hareket (barkod, ad, tip, adet, kullanici)
        VALUES (?, ?, ?, ?, ?)
        """, (barkod, ad, tip, 1, kullanici))

        # 👇 KULLANICI TOPLAMI (DOĞRU YER)
        toplam = cur.execute("""
        SELECT SUM(adet) FROM hareket
        WHERE kullanici=? AND tip='cikis'
        """, (kullanici,)).fetchone()[0]

        if not toplam:
            toplam = 0

        return jsonify({
            "ok": True,
            "ad": ad,
            "adet": adet,
            "toplam": toplam
        })
# GERİ AL
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

        if tip == "giris":
            adet -= 1
        else:
            adet += 1

        if adet < 0:
            adet = 0

        cur.execute("UPDATE urun SET adet=? WHERE id=?", (adet, uid))
        con.commit()

    return jsonify({"ok":True})

# KAMERA
@app.route("/kamera/<tip>")
def kamera(tip):

    return render_template_string("""
    <a href="/">Ana Sayfa</a>

    <h2>{{tip.upper()}} OKUT</h2>

    <button onclick="window.print()">Yazdır</button>

    <script src="https://unpkg.com/@zxing/library@latest"></script>

   <button onclick="baslat()">Kamerayı Başlat</button>

<video id="video" width="300" height="200"></video>
<h3 id="sonuc"></h3>

<script>
let bipSes;

function baslat(){

    // 🔊 SESİ KULLANICI TIKLAMASIYLA AKTİF ET
    bipSes = new Audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg");

    bipSes.play().then(() => {
        bipSes.pause();
        bipSes.currentTime = 0;
        console.log("Ses hazır");
    }).catch(e => console.log("Ses hatası:", e));

    // 📷 kamera
    codeReader = new ZXing.BrowserMultiFormatReader();

    codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {
        if (result) {
            okut(result);
        }
    });
}

function okut(result){

    let barkod = result.text;

    // 🔊 BİP
    bipSes.currentTime = 0;
    bipSes.play().catch(e => console.log("çalınamadı", e));

    document.getElementById("sonuc").innerHTML = "OK: " + barkod;
}
</script>

let bipSes;

function baslat(){
    bipSes = new Audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg");
    bipSes.load();
}

let codeReader;
let okundu = false;
let sonBarkod = "";

function baslat(){
    codeReader = new ZXing.BrowserMultiFormatReader();

    codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {

        if (result && !okundu) {

            let barkod = result.text;

            // ONAY SİSTEMİ
            if (sonBarkod != barkod) {
                sonBarkod = barkod;
                document.getElementById("sonuc").innerHTML =
                "Tekrar okut (onay): " + barkod;
                return;
            }

            okundu = true;

            let kullanici = document.getElementById("kullanici").value;

            if (!kullanici) {
                alert("Kullanıcı seç!");
                okundu = false;
                return;
            }

            fetch("/hizli_islem", {
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body: JSON.stringify({
                    barkod: barkod,
                    tip: "{{tip}}",
                    kullanici: kullanici
                })
            })
            .then(res => res.json())
            .then(data => {

                if(data.ok){
                    document.getElementById("sonuc").innerHTML =
                    "OK: " + data.ad +
                    "<br>Kalan stok: " + data.adet +
                    "<br>Toplam: " + data.toplam;
                }else{
                    document.getElementById("sonuc").innerHTML =
                    "Hata: " + (data.msg || "Urun yok");
                }

                setTimeout(function(){
                    okundu = false;
                }, 2000);

            });
        }
    });
}
</script>

    <script>
    let codeReader;
    let okundu = false;

    function baslat(){
        codeReader = new ZXing.BrowserMultiFormatReader();

        codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {

    if (result && !okundu) {

        let barkod = result.text;
        <script>
let sonBarkod = "";
let onaylandi = false;

function okut(result) {

    let barkod = result.text;

    if (sonBarkod != barkod) {
        sonBarkod = barkod;
        onaylandi = false;

        document.getElementById("sonuc").innerHTML =
        "Tekrar okut (onay): " + barkod;

        return;
    }

    if (!onaylandi) {
        onaylandi = true;

        fetch("/hizli_islem", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                barkod: barkod,
                tip: "cikis",
                kullanici: "Ali"
            })
        })
        .then(r => r.json())
        .then(d => {
            if (d.ok) {
                // 🔊 SES
                bip.currentTime = 0;
                bip.play().catch(e => console.log(e));

                document.getElementById("sonuc").innerHTML =
                "✅ Düşüldü: " + barkod;

            } else {
                document.getElementById("sonuc").innerHTML =
                "✅ Düşüldü: " + barkod;
            } else {
                document.getElementById("sonuc").innerHTML =
                "❌ Hata: " + (d.msg || "Bulunamadı");
            }
        });

        sonBarkod = "";
    }
}
</script>
        // ONAY SİSTEMİ
        if (sonBarkod != barkod) {
            sonBarko
            
            = barkod;
            document.getElementById("sonuc").innerHTML =
            "Tekrar okut (onay): " + barkod;
            return;
        }

        okundu = true;

        let kullanici = document.getElementById("kullanici").value;

        if (!kullanici) {
            alert("Kullanıcı gir!");
            okundu = false;
            return;
        }

        fetch("/hizli_islem", {
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body: JSON.stringify({
                barkod: barkod,
                tip: "{{tip}}",
                kullanici: kullanici
            })
        })
        .then(res => res.json())
        .then(data => {

            if(data.ok){
            
               new Audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg").play();
                
                document.getElementById("sonuc").innerHTML =
                "OK: " + data.ad +
                "<br>Kalan stok: " + data.adet +
                "<br>Toplam cikisin: " + data.toplam;
                "Hata: " + (data.msg || "Urun yok");
            }else{
                document.getElementById("sonuc").innerHTML =
                "Hata: " + (data.msg || "Urun yok");
            }

            setTimeout(function(){
                okundu = false;
            }, 2000);

        });
    }
});
    </script>
    """, tip=tip)


if __name__ == "__main__":
    app.run(debug=True)
