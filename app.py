from flask import Flask, request, render_template_string
import json, os, datetime, uuid
import qrcode, base64
from io import BytesIO

app = Flask(__name__)

# ================= DOSYA =================
def oku(d):
    if not os.path.exists(d):
        with open(d,"w") as f: json.dump([], f)
    with open(d) as f:
        return json.load(f)

def yaz(d,v):
    with open(d,"w") as f:
        json.dump(v,f,indent=2)

# ================= SABİT DEPO =================
DEPOLAR = [
    "MDF SATIŞ DEPOSU","LAMİNANT DEPOSU","KAPI DEPOSU",
    "HGLOSS DEPOSU","MORAY YANI","SÜTÇÜ YANI",
    "HELVACI YANI","RÖTBALANSÇI YANI","KESİMHANE"
]

# ================= QR =================
def qr_olustur(veri):
    qr = qrcode.make(veri)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

# ================= LOG =================
def log_yaz(kim, islem, urun, adet, depo):
    log = oku("hareket.json")
    log.append({
        "kim": kim,
        "islem": islem,
        "urun": urun,
        "adet": adet,
        "depo": depo,
        "saat": str(datetime.datetime.now())
    })
    yaz("hareket.json", log)

# ================= ANA =================
@app.route("/")
def home():
    return """
    <h1>📦 DEPO SİSTEMİ</h1>
    <a href='/ekle'>➕ Ürün Ekle</a><br><br>
    <a href='/kamera'>📷 Kamera ile Okut</a><br><br>
    <a href='/okut'>⌨️ Manuel Okut</a><br><br>
    <a href='/hareket'>📋 Hareket</a>
    """

# ================= ÜRÜN EKLE =================
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method == "POST":
        f = request.form
        urunler = oku("urunler.json")

        barkod = str(uuid.uuid4())[:8]

        yeni = {
            "barkod": barkod,
            "ad": f["ad"],
            "cins": f["cins"],
            "ebat": f["ebat"],
            "sinif": f["sinif"],
            "renk": f["renk"],
            "adet": int(f["adet"]),
            "depo": f["depo"]
        }

        urunler.append(yeni)
        yaz("urunler.json", urunler)

        log_yaz("Yönetici","ÜRÜN EKLE",yeni["ad"],yeni["adet"],yeni["depo"])

        qr = qr_olustur(barkod)

        return f"""
        <h2>✅ Ürün Eklendi</h2>

        📦 {yeni['ad']}<br>
        Barkod: {barkod}<br><br>

        <img src="data:image/png;base64,{qr}"><br><br>

        <button onclick="window.print()">🖨️ Etiket Yazdır</button>

        <hr>
        <b>ETİKET</b><br>
        {yeni['ad']}<br>
        {yeni['cins']}<br>
        {yeni['ebat']}<br>
        {yeni['sinif']}<br>
        {yeni['renk']}<br>
        {yeni['depo']}<br>
        Barkod: {barkod}
        """

    return f"""
    <h2>Ürün Ekle</h2>
    <form method="post">
    Ad: <input name="ad"><br>
    Cins: <input name="cins"><br>
    Ebat: <input name="ebat"><br>
    Sınıf: <input name="sinif"><br>
    Renk: <input name="renk"><br>
    Adet: <input name="adet"><br>
    Depo:
    <select name="depo">
    {''.join([f"<option>{d}</option>" for d in DEPOLAR])}
    </select><br><br>
    <button>Kaydet</button>
    </form>
    """

# ================= MANUEL OKUT =================
@app.route("/okut", methods=["GET","POST"])
def okut():
    if request.method == "POST":
        barkod = request.form["barkod"]
        adet = int(request.form["adet"])
        kim = request.form["kim"]

        urunler = oku("urunler.json")

        for u in urunler:
            if u["barkod"] == barkod:

                if adet > u["adet"]:
                    return "❌ Yetersiz stok"

                u["adet"] -= adet
                yaz("urunler.json", urunler)

                log_yaz(kim,"MAL ÇIKIŞ",u["ad"],adet,u["depo"])

                return f"""
                <h2>✅ Çıkış</h2>
                📦 {u['ad']}<br>
                📏 {u['ebat']}<br>
                🎨 {u['renk']}<br>
                🏬 {u['depo']}<br>
                Kalan: {u['adet']}
                """

        return "❌ Ürün yok"

    return """
    <h2>Manuel Barkod</h2>
    <form method="post">
    Barkod: <input name="barkod"><br>
    Adet: <input name="adet"><br>
    Kim: <input name="kim"><br>
    <button>Onayla</button>
    </form>
    """

# ================= KAMERA =================
@app.route("/kamera")
def kamera():
    return """
    <h2>📷 Kamera ile Barkod Okut</h2>

    <video id="video" width="300" height="200" autoplay></video>
    <p id="sonuc"></p>

    <script src="https://unpkg.com/html5-qrcode"></script>

    <script>
    function start() {
        const scanner = new Html5Qrcode("video");

        scanner.start(
            { facingMode: "environment" },
            { fps: 10, qrbox: 250 },
            qrCodeMessage => {
                document.getElementById("sonuc").innerHTML =
                "Barkod: " + qrCodeMessage +
                "<br><a href='/okut?barkod="+qrCodeMessage+"'>ÇIKIŞ YAP</a>";
                scanner.stop();
            }
        );
    }
    start();
    </script>
    """

# ================= HAREKET =================
@app.route("/hareket")
def hareket():
    log = oku("hareket.json")
    h = "<h2>Hareket</h2>"
    for l in log[::-1]:
        h += f"<hr>{l['kim']} - {l['islem']} - {l['urun']} - {l['adet']} - {l['depo']} - {l['saat']}"
    return h

# ================= RUN =================
if __name__ == "__main__":
    app.run()
