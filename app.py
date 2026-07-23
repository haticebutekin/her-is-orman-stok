from flask import Flask, request, jsonify, render_template_string, send_file
import sqlite3, uuid, os
from barcode import Code128
from barcode.writer import ImageWriter
from reportlab.platypus import SimpleDocTemplate, Paragraph

app = Flask(__name__)

# ---------------- DB ----------------
conn = sqlite3.connect("stok.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS urun(
id INTEGER PRIMARY KEY,
ad TEXT,
cins TEXT,
ebat TEXT,
tip TEXT,
renk TEXT,
adet INTEGER,
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
def etiket_yap(u):
    path = f"static/{u['barkod']}.pdf"
    doc = SimpleDocTemplate(path)

    content = []
    content.append(Paragraph(f"ÜRÜN: {u['ad']}", None))
    content.append(Paragraph(f"CİNS: {u['cins']}", None))
    content.append(Paragraph(f"EBAT: {u['ebat']}", None))
    content.append(Paragraph(f"RENK: {u['renk']}", None))
    content.append(Paragraph(f"BARKOD: {u['barkod']}", None))

    doc.build(content)
    return path

# ---------------- ÜRÜN EKLE ----------------
@app.route("/urun_ekle", methods=["POST"])
def urun_ekle():
    d = request.json

    barkod = str(uuid.uuid4())[:12]

    c.execute("""
    INSERT INTO urun (ad,cins,ebat,tip,renk,adet,barkod,stok)
    VALUES (?,?,?,?,?,?,?,?)
    """, (
        d["ad"], d["cins"], d["ebat"], d["tip"],
        d["renk"], d["adet"], barkod, d["stok"]
    ))
    conn.commit()

    barkod_olustur(barkod)

    return jsonify({"ok":True, "barkod":barkod})

# ---------------- ETİKET ----------------
@app.route("/etiket/<kod>")
def etiket(kod):
    c.execute("SELECT * FROM urun WHERE barkod=?", (kod,))
    u = c.fetchone()

    urun = {
        "ad":u[1], "cins":u[2], "ebat":u[3],
        "tip":u[4], "renk":u[5], "adet":u[6],
        "barkod":u[7]
    }

    path = etiket_yap(urun)
    return send_file(path, as_attachment=True)

# ---------------- SCAN ----------------
@app.route("/scan/<kod>")
def scan(kod):

    c.execute("SELECT * FROM urun WHERE barkod=?", (kod,))
    u = c.fetchone()

    if not u:
        return jsonify({"hata":"YANLIŞ ÜRÜN"})

    stok = u[8] - 1

    c.execute("UPDATE urun SET stok=? WHERE barkod=?", (stok, kod))
    conn.commit()

    return jsonify({
        "urun": u[1],
        "stok": stok
    })

# ---------------- PANEL ----------------
@app.route("/")
def panel():
    return render_template_string("""

<h2>ÜRÜN EKLE</h2>

<input id="ad" placeholder="ad"><br>
<input id="cins" placeholder="cins"><br>
<input id="ebat" placeholder="ebat"><br>
<input id="tip" placeholder="mat/parlak"><br>
<input id="renk" placeholder="renk"><br>
<input id="adet" placeholder="adet"><br>
<input id="stok" placeholder="stok"><br>

<button onclick="ekle()">KAYDET</button>

<hr>

<h2>DEPO MODU</h2>
<div id="reader" style="width:300px"></div>

<script src="https://unpkg.com/html5-qrcode"></script>

<script>
function ekle(){
fetch("/urun_ekle",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({
ad:ad.value,
cins:cins.value,
ebat:ebat.value,
tip:tip.value,
renk:renk.value,
adet:parseInt(adet.value),
stok:parseInt(stok.value)
})
})
.then(r=>r.json())
.then(d=>{
alert("Barkod: "+d.barkod)
window.open("/etiket/"+d.barkod)
})
}

// SCAN
const scanner = new Html5Qrcode("reader")

scanner.start(
{ facingMode: "environment" },
{ fps: 10 },
(kod)=>{
fetch("/scan/"+kod)
.then(r=>r.json())
.then(d=>{
if(d.hata){
alert("YANLIŞ ÜRÜN ❌")
}else{
alert(d.urun + " stok: " + d.stok)
}
})
})
</script>

""")

app.run()
