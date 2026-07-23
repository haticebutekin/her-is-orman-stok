from flask import Flask, request, jsonify, render_template_string
import sqlite3
import os
from datetime import datetime
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)
DB = "stok.db"

# ---------------- DB ----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        barcode TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        depo INTEGER,
        adet INTEGER
    )''')

    conn.commit()
    conn.close()

init_db()

# ---------------- HTML PANEL ----------------
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>STOK PANEL</title>
</head>
<body>

<h2>ÜRÜN EKLE</h2>
<form id="form">
İsim: <input name="name"><br>
<button type="submit">EKLE</button>
</form>

<h2>STOK EKLE</h2>
<form id="stokForm">
Ürün ID: <input name="product_id"><br>
Depo: <input name="depo"><br>
Adet: <input name="adet"><br>
<button type="submit">EKLE</button>
</form>

<h2>BARKOD OKUT</h2>
<div id="reader" style="width:300px"></div>

Depo: <input id="scanDepo"><br>
Adet: <input id="scanAdet" value="1"><br>

<button onclick="startScanner()">KAMERAYI AÇ</button>

<pre id="log"></pre>

<script src="https://unpkg.com/html5-qrcode"></script>

<script>
document.getElementById("form").onsubmit = async (e)=>{
e.preventDefault()
let data = Object.fromEntries(new FormData(e.target))

let res = await fetch("/add_product",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify(data)
})

let json = await res.json()
alert("BARKOD: " + json.barcode)
}

document.getElementById("stokForm").onsubmit = async (e)=>{
e.preventDefault()
let data = Object.fromEntries(new FormData(e.target))

await fetch("/add_stock",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify(data)
})

alert("stok eklendi")
}

function startScanner(){

const html5QrCode = new Html5Qrcode("reader");

html5QrCode.start(
{ facingMode: "environment" },
{ fps: 10, qrbox: 250 },

async (decodedText) => {

let depo = Number(document.getElementById("scanDepo").value)
let adet = Number(document.getElementById("scanAdet").value)

let res = await fetch("/scan",{
method:"POST",
headers:{"Content-Type":"application/json"},
body:JSON.stringify({
barcode: decodedText,
depo: depo,
adet: adet
})
})

let data = await res.json()

document.getElementById("log").innerText = JSON.stringify(data,null,2)

alert("OKUTULDU: " + decodedText)

html5QrCode.stop()

},
(err)=>{}
)
}
</script>

</body>
</html>
"""

# ---------------- ANA SAYFA ----------------
@app.route("/")
def panel():
    return render_template_string(HTML)

# ---------------- BARKOD ----------------
def generate_barcode(code):
    EAN = barcode.get_barcode_class('code128')
    ean = EAN(code, writer=ImageWriter())
    if not os.path.exists("barcodes"):
        os.makedirs("barcodes")
    ean.save(f"barcodes/{code}")

# ---------------- ÜRÜN EKLE ----------------
@app.route("/add_product", methods=["POST"])
def add_product():
    data = request.json
    code = str(int(datetime.now().timestamp()))

    generate_barcode(code)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("INSERT INTO products (name, barcode) VALUES (?, ?)",
              (data["name"], code))

    conn.commit()
    conn.close()

    return jsonify({"barcode": code})

# ---------------- STOK EKLE ----------------
@app.route("/add_stock", methods=["POST"])
def add_stock():
    data = request.json

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("INSERT INTO stock (product_id, depo, adet) VALUES (?, ?, ?)",
              (data["product_id"], data["depo"], data["adet"]))

    conn.commit()
    conn.close()

    return jsonify({"ok": True})

# ---------------- SCAN (HATA FIXLİ) ----------------
@app.route("/scan", methods=["POST"])
def scan():
    data = request.json

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT id, name FROM products WHERE barcode=?", (data["barcode"],))
    product = c.fetchone()

    if not product:
        return jsonify({"error": "ÜRÜN YOK"}), 404

    product_id, name = product

    c.execute("""
    UPDATE stock
    SET adet = adet - ?
    WHERE product_id=? AND depo=?
    """, (data["adet"], product_id, data["depo"]))

    conn.commit()
    conn.close()

    return jsonify({
        "ok": True,
        "urun": name,
        "dusen": data["adet"]
    })

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
