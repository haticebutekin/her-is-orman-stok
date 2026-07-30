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

# LİSTE
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
        Stok: {u[8]}<br>
        <img src="/static/{u[10]}_qr.png" width="120"><br>
        <img src="/static/{u[10]}.png" width="250"><br>
        </div>
        """

    return html

# HAREKETLER
@app.route("/hareketler")
def hareketler():
    with db() as con:
        rows = con.execute("SELECT barkod, ad, tip, adet, tarih FROM hareket ORDER BY id DESC").fetchall()

    html = """
    <div style="text-align:center">
    <a href="/" style="padding:10px;background:#00b894;color:white;border-radius:10px;text-decoration:none">🏠 Ana Sayfa</a>
    <h2>📊 Hareketler</h2>
    </div>
    """

    for r in rows:
        barkod, ad, tip, adet, tarih = r
        renk = "green" if tip=="giris" else "red"

        html += f"""
        <div style="background:#222;color:white;margin:5px;padding:10px;border-left:5px solid {renk}">
        {tarih} | {ad} | {tip} | {adet}
        </div>
        """

    return html

# HIZLI İŞLEM
@app.route("/hizli_islem", methods=["POST"])
def hizli_islem():
    try:
        data = request.get_json()
        barkod = str(data.get("barkod","")).strip()
        tip = data.get("tip","")

        with db() as con:
            cur = con.cursor()
            cur.execute("SELECT id, ad, adet FROM urun WHERE barkod=?", (barkod,))
            row = cur.fetchone()

            if not row:
                return jsonify({"ok":False,"mesaj":"ÜRÜN YOK"})

            uid, ad, adet = row

            if tip=="giris":
                adet+=1
            else:
                adet-=1

            if adet<0:
                adet=0

            cur.execute("UPDATE urun SET adet=? WHERE id=?", (adet,uid))
            cur.execute("INSERT INTO hareket (barkod,ad,tip,adet) VALUES (?,?,?,?)",(barkod,ad,tip,adet))
            con.commit()

        return jsonify({"ok":True,"ad":ad,"adet":adet})

    except Exception as e:
        print("HATA:", e)
        return jsonify({"ok":False})

@app.route("/geri_al", methods=["POST"])
def geri_al():
    data = request.get_json()
    barkod = data.get("barkod")
    tip = data.get("tip")

    with db() as con:
        cur = con.cursor()

        cur.execute("SELECT id, ad, adet FROM urun WHERE barkod=?", (barkod,))
        row = cur.fetchone()

        if not row:
            return jsonify({"ok":False})

        uid, ad, adet = row

        # ters işlem
        if tip == "giris":
            adet -= 1
        else:
            adet += 1

        if adet < 0:
            adet = 0

        cur.execute("UPDATE urun SET adet=? WHERE id=?", (adet, uid))
        con.commit()

    return jsonify({"ok":True})

# 🔥 OKUT API (YENİ)
@app.route("/okut", methods=["POST"])
def okut():
    try:
        data = request.get_json()
        barkod = data.get("barkod") if data else "123456789"

        return app.test_client().post("/hizli_islem", json={
            "barkod": barkod,
            "tip": "giris"
        }).get_json()

    except Exception as e:
        print("HATA:", e)
        return jsonify({"ok":False})
        
# KAMERA
@app.route("/kamera/<tip>")
def kamera(tip):
    return render_template_string("""
    <body style="background:#000;color:white;text-align:center;font-family:Arial">

    <a href="/" style="position:fixed;top:10px;left:10px;padding:10px;background:#00b894;color:white;border-radius:10px;text-decoration:none">🏠</a>

    <h2>Kamera Okuyucu ULTRA</h2>

    <div style="position:relative;display:inline-block">
        <video id="video" width="320" height="240"></video>

        <!-- 🎯 hedef alan -->
        <div id="hedef" style="
            position:absolute;
            top:50%; left:50%;
            width:160px; height:160px;
            transform:translate(-50%,-50%);
            border:4px solid #00ffcc;
            border-radius:15px;">
        </div>
    </div>

    <div id="sonuc" style="margin-top:20px;font-size:28px;font-weight:bold;">Hazır...</div>
    <button onclick="geriAl()" style="
    margin-top:10px;
    padding:10px;
    background:red;
    color:white;
    border:0;
    border-radius:10px">
    ⛔ SON OKUTMAYI GERİ AL
    </button>

    <img id="urunResim" width="120" style="margin-top:10px;display:none">

    <div id="sayac" style="margin-top:10px;color:#00ffcc"></div>

    <script src="https://unpkg.com/@zxing/library@latest"></script>

    <script>
    const codeReader = new ZXing.BrowserMultiFormatReader();

    let ses_ok = new Audio("https://actions.google.com/sounds/v1/cartoon/clang_and_wobble.ogg");
    let ses_cikis = new Audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg");
    let ses_hata = new Audio("https://actions.google.com/sounds/v1/cartoon/cartoon_boing.ogg");

    let sonKod = "";
    let sonZaman = 0;

    let sayac = {};

    function titre(){
        if(navigator.vibrate){
            navigator.vibrate(100);
        }
    }

    function sayacGuncelle(ad){
        if(!sayac[ad]){
            sayac[ad] = 1;
        } else {
            sayac[ad]++;
        }
        

        let html = "";
        for(let urun in sayac){
            html += urun + " : " + sayac[urun] + "<br>";
        }

        document.getElementById("sayac").innerHTML = html;
    }

    function kareIcindeMi(points){
        // barkod merkezini hesapla
        let x = 0, y = 0;
        points.forEach(p=>{
            x += p.x;
            y += p.y;
        });
        x /= points.length;
        y /= points.length;

        // hedef kare koordinat
        let hedef = document.getElementById("hedef").getBoundingClientRect();
        let video = document.getElementById("video").getBoundingClientRect();

        let sol = hedef.left - video.left;
        let sag = sol + hedef.width;
        let ust = hedef.top - video.top;
        let alt = ust + hedef.height;

        return (x > sol && x < sag && y > ust && y < alt);
    }

    codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {
        if (result) {

            let kod = result.text;
            sonKod = kod;
            console.log("SON KOD:", sonKod);
            let simdi = Date.now();

            // 🎯 sadece kare içindeyse
            if(!kareIcindeMi(result.resultPoints)) return;

            // ⚡ ultra cooldown (0.5 sn)
            if(kod === sonKod && (simdi - sonZaman) < 500){
                return;
            }

            sonKod = kod;
            sonZaman = simdi;

            gonder(kod);
        }
    });

    function geriAl(){
    fetch("/geri_al", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({
            barkod: sonKod,
            tip: "{{tip}}"
        })
    })
}

    function geriAl(){
    console.log("GERİ AL BASILDI", sonKod);

    fetch("/geri_al", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({
            barkod: sonKod,
            tip: "{{tip}}"
        })
    })
    .then(r => r.json())
    .then(d => console.log("SONUÇ:", d));
}

    function gonder(kod){
        fetch("/hizli_islem", {
            method: "POST",
            headers: {"Content-Type":"application/json"},
            body: JSON.stringify({
                barkod: kod,
                tip: "{{tip}}"
            })
        })
        .then(res => res.json())
        .then(data => {

            if(!data.ok){
                document.getElementById("sonuc").innerHTML =
                "<span style='color:red'>❌ ÜRÜN YOK</span>";
                ses_hata.play();
                titre();
            } else {

                document.getElementById("sonuc").innerHTML =
                "<span style='color:lightgreen;font-size:32px'>" + data.ad + "</span><br>Stok: " + data.adet;

                document.getElementById("urunResim").src = "/static/" + kod + "_qr.png";
                document.getElementById("urunResim").style.display = "block";

                sayacGuncelle(data.ad);

                if("{{tip}}" == "giris"){
                    ses_ok.play();
                } else {
                    ses_cikis.play();
                }

                titre();
            }

        });
    }
    </script>
    """)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
