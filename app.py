from flask import Flask, request, jsonify, render_template_string, send_file
import sqlite3, uuid, os
from barcode import Code128
from barcode.writer import ImageWriter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

# ---------------- DB ----------------
conn = sqlite3.connect("stok.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS urun (
id INTEGER PRIMARY KEY,
ad TEXT,
barkod TEXT,
stok INTEGER
)
""")
conn.commit()

# ---------------- BARKOD ----------------
def barkod_olustur(kod):
    if not os.path.exists("static"):
        os.makedirs("static")
    Code128(kod, writer=ImageWriter()).save(f"static/{kod}")

# ---------------- ETİKET ----------------
def etiket_pdf(urun):
    path = f"static/{urun['barkod']}.pdf"
    doc = SimpleDocTemplate(path)
    styles = getSampleStyleSheet()

    content = []
    content.append(Paragraph(f"ÜRÜN: {urun['ad']}", styles["Normal"]))
    content.append(Paragraph(f"BARKOD: {urun['barkod']}", styles["Normal"]))
    content.append(Paragraph(f"STOK: {urun['stok']}", styles["Normal"]))

    doc.build(content)
    return path

# ---------------- AI EŞLEŞME ----------------
def urun_bul_ai(text):
    c.execute("SELECT * FROM urun")
    data = c.fetchall()

    en = None
    skor_max = 0

    for i in data:
        isim = i[1].lower()
        skor = sum(1 for k in text.lower().split() if k in isim)

        if skor > skor_max:
            skor_max = skor
            en = i

    return en

# ---------------- EKLE ----------------
@app.route("/ekle", methods=["POST"])
def ekle():
    isim = request.json["isim"]

    bulunan = urun_bul_ai(isim)

    if bulunan:
        c.execute("UPDATE urun SET stok=stok+1 WHERE id=?", (bulunan[0],))
        conn.commit()
        return jsonify({"ok":"stok arttı", "urun":bulunan[1]})

    barkod = str(uuid.uuid4())[:12]

    c.execute("INSERT INTO urun (ad,barkod,stok) VALUES (?,?,?)",
              (isim, barkod, 1))
    conn.commit()

    barkod_olustur(barkod)

    return jsonify({"ok":"yeni eklendi", "barkod":barkod})

# ---------------- SCAN ----------------
@app.route("/scan/<kod>")
def scan(kod):
    c.execute("SELECT * FROM urun WHERE barkod=?", (kod,))
    u = c.fetchone()

    if u:
        yeni = u[3] - 1
        c.execute("UPDATE urun SET stok=? WHERE barkod=?", (yeni, kod))
        conn.commit()

        if yeni <= 2:
            return jsonify({"uyari":"STOK AZ!", "urun":u[1]})

        return jsonify({"ok":"stok düştü", "urun":u[1]})

    return jsonify({"hata":"ürün yok"})

# ---------------- ETİKET ----------------
@app.route("/etiket/<kod>")
def etiket(kod):
    c.execute("SELECT * FROM urun WHERE barkod=?", (kod,))
    u = c.fetchone()

    urun = {"ad":u[1], "barkod":u[2], "stok":u[3]}
    path = etiket_pdf(urun)

    return send_file(path, as_attachment=True)

# ---------------- PANEL ----------------
@app.route("/")
def home():
    return render_template_string("""

<h2>STOK PRO MAX</h2>

<input id="isim" placeholder="ürün adı">
<button onclick="ekle()">EKLE</button>

<br><br>

<div id="reader" style="width:300px"></div>

<script src="https://unpkg.com/html5-qrcode"></script>

<script>
function ekle(){
fetch("/ekle",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({isim:document.getElementById("isim").value})
})
.then(r=>r.json())
.then(d=>alert(JSON.stringify(d)))
}

// KAMERA
const scanner = new Html5Qrcode("reader")

scanner.start(
{ facingMode: "environment" },
{ fps: 10 },
(kod)=>{

fetch("/scan/"+kod)
.then(r=>r.json())
.then(d=>{

if(d.uyari){
alert(d.uyari)
var audio = new Audio("https://www.soundjay.com/button/beep-07.wav")
audio.play()
}else{
alert("OK")
}

})
})
</script>

""")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
