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
@app.route("/barkod_cikis/<kod>")
def barkod_cikis(kod):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT id, isim, adet FROM urun WHERE barkod=?", (kod,))
    urun = c.fetchone()

    if urun:
        yeni_adet = urun[2] - 1

        c.execute("UPDATE urun SET adet=? WHERE id=?", (yeni_adet, urun[0]))
        conn.commit()
        conn.close()

        return f"""
        <h2>📤 ÇIKIŞ YAPILDI</h2>
        <p><b>Ürün:</b> {urun[1]}</p>
        <p><b>Çıkan:</b> 1 adet</p>
        <p><b>Kalan:</b> {yeni_adet}</p>
        <a href="/kamera">🔙 Geri</a>
        """

    else:
        conn.close()
        return "❌ Ürün bulunamadı"
    
@app.route("/barkod_ekle/<kod>", methods=["GET","POST"])
def barkod_ekle(kod):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT id, adet FROM urun WHERE barkod=?", (kod,))
    urun = c.fetchone()

    if urun:
        # Ürün varsa stok artır
        c.execute("UPDATE urun SET adet = adet + 1 WHERE id=?", (urun[0],))
        conn.commit()
        conn.close()
        return f"✅ Stok arttı: {kod}"
        
    # Ürün yoksa → form göster
    if request.method == "POST":
        isim = request.form.get("isim")

        c.execute("INSERT INTO urun (barkod, isim, adet) VALUES (?, ?, ?)",
                  (kod, isim, 1))
        conn.commit()
        conn.close()

        return f"✅ {isim} eklendi"

    conn.close()

    return f"""
    <h2>Yeni Ürün Ekle</h2>
    <p>Barkod: {kod}</p>

   <form method="POST">
        <input type="text" name="isim" placeholder="Ürün adı">
        <button type="submit">Kaydet</button>
    </form>
    """
       
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
        <button onclick="baslat()">Kamerayı Başlat</button>
        <button onclick="location.reload()">🏠 Ana Sayfa</button>

        <br><br>

        <select id="kullanici">
        <option>Ramazan</option>
        <option>Orhan</option>
        <option>Behiç</option>
        <option>İrem</option>
        <option>Berke</option>
        <option>Hatice</option>
        <option>Ahmet</option>
        </select>

        <br><br>

        <video id="video" width="300" height="200"></video>

        <h3 id="sonuc"></h3>
        <script src="https://unpkg.com/@zxing/library@latest"></script>
                
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

    <a href="/" style="
    position:fixed;
    top:10px;
    left:10px;
    padding:10px 15px;
    background:#2196F3;
    color:white;
    text-decoration:none;
    border-radius:8px;
    font-weight:bold;
    z-index:9999;
    ">
    🏠 Ana Sayfa
    </a>

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
    
        <br><br>
        <a href="/" style="
        display:inline-block;
        padding:10px 20px;
        background:#00C853;
        color:white;
        text-decoration:none;
        border-radius:8px;
        font-weight:bold;
        ">
        🏠 Ana Sayfaya Dön
        </a>
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
@app.route("/urun_ekle", methods=["GET","POST"])
def urun_ekle():
    barkod = request.args.get("barkod","")

    if request.method == "POST":
        veri = (
            request.form["barkod"],
            request.form["isim"],
            request.form["cins"],
            request.form["ebat"],
            request.form["kalinlik"],
            request.form["sinif"],
            request.form["yuzey"],
            request.form["renk"],
            request.form["adet"],
            request.form["depo"]
        )

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("""
        INSERT INTO urunler 
        (barkod, isim, cins, ebat, kalinlik, sinif, yuzey, renk, adet, depo)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """, veri)
        conn.commit()
        conn.close()

        return redirect("/panel")

    return f"""
    <form method="post">
        Barkod: <input name="barkod" value="{barkod}"><br>
        İsim: <input name="isim"><br>
        Cinsi: <input name="cins"><br>
        Ebat: <input name="ebat"><br>
        Kalınlık: <input name="kalinlik"><br>
        Sınıf: <input name="sinif"><br>

        Yüzey:
        <select name="yuzey">
            <option>HG</option>
            <option>MAT</option>
            <option>PARLAK</option>
        </select><br>

        Renk: <input name="renk"><br>
        Adet: <input name="adet" value="1"><br>

        Depo:
        <select name="depo">
            <option>MDF SATIŞ DEPOSU</option>
            <option>LAMİNANT DEPOSU</option>
            <option>KAPI DEPOSU</option>
            <option>HGLOSS DEPOSU (MORAY YANI)</option>
            <option>SÜTÇÜ YANI</option>
            <option>HELVACI YANI</option>
            <option>RÖTBALANSÇI YANI</option>
            <option>KESİMHANE</option>
        </select><br>

        <button>Kaydet</button>
    </form>
    """
@app.route("/kamera_giris")
def kamera_giris():
    return """
    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <video id="video"></video>

    <script>
    const codeReader = new ZXing.BrowserMultiFormatReader();

    codeReader.decodeFromVideoDevice(null, document.getElementById('video'), (result, err) => {
        if (result) {
            window.location.href = "/barkod_ekle/" + result.text;
        }
    });
    </script>
    """

@app.route("/kamera_cikis")
def kamera_cikis():
    return """
    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <video id="video"></video>

    <script>
    const codeReader = new ZXing.BrowserMultiFormatReader();

    codeReader.decodeFromVideoDevice(null, document.getElementById('video'), (result, err) => {
        if (result) {
            window.location.href = "/barkod_cikis/" + result.text;
        }
    });
    </script>
    """
# KAMERA
@app.route("/kamera/<tip>")
def kamera(tip):

    return render_template_string("""
    <a href="/">Ana Sayfa</a>

<h2>{{tip.upper()}} OKUT</h2>

<button onclick="baslat()">Kamerayı Başlat</button>

<br><br>

<select id="kullanici">
<option>Ramazan</option>
<option>Orhan</option>
<option>Behiç</option>
<option>İrem</option>
<option>Berke</option>
<option>Hatice</option>
<option>Ahmet</option>
</select>

<br><br>

<video id="video" width="300" height="200"></video>

<h3 id="sonuc"></h3>

<script src="https://unpkg.com/@zxing/library@latest"></script>

<script>

let codeReader;
let kilit = false;
let bipSes;
let sonBarkod = "";
let onay = false;

function baslat(){

    bipSes = new Audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg");

    codeReader = new ZXing.BrowserMultiFormatReader();

    codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {

        if (result && !kilit) {

            kilit = true;

            let barkod = result.text;
            let kullanici = document.getElementById("kullanici").value;
           
            
            // 🔊 bip sesi
            bipSes.currentTime = 0;
            bipSes.play().catch(e => console.log(e));

            fetch("/hizli_islem", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    barkod: barkod,
                    tip: "{{tip}}",
                    kullanici: kullanici
                })
            })
            .then(r => r.json())
            .then(d => {

                if (d.ok) {
                    document.body.style.background = "green";
                    document.getElementById("sonuc").innerHTML =
    "✅ Barkod: " + barkod + "<br>" +
    "📦 Ürün: " + d.ad + "<br>" +
    "📦 Kalan: " + d.adet + "<br>" +
    "📊 Senin Toplam Çıkışın: " + d.toplam + "<br>" +
    "👤 Kullanıcı: " + kullanici;
                } else {
                    document.body.style.background = "red";
                    document.getElementById("sonuc").innerHTML =
                        "❌ Hata: " + (d.msg || "Bulunamadı");
                }

                setTimeout(() => {
                    kilit = false;
                }, 2000);

            });
        }

        if (err && !(err instanceof ZXing.NotFoundException)) {
            console.log(err);
        }

    });
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
                onay = false;

                document.getElementById("sonuc").innerHTML =
                "Tekrar okut (onay): " + barkod;
                kilit = false;
                return;
            }
            if (!onay) {
                onay = true;
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
