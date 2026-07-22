from flask import Flask, render_template_string, request, redirect
import sqlite3
import os
import barcode
from barcode.writer import ImageWriter
from flask import send_from_directory

@app.route('/barcodes/<path:filename>')
def serve_barcode(filename):
    return send_from_directory(BARCODE_FOLDER, filename)

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
    return f"/{path}.png"

@app.route("/")
def index():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    products = c.fetchall()
    conn.close()

    html = """
    <h1>📦 HER-İŞ STOK</h1>

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

if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
