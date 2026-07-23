from flask import Flask, request, jsonify, send_file
import sqlite3
import os
from datetime import datetime
import barcode
from barcode.writer import ImageWriter
from reportlab.pdfgen import canvas

app = Flask(__name__)
DB = "stok.db"

# -----------------------------
# VERİTABANI
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        barcode TEXT,
        cins TEXT,
        ebat TEXT,
        mm TEXT,
        hg TEXT,
        yuzey TEXT,
        renk TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        depo INTEGER,
        adet INTEGER
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        action TEXT,
        product_id INTEGER,
        depo INTEGER,
        adet INTEGER,
        tarih TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# BARKOD OLUŞTUR
# -----------------------------
def generate_barcode(code):
    EAN = barcode.get_barcode_class('code128')
    ean = EAN(code, writer=ImageWriter())
    filename = f"barcodes/{code}"
    if not os.path.exists("barcodes"):
        os.makedirs("barcodes")
    ean.save(filename)
    return filename + ".png"

# -----------------------------
# ÜRÜN EKLE
# -----------------------------
@app.route("/add_product", methods=["POST"])
def add_product():
    data = request.json

    code = str(int(datetime.now().timestamp()))
    barcode_img = generate_barcode(code)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    INSERT INTO products (name, barcode, cins, ebat, mm, hg, yuzey, renk)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["name"], code,
        data.get("cins"),
        data.get("ebat"),
        data.get("mm"),
        data.get("hg"),
        data.get("yuzey"),
        data.get("renk")
    ))

    product_id = c.lastrowid

    conn.commit()
    conn.close()

    return jsonify({
        "product_id": product_id,
        "barcode": code,
        "barcode_img": barcode_img
    })

# -----------------------------
# STOK GİR (DEPO BAZLI)
# -----------------------------
@app.route("/add_stock", methods=["POST"])
def add_stock():
    data = request.json

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    INSERT INTO stock (product_id, depo, adet)
    VALUES (?, ?, ?)
    """, (data["product_id"], data["depo"], data["adet"]))

    # LOG
    c.execute("""
    INSERT INTO logs (user, action, product_id, depo, adet, tarih)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data.get("user", "admin"),
        "stok_ekle",
        data["product_id"],
        data["depo"],
        data["adet"],
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "ok"})

# -----------------------------
# BARKOD OKUT (DEPOCU TELEFON)
# -----------------------------
@app.route("/scan", methods=["POST"])
def scan():
    data = request.json

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT id FROM products WHERE barcode=?", (data["barcode"],))
    product = c.fetchone()

    if not product:
        return jsonify({"error": "ürün yok"})

    product_id = product[0]

    # stok düş
    c.execute("""
    UPDATE stock
    SET adet = adet - ?
    WHERE product_id=? AND depo=?
    """, (data["adet"], product_id, data["depo"]))

    # LOG
    c.execute("""
    INSERT INTO logs (user, action, product_id, depo, adet, tarih)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data.get("user", "depocu"),
        "stok_dus",
        product_id,
        data["depo"],
        data["adet"],
        datetime.now().strftime("%Y-%m-%d %H:%M")
    ))

    conn.commit()
    conn.close()

    return jsonify({"status": "stok düşüldü"})

# -----------------------------
# ETİKET PDF
# -----------------------------
@app.route("/label/<int:product_id>")
def label(product_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT name, barcode FROM products WHERE id=?", (product_id,))
    p = c.fetchone()

    conn.close()

    if not p:
        return "ürün yok"

    name, code = p
    barcode_path = f"barcodes/{code}.png"

    pdf_file = f"label_{product_id}.pdf"
    c = canvas.Canvas(pdf_file)

    c.drawString(100, 750, name)
    c.drawImage(barcode_path, 100, 600, width=300, height=100)

    c.save()

    return send_file(pdf_file, as_attachment=True)

# -----------------------------
# STOK GÖR (8 DEPO)
# -----------------------------
@app.route("/stock/<int:product_id>")
def stock(product_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    SELECT depo, SUM(adet)
    FROM stock
    WHERE product_id=?
    GROUP BY depo
    """, (product_id,))

    data = c.fetchall()
    conn.close()

    return jsonify(data)

# -----------------------------
# SERVER
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
