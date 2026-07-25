from flask import Flask, render_template, request, redirect, jsonify
import sqlite3
import uuid
import os
import barcode
from barcode.writer import ImageWriter
import qrcode

app = Flask(__name__)

# klasörler
os.makedirs("static/barcodes", exist_ok=True)
os.makedirs("static/qrcodes", exist_ok=True)

# DB
def get_db():
    return sqlite3.connect("database.db")

# DB oluştur
def init_db():
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY,
        barkod TEXT,
        mal_adi TEXT,
        adet INTEGER,
        depo TEXT
    )''')

    db.execute('''CREATE TABLE IF NOT EXISTS movements (
        id INTEGER PRIMARY KEY,
        barkod TEXT,
        islem TEXT,
        adet INTEGER,
        tarih DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    db.commit()

init_db()

# Ana sayfa
@app.route('/')
def index():
    db = get_db()
    urunler = db.execute("SELECT * FROM products").fetchall()
    return render_template("index.html", urunler=urunler)

# Barkod üret
def barkod_uret():
    return str(uuid.uuid4())[:10]

# Ürün ekle
@app.route('/ekle', methods=['GET','POST'])
def ekle():
    if request.method == 'POST':
        mal_adi = request.form['mal_adi']
        adet = int(request.form['adet'])
        depo = request.form['depo']

        barkod = barkod_uret()

        # barkod
        code = barcode.get('code128', barkod, writer=ImageWriter())
        code.save(f'static/barcodes/{barkod}')

        # qr
        img = qrcode.make(barkod)
        img.save(f"static/qrcodes/{barkod}.png")

        db = get_db()
        db.execute("INSERT INTO products (barkod, mal_adi, adet, depo) VALUES (?,?,?,?)",
                   (barkod, mal_adi, adet, depo))

        db.commit()

        return redirect('/')

    return render_template("ekle.html")

# Barkod okutma ekranı
@app.route('/okut')
def okut():
    return render_template("okut.html")

# Barkod bul
@app.route('/barkod/<kod>')
def barkod_bul(kod):
    db = get_db()
    urun = db.execute("SELECT * FROM products WHERE barkod=?", (kod,)).fetchone()

    if urun:
        return jsonify({
            "barkod": urun[1],
            "mal_adi": urun[2],
            "adet": urun[3],
            "depo": urun[4]
        })
    else:
        return jsonify({"hata": "Ürün bulunamadı"})

# Stok düş
@app.route('/stok-dus', methods=['POST'])
def stok_dus():
    barkod = request.form['barkod']
    adet = int(request.form['adet'])

    db = get_db()
    urun = db.execute("SELECT adet FROM products WHERE barkod=?", (barkod,)).fetchone()

    if urun[0] < adet:
        return "Yetersiz stok!"

    db.execute("UPDATE products SET adet = adet - ? WHERE barkod=?", (adet, barkod))
    db.execute("INSERT INTO movements (barkod, islem, adet) VALUES (?, 'CIKIS', ?)",
               (barkod, adet))

    db.commit()

    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)
