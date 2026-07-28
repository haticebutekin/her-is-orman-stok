from flask import Flask, request, redirect, render_template_string
import sqlite3

app = Flask(__name__)

# DB
def get_db():
    return sqlite3.connect("db.sqlite", check_same_thread=False)

db = get_db()
cur = db.cursor()

# TABLO
cur.execute("""
CREATE TABLE IF NOT EXISTS urun(
id INTEGER PRIMARY KEY,
ad TEXT,
cins TEXT,
ebat TEXT,
kalinlik TEXT,
yuzey TEXT,
sinif TEXT,
renk TEXT,
adet INTEGER,
barkod TEXT UNIQUE
)
""")
db.commit()

# ANA SAYFA (MODERN)
@app.route("/")
def index():
    return """
    <style>
    body { font-family:Arial; background:#f5f6fa; text-align:center; }
    .box {
        background:white; padding:20px; margin:20px auto;
        width:300px; border-radius:15px;
        box-shadow:0 5px 20px rgba(0,0,0,0.1);
    }
    a {
        display:block; margin:10px;
        padding:12px; background:#4CAF50;
        color:white; text-decoration:none;
        border-radius:8px;
    }
    </style>

    <div class="box">
    <h2>📦 Depo Sistem</h2>
    <a href="/ekle">➕ Ürün Ekle</a>
    <a href="/kamera/giris">📥 Giriş</a>
    <a href="/kamera/cikis">📤 Çıkış</a>
    <a href="/liste">📋 Liste</a>
    </div>
    """

# ÜRÜN EKLE (DETAYLI)
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method == "POST":
        data = (
            request.form["ad"],
            request.form["cins"],
            request.form["ebat"],
            request.form["kalinlik"],
            request.form["yuzey"],
            request.form["sinif"],
            request.form["renk"],
            int(request.form["adet"]),
            request.form["barkod"]
        )

        try:
            cur.execute("""
            INSERT INTO urun
            (ad,cins,ebat,kalinlik,yuzey,sinif,renk,adet,barkod)
            VALUES (?,?,?,?,?,?,?,?,?)
            """, data)
            db.commit()
        except:
            return "Barkod zaten var!"

        return redirect("/")

    return """
    <style>
    body { font-family:Arial; background:#f5f6fa; }
    form {
        background:white; padding:20px;
        width:320px; margin:30px auto;
        border-radius:15px;
    }
    input, select {
        width:100%; padding:10px; margin:5px 0;
    }
    button {
        width:100%; padding:12px;
        background:#4CAF50; color:white;
        border:none; border-radius:8px;
    }
    </style>

    <form method="post">
    <h3>Ürün Ekle</h3>

    <input name="ad" placeholder="Ad">
    <input name="cins" placeholder="Cins">
    <input name="ebat" placeholder="Ebat">
    <input name="kalinlik" placeholder="Kalınlık">

    <select name="yuzey">
        <option>HG</option>
        <option>Mat</option>
    </select>

    <input name="sinif" placeholder="Sınıf">
    <input name="renk" placeholder="Renk">
    <input name="adet" type="number" placeholder="Adet">
    <input name="barkod" placeholder="Barkod">

    <button>Ekle</button>
    </form>
    """

# LİSTE
@app.route("/liste")
def liste():
    cur.execute("SELECT * FROM urun")
    data = cur.fetchall()

    html = """
    <style>
    body { font-family:Arial; background:#f5f6fa; }
    .card {
        background:white; margin:10px; padding:15px;
        border-radius:10px;
    }
    </style>
    <h2 style='text-align:center'>Ürünler</h2>
    """

    for u in data:
        html += f"""
        <div class="card">
        <b>{u[1]}</b><br>
        {u[2]} | {u[3]} | {u[4]}<br>
        {u[5]} | {u[6]} | {u[7]}<br>
        Adet: {u[8]}
        </div>
        """

    return html

# HIZLI İŞLEM
@app.route("/hizli_islem", methods=["POST"])
def hizli_islem():
    barkod = request.json.get("barkod")
    tip = request.json.get("tip")

    cur.execute("SELECT ad, adet FROM urun WHERE barkod=?", (barkod,))
    veri = cur.fetchone()

    if not veri:
        return {"ok": False}

    ad, adet = veri

    if tip == "cikis":
        if adet <= 0:
            return {"ok": False}
        adet -= 1
    else:
        adet += 1

    cur.execute("UPDATE urun SET adet=? WHERE barkod=?", (adet, barkod))
    db.commit()

    return {"ok": True, "ad": ad, "adet": adet}

# KAMERA
@app.route("/kamera/<tip>")
def kamera(tip):
    return render_template_string("""
    <style>
    body { font-family:Arial; text-align:center; }
    #isim { font-size:28px; margin:10px; }
    </style>

    <h2>📷 Okut</h2>
    <video id="video" width="300" autoplay></video>
    <div id="isim">Hazır</div>
    <div id="stok"></div>

    <script src="https://unpkg.com/@zxing/library@latest"></script>

    <script>
    const codeReader = new ZXing.BrowserBarcodeReader()
    let lock=false

    codeReader.decodeFromVideoDevice(null, 'video', async (result, err) => {
        if (result && !lock) {

            lock=true

            let res = await fetch("/hizli_islem", {
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body: JSON.stringify({
                    barkod: result.text,
                    tip: "{{tip}}"
                })
            })

            let data = await res.json()

            if (data.ok) {
                document.body.style.background="white"
                isim.innerText = data.ad
                stok.innerText = "Kalan: " + data.adet
            } else {
                document.body.style.background="red"
                isim.innerText = "HATALI ÜRÜN"
                stok.innerText = ""
            }

            setTimeout(()=>lock=false,500)
        }
    })
    </script>
    """, tip=tip)

if __name__ == "__main__":
    app.run(debug=True)
