import os
from flask import Flask, request, jsonify
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
BARCODE_DIR = os.path.join(STATIC_DIR, "barcodes")
QR_DIR = os.path.join(STATIC_DIR, "qrcodes")

# 🔥 KRİTİK FIX
# Eğer yanlışlıkla dosya varsa sil
if os.path.exists(BARCODE_DIR) and not os.path.isdir(BARCODE_DIR):
    os.remove(BARCODE_DIR)

if os.path.exists(QR_DIR) and not os.path.isdir(QR_DIR):
    os.remove(QR_DIR)

# klasörleri oluştur
os.makedirs(BARCODE_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)

app = Flask(__name__)

# 🔥 KESİN ÇÖZÜM (Render uyumlu path)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_DIR = os.path.join(BASE_DIR, "static")
BARCODE_DIR = os.path.join(STATIC_DIR, "barcodes")
QR_DIR = os.path.join(STATIC_DIR, "qrcodes")

# klasörleri zorla oluştur
os.makedirs(BARCODE_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)

# test route
@app.route("/")
def home():
    return "Sistem çalışıyor 🚀"

# örnek barkod üretme endpoint
@app.route("/urun-ekle", methods=["POST"])
def urun_ekle():
    data = request.json
    kod = data.get("kod", "123456")

    # sahte dosya oluştur (test için)
    barcode_path = os.path.join(BARCODE_DIR, f"{kod}.png")
    qr_path = os.path.join(QR_DIR, f"{kod}.png")

    with open(barcode_path, "w") as f:
        f.write("barcode")

    with open(qr_path, "w") as f:
        f.write("qr")

    return jsonify({
        "mesaj": "ürün eklendi",
        "barcode": barcode_path,
        "qr": qr_path
    })

if __name__ == "__main__":
    app.run()
