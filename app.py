from flask import Flask, request, redirect, render_template_string, send_file
import sqlite3, os, uuid
from datetime import datetime
import barcode
from barcode.writer import ImageWriter
from openpyxl import Workbook

DB = "veri.db"

app = Flask(__name__)

STATIC = "static"

# ---------------- DB ----------------
def db():
    return sqlite3.connect(DB)

def init_db():
    with db() as con:
        # ürünler
        con.execute("""
        CREATE TABLE IF NOT EXISTS urunler(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barkod TEXT,
            isim TEXT,
            adet INTEGER,
            fiyat REAL,
            tarih TEXT
        )
        """)

        # kullanıcılar
        con.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            password TEXT
        )
        """)

        # satışlar
        con.execute("""
        CREATE TABLE IF NOT EXISTS sales(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barkod TEXT,
            isim TEXT,
            adet INTEGER,
            toplam REAL,
            tarih TEXT
        )
        """)

        # default kullanıcı
        cur = con.execute("SELECT * FROM users")
        if not cur.fetchone():
            con.execute("INSERT INTO users VALUES (NULL,'admin','1234')")

# ✅ BURAYA ALINDI (EN KRİTİK DÜZELTME)
init_db()

# ---------------- BARKOD ----------------
def barkod_olustur():
    return str(uuid.uuid4())[:12]

def barkod_png(kod):
    os.makedirs(STATIC, exist_ok=True)
    EAN = barcode.get_barcode_class('code128')
    ean = EAN(kod, writer=ImageWriter())
    path = os.path.join(STATIC, kod)
    ean.save(path)

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["kullanici"]
        p = request.form["sifre"]

        with db() as con:
            user = con.execute(
                "SELECT * FROM users WHERE username=? AND password=?",
                (u,p)
            ).fetchone()

        if user:
            return redirect("/satis")

   return render_template_string("""
<style>
body{background:#0f172a;color:white;font-family:Arial}
input,button{padding:10px;width:100%;margin:5px}
.box{background:#1e293b;padding:10px;margin:5px}
video{width:100%;border-radius:10px}
</style>

<h2>🛒 KASA</h2>

<video id="camera" autoplay></video>

<form method="post" id="form">
<input name="barkod" id="barkod" placeholder="Barkod okut">
<button>Ekle</button>
</form>

<h3>Sepet</h3>

{% for v in sepet.values() %}
<div class="box">
{{v.isim}} - {{v.adet}} x {{v.fiyat}} ₺
</div>
{% endfor %}

<h2>💰 Toplam: {{toplam}} ₺</h2>

<a href="/fis"><button>🧾 Fiş</button></a>
<a href="/tamamla"><button>💳 Tamamla</button></a>

<script src="https://unpkg.com/html5-qrcode"></script>

<script>
const scanner = new Html5Qrcode("camera");

scanner.start(
    { facingMode: "environment" },
    {
        fps: 10,
        qrbox: 250
    },
    (decodedText) => {
        document.getElementById("barkod").value = decodedText;
        document.getElementById("form").submit();
    }
);
</script>
""", sepet=sepet, toplam=toplam)

# ---------------- ÜRÜN PANEL ----------------
@app.route("/panel", methods=["GET","POST"])
def panel():
    if request.method == "POST":
        kod = barkod_olustur()
        barkod_png(kod)

        with db() as con:
            con.execute("""
            INSERT INTO urunler (barkod,isim,adet,fiyat,tarih)
            VALUES (?,?,?,?,?)
            """,(
                kod,
                request.form["isim"],
                int(request.form["adet"]),
                float(request.form["fiyat"]),
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))

        return redirect("/panel")

    with db() as con:
        data = con.execute("SELECT * FROM urunler").fetchall()

    return render_template_string("""
    <style>
    body{background:#0f172a;color:white;font-family:Arial}
    input,button{padding:10px;margin:5px;width:100%}
    </style>

    <h2>📦 Ürün Panel</h2>

    <form method="post">
    <input name="isim" placeholder="İsim">
    <input name="adet" type="number" placeholder="Adet">
    <input name="fiyat" type="number" step="0.01" placeholder="Fiyat ₺">
    <button>EKLE</button>
    </form>

    <hr>

    {% for u in data %}
    <div>{{u[2]}} - {{u[3]}} adet - {{u[4]}} ₺</div>
    {% endfor %}

    <a href="/excel"><button>Excel</button></a>
    """ , data=data)

# ---------------- SEPET ----------------
sepet = {}

@app.route("/satis", methods=["GET","POST"])
def satis():
    global sepet

    if request.method == "POST":
        kod = request.form["barkod"]

        with db() as con:
            u = con.execute("SELECT * FROM urunler WHERE barkod=?", (kod,)).fetchone()

        if u:
            if kod in sepet:
                sepet[kod]["adet"] += 1
            else:
                sepet[kod] = {
                    "isim": u[2],
                    "fiyat": u[4],
                    "adet": 1
                }

    toplam = sum(v["fiyat"] * v["adet"] for v in sepet.values())

    return render_template_string("""
    <style>
    body{background:#0f172a;color:white;font-family:Arial}
    input,button{padding:10px;width:100%;margin:5px}
    .box{background:#1e293b;padding:10px;margin:5px}
    </style>

    <h2>🛒 KASA</h2>

    <form method="post">
    <input name="barkod" placeholder="Barkod okut">
    <button>Ekle</button>
    </form>

    <h3>Sepet</h3>

    {% for v in sepet.values() %}
    <div class="box">
    {{v.isim}} - {{v.adet}} x {{v.fiyat}} ₺
    </div>
    {% endfor %}

    <h2>💰 Toplam: {{toplam}} ₺</h2>

    <a href="/fis"><button>🧾 Fiş</button></a>
    <a href="/tamamla"><button>💳 Tamamla</button></a>
    """, sepet=sepet, toplam=toplam)

# ---------------- SATIŞ TAMAMLA ----------------
@app.route("/tamamla")
def tamamla():
    global sepet

    with db() as con:
        for kod,v in sepet.items():
            con.execute("UPDATE urunler SET adet=adet-? WHERE barkod=?",
                        (v["adet"],kod))

            con.execute("""
            INSERT INTO sales (barkod,isim,adet,toplam,tarih)
            VALUES (?,?,?,?,?)
            """,(
                kod,
                v["isim"],
                v["adet"],
                v["fiyat"]*v["adet"],
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))

    sepet = {}
    return redirect("/satis")

# ---------------- FİŞ ----------------
@app.route("/fis")
def fis():
    global sepet
    toplam = sum(v["fiyat"] * v["adet"] for v in sepet.values())

    html = "<body onload='window.print()'>"
    html += "<h2>🌲 HER İŞ ORMAN</h2><hr>"

    for v in sepet.values():
        html += f"{v['isim']} - {v['adet']} x {v['fiyat']} ₺<br>"

    html += f"<hr><h2>Toplam: {toplam} ₺</h2>"
    html += "</body>"

    return html

# ---------------- EXCEL ----------------
@app.route("/excel")
def excel():
    wb = Workbook()
    ws = wb.active
    ws.append(["İsim","Adet","Fiyat"])

    with db() as con:
        for u in con.execute("SELECT * FROM urunler"):
            ws.append([u[2],u[3],u[4]])

    file="stok.xlsx"
    wb.save(file)
    return send_file(file, as_attachment=True)

# ---------------- RUN ----------------

if __name__ == "__main__":
    init_db()
