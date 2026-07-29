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

# HIZLI İŞLEM (FIX)
@app.route("/hizli_islem", methods=["POST"])
def hizli_islem():
    data = request.get_json()
    barkod = str(data.get("barkod")).strip()
    tip = data.get("tip")

    with db() as con:
        urun = con.execute("SELECT * FROM urun WHERE barkod=?", (barkod,)).fetchone()

        if not urun:
            return jsonify({"ok": False})

        adet = urun[8]

        if tip == "giris":
            adet += 1
        elif tip == "cikis":
            adet -= 1

        con.execute("UPDATE urun SET adet=? WHERE barkod=?", (adet, barkod))

    return jsonify({
        "ok": True,
        "ad": urun[1],
        "adet": adet
    })

# KAMERA (KESİN ÇALIŞAN)
@app.route("/kamera/<tip>")
def kamera(tip):

    return f"""
<button onclick="sesAc()">🔊 Sesi Aç</button>

<video id="video" width="300" height="200"></video>

<script src="https://unpkg.com/@zxing/library@latest"></script>

<script>
const codeReader = new ZXing.BrowserMultiFormatReader();

// 🔊 SES
let sesHazir = false;
const bip = new Audio("https://actions.google.com/sounds/v1/alarms/beep_short.ogg");

// 🔥 SESİ AKTİF ET (ŞART!)
function sesAc(){
    bip.play().then(()=>{
        bip.pause();
        bip.currentTime = 0;
        sesHazir = true;
    });
}
let sonOkuma = 0;

codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {
    if (result) {

        const simdi = Date.now();

        // 🔥 3 saniye bekleme
        if (simdi - sonOkuma < 3000) return;
        sonOkuma = simdi;

        console.log("OKUNAN:", result.text);

        // 🔊 SES ÇAL
        if (sesHazir) {
            bip.currentTime = 0;
            bip.play().catch(e => console.log(e));
        }

        // 📳 TİTREŞİM
        if (navigator.vibrate) {
            navigator.vibrate(150);
        }

        // 🔥 BACKEND
        fetch("/hizli_islem", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ barkod: result.text })
        });

    }
});
</script>

</body>
</html>
"""
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
