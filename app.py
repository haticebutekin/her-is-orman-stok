from flask import Flask, render_template_string, request, jsonify
import re, uuid, sqlite3, os
from barcode import Code128
from barcode.writer import ImageWriter

app = Flask(__name__)

# 📦 DB
conn = sqlite3.connect("stok.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS stok (
id INTEGER PRIMARY KEY,
isim TEXT,
mm TEXT,
renk TEXT,
yuzey TEXT,
barkod TEXT,
adet INTEGER
)
""")
conn.commit()

# 🔍 ANALİZ
def analiz_et(metin):
    mm = re.search(r'(\d+)\s*mm', metin.lower())
    renkler = ["beyaz","siyah","gri","kırmızı","mavi"]
    yuzey = ["mat","parlak","hg"]

    return {
        "isim": metin,
        "mm": mm.group(1) if mm else "",
        "renk": next((r for r in renkler if r in metin.lower()), ""),
        "yuzey": next((y for y in yuzey if y in metin.lower()), "")
    }

# ➕ EKLE / ARTIR
@app.route("/ekle", methods=["POST"])
def ekle():
    veri = request.json
    analiz = analiz_et(veri["isim"])

    # aynı ürün var mı?
    c.execute("SELECT * FROM stok WHERE isim=?", (analiz["isim"],))
    urun = c.fetchone()

    if urun:
        c.execute("UPDATE stok SET adet = adet + 1 WHERE id=?", (urun[0],))
        conn.commit()
        barkod = urun[5]
    else:
        barkod = str(uuid.uuid4())[:12]
        c.execute("INSERT INTO stok (isim,mm,renk,yuzey,barkod,adet) VALUES (?,?,?,?,?,?)",
                  (analiz["isim"], analiz["mm"], analiz["renk"], analiz["yuzey"], barkod, 1))
        conn.commit()

        if not os.path.exists("static"):
            os.makedirs("static")

        Code128(barkod, writer=ImageWriter()).save(f"static/{barkod}")

    return jsonify({"ok": True, "barkod": barkod})

# 📦 STOK LİSTE
@app.route("/stok")
def stok():
    c.execute("SELECT * FROM stok")
    data = c.fetchall()

    sonuc = []
    for i in data:
        sonuc.append({
            "id": i[0],
            "isim": i[1],
            "mm": i[2],
            "renk": i[3],
            "yuzey": i[4],
            "barkod": i[5],
            "adet": i[6]
        })
    return jsonify(sonuc)

# ➖ AZALT (stok çıkışı)
@app.route("/dus/<kod>")
def dus(kod):
    c.execute("SELECT * FROM stok WHERE barkod=?", (kod,))
    urun = c.fetchone()

    if urun:
        yeni = urun[6] - 1
        c.execute("UPDATE stok SET adet=? WHERE barkod=?", (yeni, kod))
        conn.commit()

        return jsonify({"adet": yeni, "uyari": yeni <= 2})
    return jsonify({"hata":"yok"})

# 🔍 BUL
@app.route("/bul/<kod>")
def bul(kod):
    c.execute("SELECT * FROM stok WHERE barkod=?", (kod,))
    i = c.fetchone()
    if i:
        return jsonify({
            "isim": i[1],
            "adet": i[6]
        })
    return jsonify({"hata":"yok"})

# 🌐 ARAYÜZ
@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://unpkg.com/html5-qrcode"></script>
</head>

<body>

<h2>📦 Stok Sistemi</h2>

<input id="isim" placeholder="örn: 60mm beyaz mat PVC">
<button onclick="ekle()">Ekle</button>

<h3>📋 Stok</h3>
<ul id="liste"></ul>

<h3>📷 Barkod Okut</h3>
<div id="reader" style="width:300px"></div>

<script>
function ekle(){
fetch("/ekle",{
method:"POST",
headers:{"Content-Type":"application/json"},
body: JSON.stringify({isim:isim.value})
}).then(r=>r.json()).then(d=>{
alert("Barkod: "+d.barkod)
liste()
})
}

function liste(){
fetch("/stok").then(r=>r.json()).then(data=>{
let html=""
data.forEach(i=>{
html+=`
<li>
${i.isim} | Adet:${i.adet}
<br>
<img src="/static/${i.barkod}.png" width="120">
<button onclick="yazdir('${i.barkod}')">🖨</button>
</li><hr>`
})
liste.innerHTML=html
})
}

function yazdir(kod){
let w=window.open("")
w.document.write(`<img src="/static/${kod}.png">`)
w.print()
}

function barkod(){
const scanner = new Html5Qrcode("reader")
scanner.start(
{ facingMode:"environment"},
{ fps:15 },
(kod)=>{
fetch("/dus/"+kod)
.then(r=>r.json())
.then(d=>{
if(d.uyari){
alert("⚠️ STOK AZALDI!")
}else{
alert("OK. Kalan: "+d.adet)
}
liste()
})
})
}

liste()
barkod()
</script>

</body>
</html>
""")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
