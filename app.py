from flask import Flask, render_template_string, request, redirect, send_from_directory
import sqlite3
import os
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)

DB = "stok.db"
BARCODE_FOLDER = "barcodes"

os.makedirs(BARCODE_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        barcode TEXT UNIQUE,
        stock INTEGER
    )
    """)
    conn.commit()
    conn.close()

def generate_barcode(code):
    path = os.path.join(BARCODE_FOLDER, code)
    ean = barcode.get('code128', code, writer=ImageWriter())
    ean.save(path)
    return f"/barcodes/{code}.png"

@app.route('/barcodes/<path:filename>')
def serve_barcode(filename):
    return send_from_directory(BARCODE_FOLDER, filename)

@app.route("/")
def index():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()

    html = """
    <h1>📦 HER-İŞ STOK</h1>

    <a href="/scan"><button>📷 Barkod Oku</button></a>

    <h2>Ürün Ekle</h2>
    <form method="POST" action="/add">
        <input name="name" placeholder="Ürün adı" required>
        <input name="barcode" placeholder="Barkod" required>
        <input name="stock" type="number" placeholder="Stok" required>
        <button type="submit">EKLE</button>
    </form>

    <h2>📋 Ürünler</h2>
    {% for p in products %}
        <div style="border:1px solid #ccc; padding:10px; margin:10px;">
            <b>{{p[1]}}</b><br>
            Barkod: {{p[2]}}<br>
            Stok: {{p[3]}}<br>
            <img src="/barcodes/{{p[2]}}.png" width="200"><br><br>

            <a href="/stock/{{p[2]}}/add">➕</a>
            <a href="/stock/{{p[2]}}/remove">➖</a>
        </div>
    {% endfor %}
    """
    return render_template_string(html, products=products)

@app.route("/add", methods=["POST"])
def add():
    name = request.form["name"]
    code = request.form["barcode"]
    stock = int(request.form["stock"])

    try:
        generate_barcode(code)

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO products (name, barcode, stock) VALUES (?, ?, ?)",
                  (name, code, stock))
        conn.commit()
        conn.close()
    except:
        pass

    return redirect("/")

@app.route("/stock/<code>/add")
def stock_add(code):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE products SET stock = stock + 1 WHERE barcode=?", (code,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/stock/<code>/remove")
def stock_remove(code):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE products SET stock = stock - 1 WHERE barcode=?", (code,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/scan")
def scan():
    html = """
    <h1>📷 Barkod Okut</h1>

    <video id="video" width="300" height="200" autoplay></video>
    <p id="result">Kod: -</p>

    <script src="https://unpkg.com/@zxing/library@latest"></script>

    <script>
    const codeReader = new ZXing.BrowserBarcodeReader()
    const videoElement = document.getElementById('video')

    codeReader.decodeFromVideoDevice(null, videoElement, (result, err) => {
        if (result) {
            let code = result.text
            document.getElementById('result').innerText = "Kod: " + code
            window.location.href = "/scan-result/" + code
        }
    })
    </script>
    """
    return html

@app.route("/scan-result/<code>")
def scan_result(code):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE products SET stock = stock - 1 WHERE barcode=?", (code,))
    conn.commit()
    conn.close()

    return f"<h2>{code} okutuldu ✔️ Stok düşürüldü</h2><a href='/'>Geri dön</a>"

app = Flask(__name__)

DB = "stok.db"
BARCODE_FOLDER = "barcodes"

os.makedirs(BARCODE_FOLDER, exist_ok=True)

init_db()   # 🔥 BURAYA EKLE
