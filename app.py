from flask import Flask, request, redirect, render_template_string, jsonify
import sqlite3, os
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)

# SABİT DEPOLAR (DEĞİŞMEZ)
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
depo TEXT,
barkod TEXT UNIQUE
)
""")
db.commit()

# BARKOD ÜRET
def barkod_uret():
    cur.execute("SELECT COUNT(*) FROM urun")
    sayi = cur.fetchone()[0] + 1
    return f"URUN-{str(sayi).zfill(5)}"

# BARKOD RESİM
def barkod_resim_olustur(kod):
    if not os.path.exists("static"):
        os.makedirs("static")

    path = f"static/{kod}.png"

    # varsa tekrar üretme
    if os.path.exists(path):
        return path

    try:
        Code128 = barcode.get_barcode_class('code128')
        b = Code128(kod, writer=ImageWriter())
        b.save(f"static/{kod}")
        return path
    except Exception as e:
        print("BARKOD HATA:", e)
        return None

# ANA SAYFA
@app.route("/")
def index():
    return """
    <style>
    body { font-family:Arial; background:#f5f6fa; text-align:center; }
    .box { background:white; padding:20px; margin:20px auto; width:300px; border-radius:15px;}
    a { display:block; margin:10px; padding:12px; background:#4CAF50; color:white; text-decoration:none; border-radius:8px;}
    </style>
    <div class="box">
    <h2>📦 HER İŞ ORMAN STOK</h2>
    <a href="/ekle">➕ Ürün Ekle</a>
    <a href="/kamera/giris">📥 Giriş</a>
    <a href="/kamera/cikis">📤 Çıkış</a>
    <a href="/liste">📋 Liste</a>
    </div>
    """

# ÜRÜN EKLE
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method == "POST":

        barkod = request.form.get("barkod")
        if not barkod:
            barkod = barkod_uret()

        barkod_resim_olustur(barkod)

        data = (
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
        )

        try:
            cur.execute("""
            INSERT INTO urun
            (ad,cins,ebat,kalinlik,yuzey,sinif,renk,adet,depo,barkod)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """, data)
            db.commit()
        except:
            return "Barkod zaten var!"

        return redirect("/liste")

    return render_template_string("""
    <style>
    body { font-family:Arial; background:#f5f6fa; }
    form { background:white; padding:20px; width:320px; margin:30px auto; border-radius:15px;}
    input, select { width:100%; padding:10px; margin:5px 0;}
    button { width:100%; padding:12px; background:#4CAF50; color:white; border:none; border-radius:8px;}
    </style>

    <form method="post">
    <h3>Ürün Ekle</h3>

    <input name="ad" placeholder="Malın Adı">
    <input name="cins" placeholder="Malın Cinsi">
    <input name="ebat" placeholder="Ebat (mm)">
    <input name="kalinlik" placeholder="Kalınlık">

    <select name="yuzey">
        <option>HG</option>
        <option>Mat</option>
    </select>

    <input name="sinif" placeholder="Sınıf">
    <input name="renk" placeholder="Renk">
    <input name="adet" type="number" placeholder="Adet">

    <select name="depo">
        {% for d in depolar %}
        <option>{{d}}</option>
        {% endfor %}
    </select>

    <input name="barkod" placeholder="Barkod (boş bırak = otomatik)">
    <button>Ekle</button>
    </form>
    """, depolar=DEPOLAR)

# LİSTE
@app.route("/liste")
def liste():
    cur.execute("SELECT * FROM urun")
    data = cur.fetchall()

    html = """
    <style>
    body { font-family:Arial; background:#f5f6fa; }
    .card { background:white; margin:10px; padding:15px; border-radius:10px;}
    a { display:inline-block; margin-top:10px; background:#4CAF50; color:white; padding:6px 10px; border-radius:6px; text-decoration:none;}
    </style>
    <h2 style='text-align:center'>Ürünler</h2>
    """

    for u in data:
        html += f"""
        <div class="card">
        <b>{u[1]}</b><br>
        Depo: {u[9]}<br>
        {u[2]} | {u[3]} | {u[4]}<br>
        {u[5]} | {u[6]} | {u[7]}<br>
        Adet: {u[8]}<br>
        Barkod: {u[10]}<br>

        <a href="/etiket/{u[10]}" target="_blank">🖨 Etiket</a>
        <a href="/coklu/{u[10]}" target="_blank">📄 Çoklu Etiket</a>
        </div>
        """

    return html

# TEK ETİKET
@app.route("/etiket/<kod>")
def etiket(kod):

    # ÜRÜNÜ BUL
    cur.execute("SELECT * FROM urun WHERE barkod=?", (kod,))
    u = cur.fetchone()

    if not u:
        return "Ürün bulunamadı"

    # barkod yoksa üret
    path = barkod_resim_olustur(kod)

    return f"""
    <html>
    <head>
    <style>
    body {{ font-family:Arial; background:#f5f6fa; text-align:center; }}

    .etiket {{
        width:350px;
        background:white;
        padding:15px;
        margin:20px auto;
        border-radius:10px;
        border:2px solid black;
    }}

    .logo {{
        font-weight:bold;
        font-size:20px;
        margin-bottom:5px;
    }}

    .ad {{
        font-size:18px;
        font-weight:bold;
        margin-bottom:10px;
    }}

    .row {{
        text-align:left;
        font-size:14px;
    }}

    .badge {{
        padding:3px 8px;
        border-radius:6px;
        color:white;
        font-weight:bold;
    }}

    .hg {{ background:green; }}
    .mat {{ background:gray; }}
    </style>
    </head>

    <body>

    <div class="etiket">

        <div class="logo">HER İŞ ORMAN</div>

        <div class="ad">{u[1]}</div>

        <div class="row">Cinsi: {u[2]}</div>
        <div class="row">Ebat: {u[3]}</div>
        <div class="row">Kalınlık: {u[4]}</div>

        <div class="row">Sınıf: {u[6]}</div>
        <div class="row">Renk: {u[7]}</div>

        <div class="row">
        Yüzey:
        <span class="badge {'hg' if u[5]=='HG' else 'mat'}">
        {u[5]}
        </span>
        </div>

        <div class="row">Depo: {u[9]}</div>

        {"<img src='/" + path + "' width='300'>" if path else "<br><b>Barkod yok</b>"}

        <br><br>
        <button onclick="window.print()">🖨 Yazdır</button>

    </div>

    </body>
    </html>
    """

# ÇOKLU ETİKET (A4)
@app.route("/coklu/<kod>")
def coklu(kod):
    cur.execute("SELECT * FROM urun WHERE barkod=?", (kod,))
    u = cur.fetchone()

    if not u:
        return "Ürün yok"

    path = barkod_resim_olustur(kod)

    html = "<body style='font-family:Arial'>"

    for i in range(10):
        html += f"""
        <div style="width:45%;float:left;border:1px solid #ccc;margin:5px;padding:10px;border-radius:8px">
        
        <b>{u[1]}</b><br>

        {u[2]} | {u[3]} | {u[4]}<br>
        {u[6]} | {u[7]}<br>

        Yüzey: {u[5]}<br>
        Depo: {u[9]}<br>

        {"<img src='/" + path + "' width='200'>" if path else ""}

        </div>
        """

    html += "<div style='clear:both'></div><br>"
    html += "<button onclick='window.print()'>🖨 YAZDIR</button></body>"

    return html
# HIZLI İŞLEM
@app.route("/hizli_islem", methods=["POST"])
def hizli_islem():
    data = request.get_json()
    barkod = data.get("barkod")
    tip = data.get("tip")

    cur.execute("SELECT ad, adet FROM urun WHERE barkod=?", (barkod,))
    veri = cur.fetchone()

    if not veri:
        return jsonify({"ok": False})

    ad, adet = veri

    if tip == "cikis":
        if adet <= 0:
            return jsonify({"ok": False})
        adet -= 1
    else:
        adet += 1

    cur.execute("UPDATE urun SET adet=? WHERE barkod=?", (adet, barkod))
    db.commit()

    return jsonify({"ok": True, "ad": ad, "adet": adet})

# KAMERA
@app.route("/kamera/<tip>")
def kamera(tip):
    return render_template_string("""
    <video id="video" width="300" autoplay></video>
    <h2 id="isim">Hazır</h2>
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
                body: JSON.stringify({barkod: result.text, tip: "{{tip}}"})
            })

            let data = await res.json()

            if (data.ok){
                isim.innerText = data.ad
                stok.innerText = "Kalan: " + data.adet
            } else {
                isim.innerText = "HATALI"
            }

            setTimeout(()=>lock=false,500)
        }
    })
    </script>
    """, tip=tip)

if __name__ == "__main__":
    app.run(debug=True)
