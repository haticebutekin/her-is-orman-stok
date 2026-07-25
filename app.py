from flask import Flask, request, redirect, jsonify
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

# Barkod üret
def barkod_uret():
    return str(uuid.uuid4())[:10]

# ANA SAYFA
@app.route('/')
def index():
    db = get_db()
    urunler = db.execute("SELECT * FROM products").fetchall()

    html = "<h1>📦 Ürünler</h1>"
    html += '<a href="/ekle">Ürün Ekle</a> | <a href="/okut">Barkod Oku</a><hr>'

    for u in urunler:
        html += f"""
        <p>
        <b>{u[2]}</b><br>
        Adet: {u[3]}<br>
        Depo: {u[4]}<br>
        Barkod: {u[1]}<br>
        <img src="/static/barcodes/{u[1]}.png" width="200"><br>
        </p><hr>
        """
    return html

# ÜRÜN EKLE
@app.route('/ekle', methods=['GET','POST'])
def ekle():
    if request.method == 'POST':
        mal_adi = request.form['mal_adi']
        adet = int(request.form['adet'])
        depo = request.form['depo']

        barkod = barkod_uret()

        # barkod oluştur
        code = barcode.get('code128', barkod, writer=ImageWriter())
        code.save(f'static/barcodes/{barkod}')

        # qr oluştur
        img = qrcode.make(barkod)
        img.save(f"static/qrcodes/{barkod}.png")

        db = get_db()
        db.execute("INSERT INTO products (barkod, mal_adi, adet, depo) VALUES (?,?,?,?)",
                   (barkod, mal_adi, adet, depo))
        db.commit()

        return redirect('/')

    return '''
    <h1>Ürün Ekle</h1>
    <form method="POST">
    Mal Adı: <input name="mal_adi"><br>
    Adet: <input name="adet"><br>

    Depo:
    <select name="depo">
    <option>MDF SATIŞ DEPOSU</option>
    <option>LAMİNANT DEPOSU</option>
    <option>KAPI DEPOSU</option>
    <option>HGLOSS DEPOSU</option>
    </select>

    <br><br>
    <button>Kaydet</button>
    </form>
    '''

# BARKOD OKUT
@app.route('/okut')
def okut():
    return '''
    <h1>Barkod Oku</h1>

    <script src="https://unpkg.com/html5-qrcode"></script>

    <div id="reader"></div>

    <form method="POST" action="/stok-dus">
    Barkod: <input id="barkod" name="barkod"><br>
    Adet: <input name="adet"><br>
    <button>Çıkış Yap</button>
    </form>

    <script>
    function onScanSuccess(decodedText) {
        document.getElementById("barkod").value = decodedText;
    }

    new Html5QrcodeScanner("reader").render(onScanSuccess);
    </script>
    '''

# STOK DÜŞ
@app.route('/stok-dus', methods=['POST'])
def stok_dus():
    barkod = request.form['barkod']
    adet = int(request.form['adet'])

    db = get_db()
    urun = db.execute("SELECT adet FROM products WHERE barkod=?", (barkod,)).fetchone()

    if not urun:
        return "Ürün yok!"

    if urun[0] < adet:
        return "Yetersiz stok!"

    db.execute("UPDATE products SET adet = adet - ? WHERE barkod=?", (adet, barkod))
    db.execute("INSERT INTO movements (barkod, islem, adet) VALUES (?, 'CIKIS', ?)",
               (barkod, adet))
    db.commit()

    return redirect('/')

if __name__ == "__main__":
    app.run(debug=True)
