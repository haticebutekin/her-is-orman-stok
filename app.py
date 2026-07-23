from flask import Flask, request, jsonify, render_template_string, send_file
import sqlite3
import cv2
from pyzbar.pyzbar import decode
from barcode import Code128
from barcode.writer import ImageWriter
from reportlab.pdfgen import canvas
import uuid
import os

app = Flask(__name__)

# -------------------- VERİTABANI --------------------
def init_db():
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS urunler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barkod TEXT UNIQUE,
        ad TEXT,
        cins TEXT,
        ebat TEXT,
        mm TEXT,
        kalite TEXT,
        renk TEXT,
        stok INTEGER
    )
    """)

    conn.commit()
    conn.close()

init_db()

# -------------------- ÜRÜN EKLE --------------------
def urun_ekle(data):
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()

    barkod = str(uuid.uuid4())[:12]

    c.execute("""
    INSERT INTO urunler (barkod, ad, cins, ebat, mm, kalite, renk, stok)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        barkod,
        data["ad"],
        data["cins"],
        data["ebat"],
        data["mm"],
        data["kalite"],
        data["renk"],
        1
    ))

    conn.commit()
    conn.close()

    return barkod

# -------------------- BARKOD OLUŞTUR --------------------
def barkod_olustur(kod):
    barcode = Code128(kod, writer=ImageWriter())
    filename = f"static/{kod}"
    barcode.save(filename)
    return filename + ".png"

# -------------------- ETİKET PDF --------------------
def etiket_olustur(urun):
    pdf_path = f"static/{urun['barkod']}.pdf"
    c = canvas.Canvas(pdf_path)

    c.drawString(50, 800, f"AD: {urun['ad']}")
    c.drawString(50, 780, f"CINS: {urun['cins']}")
    c.drawString(50, 760, f"EBAT: {urun['ebat']}")
    c.drawString(50, 740, f"MM: {urun['mm']}")
    c.drawString(50, 720, f"KALITE: {urun['kalite']}")
    c.drawString(50, 700, f"RENK: {urun['renk']}")
    c.drawString(50, 680, f"BARKOD: {urun['barkod']}")

    c.save()
    return pdf_path

# -------------------- ÜRÜN BUL --------------------
def urun_bul(barkod):
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()

    c.execute("SELECT * FROM urunler WHERE barkod=?", (barkod,))
    row = c.fetchone()

    conn.close()

    if row:
        return {
            "id": row[0],
            "barkod": row[1],
            "ad": row[2],
            "cins": row[3],
            "ebat": row[4],
            "mm": row[5],
            "kalite": row[6],
            "renk": row[7],
            "stok": row[8]
        }
    return None

# -------------------- STOK GÜNCELLE --------------------
def stok_arttir(barkod):
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()

    c.execute("UPDATE urunler SET stok = stok + 1 WHERE barkod=?", (barkod,))
    conn.commit()
    conn.close()

# -------------------- ANA SAYFA --------------------
@app.route("/")
def index():
    return render_template_string("""
    <h2>Barkod Okut</h2>
    <button onclick="baslat()">Kamera Aç</button>
    <p id="sonuc"></p>

    <script>
    function baslat(){
        fetch('/scan')
        .then(res=>res.json())
        .then(data=>{
            document.getElementById("sonuc").innerText = JSON.stringify(data)
        })
    }
    </script>
    """)

# -------------------- BARKOD OKUMA --------------------
@app.route("/scan")
def scan():
    cap = cv2.VideoCapture(0)

    while True:
        _, frame = cap.read()
        codes = decode(frame)

        for code in codes:
            barkod = code.data.decode("utf-8")
            cap.release()

            urun = urun_bul(barkod)

            if urun:
                stok_arttir(barkod)

                if urun["stok"] <= 1:
                    return jsonify({"UYARI": "STOK AZALDI!", "urun": urun})

                return jsonify({"OK": "Stok Güncellendi", "urun": urun})

            else:
                return jsonify({"HATA": "ÜRÜN YOK"})

# -------------------- YENİ ÜRÜN --------------------
@app.route("/yeni", methods=["POST"])
def yeni():
    data = request.json

    barkod = urun_ekle(data)
    barkod_olustur(barkod)

    urun = urun_bul(barkod)
    pdf = etiket_olustur(urun)

    return jsonify({
        "barkod": barkod,
        "etiket": pdf
    })

# -------------------- ETİKET İNDİR --------------------
@app.route("/etiket/<kod>")
def etiket(kod):
    path = f"static/{kod}.pdf"
    return send_file(path, as_attachment=True)

# --------------------
if __name__ == "__main__":
    app.run(debug=True)
