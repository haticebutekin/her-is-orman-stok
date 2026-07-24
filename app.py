from flask import Flask, request, session, redirect
import json, os, datetime, uuid
import qrcode, base64
from io import BytesIO

app = Flask(__name__)
app.secret_key = "gizli123"

# ================= DOSYA =================
def oku(d):
    if not os.path.exists(d):
        with open(d,"w") as f: json.dump([], f)
    with open(d) as f:
        return json.load(f)

def yaz(d,v):
    with open(d,"w") as f:
        json.dump(v,f,indent=2)

# ================= KULLANICI =================
KULLANICILAR = {
    "admin": {"sifre": "1234", "rol": "yonetici"},
    "depocu": {"sifre": "1234", "rol": "depocu"}
}

# ================= DEPO =================
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

# ================= LOGIN =================
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        k = request.form["kullanici"]
        s = request.form["sifre"]

        if k in KULLANICILAR and KULLANICILAR[k]["sifre"] == s:
            session["user"] = k
            session["rol"] = KULLANICILAR[k]["rol"]
            return redirect("/")

        return "❌ Hatalı giriş"

    return """
    <h2>🔐 Giriş</h2>
    <form method="post">
    Kullanıcı: <input name="kullanici"><br>
    Şifre: <input name="sifre" type="password"><br><br>
    <button>Giriş</button>
    </form>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ================= ANA =================
@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")

    menu = "<h1>📦 DEPO SİSTEMİ</h1>"

    if session["rol"] == "yonetici":
        menu += "<a href='/ekle'>➕ Ürün Ekle</a><br><br>"
        menu += "<a href='/stok'>📊 Stok</a><br><br>"

    menu += "<a href='/kamera'>📷 Kamera (Hızlı)</a><br><br>"
    menu += "<a href='/okut'>⌨️ Manuel</a><br><br>"
    menu += "<a href='/hareket'>📋 Hareket</a><br><br>"
    menu += "<a href='/logout'>🚪 Çıkış</a>"

    return menu

# ================= ÜRÜN EKLE =================
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if session.get("rol") != "yonetici":
        return "❌ Yetkisiz"

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

        log_yaz(session["user"],"ÜRÜN EKLE",yeni["ad"],yeni["adet"],yeni["depo"])

        qr = qr_olustur(barkod)

        return f"""
        <h2>✅ Ürün Eklendi</h2>
        📦 {yeni['ad']}<br>
        Barkod: {barkod}<br><br>

        <img src="data:image/png;base64,{qr}"><br><br>
        <button onclick="window.print()">🖨️ Yazdır</button>
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

# ================= STOK =================
@app.route("/stok")
def stok():
    if session.get("rol") != "yonetici":
        return "❌ Yetkisiz"

    urunler = oku("urunler.json")

    html = "<h2>📊 STOK</h2><table border=1>"
    html += "<tr><th>Ad</th><th>Depo</th><th>Adet</th></tr>"

    for u in urunler:
        renk = "red" if u["adet"] < 5 else "black"
        html += f"<tr style='color:{renk}'><td>{u['ad']}</td><td>{u['depo']}</td><td>{u['adet']}</td></tr>"

    html += "</table>"
    return html

# ================= MANUEL =================
@app.route("/okut", methods=["GET","POST"])
def okut():
    if request.method == "POST":
        barkod = request.form["barkod"]
        adet = int(request.form["adet"])

        urunler = oku("urunler.json")

        for u in urunler:
            if u["barkod"] == barkod:
                if adet > u["adet"]:
                    return "❌ Yetersiz stok"

                u["adet"] -= adet
                yaz("urunler.json", urunler)

                log_yaz(session["user"],"MAL ÇIKIŞ",u["ad"],adet,u["depo"])

                return f"✅ {u['ad']} → Kalan: {u['adet']}"

        return "❌ Ürün yok"

    return """
    <h2>Manuel</h2>
    <form method="post">
    Barkod: <input name="barkod"><br>
    Adet: <input name="adet"><br>
    <button>Onayla</button>
    </form>
    """

# ================= HIZLI KAMERA =================
@app.route("/kamera")
def kamera():
    return """
    <h2>📷 Hızlı Okutma</h2>
    <video id="reader" width="300"></video>
    <p id="durum"></p>

    <script src="https://unpkg.com/html5-qrcode"></script>
    <script>
    function baslat() {
        const html5QrCode = new Html5Qrcode("reader");

        html5QrCode.start(
            { facingMode: "environment" },
            { fps: 10, qrbox: 250 },
            (qr) => {
                document.getElementById("durum").innerHTML = "OKUNDU: " + qr;

                fetch("/hizli_cikis", {
                    method: "POST",
                    headers: {"Content-Type":"application/json"},
                    body: JSON.stringify({barkod: qr})
                })
                .then(r => r.text())
                .then(d => document.getElementById("durum").innerHTML = d)
            }
        );
    }
    baslat();
    </script>
    """

# ================= HIZLI ÇIKIŞ =================
@app.route("/hizli_cikis", methods=["POST"])
def hizli():
    data = request.get_json()
    barkod = data["barkod"]

    urunler = oku("urunler.json")

    for u in urunler:
        if u["barkod"] == barkod:

            if u["adet"] <= 0:
                return "❌ Stok yok"

            u["adet"] -= 1
            yaz("urunler.json", urunler)

            log_yaz(session.get("user","depocu"),"HIZLI ÇIKIŞ",u["ad"],1,u["depo"])

            return f"✅ {u['ad']} çıktı | Kalan: {u['adet']}"

    return "❌ Ürün bulunamadı"

# ================= HAREKET =================
@app.route("/hareket")
def hareket():
    log = oku("hareket.json")
    html = "<h2>📋 Hareket</h2>"

    for l in log[::-1]:
        html += f"<hr>{l['kim']} | {l['islem']} | {l['urun']} | {l['adet']} | {l['depo']} | {l['saat']}"

    return html

# ================= RUN =================
if __name__ == "__main__":
    app.run()
