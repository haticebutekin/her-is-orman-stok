from flask import Flask, render_template_string, request, redirect, send_from_directory
import sqlite3
import os

app = Flask(__name__)

DB = "stok.db"
BARCODE_FOLDER = "barcodes"

os.makedirs(BARCODE_FOLDER, exist_ok=True)

# ✅ SADECE 1 KEZ ÇALIŞIR
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

# 🔥 BURASI KRİTİK (IMPORT OLURKEN ÇALIŞIR)
init_db()

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

    return render_template_string("""
    <h1>📦 STOK</h1>

    <a href="/scan"><button>📷 Barkod Oku</button></a>

    <h2>Ürün Ekle</h2>
    <form method="POST" action="/add">
        <input name="name" placeholder="Ürün adı" required>
        <input name="barcode" placeholder="Barkod" required>
        <input name="stock" type="number" required>
        <button type="submit">EKLE</button>
    </form>

    <h2>Ürünler</h2>
    {% for p in products %}
        <div style="border:1px solid #ccc; margin:10px; padding:10px;">
            <b>{{p[1]}}</b><br>
            Kod: {{p[2]}}<br>
            Stok: {{p[3]}}<br>
            <a href="/stock/{{p[2]}}/add">➕</a>
            <a href="/stock/{{p[2]}}/remove">➖</a>
        </div>
    {% endfor %}
    """, products=products)

@app.route("/add", methods=["POST"])
def add():
    name = request.form["name"]
    code = request.form["barcode"]
    stock = int(request.form["stock"])

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO products (name, barcode, stock) VALUES (?, ?, ?)",
              (name, code, stock))
    conn.commit()
    conn.close()

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
    return """
    <h2>📷 Barkod Oku</h2>
    <video id="video" width="300" autoplay></video>

    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <script>
    const codeReader = new ZXing.BrowserBarcodeReader()
    codeReader.decodeFromVideoDevice(null, 'video', (result, err) => {
        if (result) {
            window.location.href = "/scan-result/" + result.text
        }
    })
    </script>
    """

@app.route("/scan-result/<code>")
def scan_result(code):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("UPDATE products SET stock = stock - 1 WHERE barcode=?", (code,))
    conn.commit()
    conn.close()

    return f"{code} okutuldu ✔️ <a href='/'>Geri</a>"
