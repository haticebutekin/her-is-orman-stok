from flask import Flask, request, redirect, session, render_template_string, send_file
import sqlite3, os, datetime
import qrcode
import barcode
from barcode.writer import ImageWriter
from openpyxl import Workbook

app = Flask(__name__)
app.secret_key = "pro123"

# ---------------- DB ----------------
def db():
    return sqlite3.connect("stok.db")

def init_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS urunler(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barkod TEXT,
            isim TEXT,
            cins TEXT,
            ebat TEXT,
            kalinlik TEXT,
            sinif TEXT,
            yuzey TEXT,
            renk TEXT,
            adet INTEGER,
            depo TEXT,
            tarih TEXT
        )
        """)
init_db()

# ---------------- BARKOD ----------------
def yeni_barkod():
    with db() as con:
        say = con.execute("SELECT COUNT(*) FROM urunler").fetchone()[0]
    return f"HER-{str(say+1).zfill(6)}"

def barkod_olustur(kod):
    os.makedirs("static", exist_ok=True)
    Code128 = barcode.get_barcode_class('code128')
    b = Code128(kod, writer=ImageWriter())
    return b.save(f"static/{kod}")

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["k"] == "admin" and request.form["s"] == "123":
            session["g"] = True
            return redirect("/panel")
    return render_template_string("""
    <style>
    body{font-family:Arial;background:#111;color:#fff;text-align:center}
    input,button{padding:10px;margin:5px}
    </style>
    <h1>HER İŞ ORMAN STOK PRO</h1>
    <form method="post">
    <input name="k" placeholder="Kullanıcı"><br>
    <input name="s" placeholder="Şifre" type="password"><br>
    <button>Giriş</button>
    </form>
    """)

# ---------------- PANEL ----------------
@app.route("/panel", methods=["GET","POST"])
def panel():
    if not session.get("g"): return redirect("/")
    
    if request.method == "POST":
        kod = yeni_barkod()
        barkod_olustur(kod)

        with db() as con:
            con.execute("""INSERT INTO urunler 
            (barkod,isim,cins,ebat,kalinlik,sinif,yuzey,renk,adet,depo,tarih)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (
                kod,
                request.form["isim"],
                request.form["cins"],
                request.form["ebat"],
                request.form["kalinlik"],
                request.form["sinif"],
                request.form["yuzey"],
                request.form["renk"],
                int(request.form["adet"]),
                request.form["depo"],
                str(datetime.datetime.now())
            ))

    with db() as con:
        urunler = con.execute("SELECT * FROM urunler ORDER BY id DESC").fetchall()

    return render_template_string("""
    <style>
    body{font-family:Arial;background:#0f172a;color:white}
    input,select{padding:8px;margin:3px}
    button{padding:10px;background:#22c55e;border:none;color:white}
    .card{background:#1e293b;padding:10px;margin:10px;border-radius:10px}
    a{color:#38bdf8}
    </style>

    <h2>STOK PANEL</h2>

    <form method="post">
    <input name="isim" placeholder="Mal adı">
    <input name="cins" placeholder="Cins">
    <input name="ebat" placeholder="Ebat">
    <input name="kalinlik" placeholder="Kalınlık">
    <input name="sinif" placeholder="Sınıf">
    <select name="yuzey">
        <option>HG</option><option>MAT</option><option>PARLAK</option>
    </select>
    <input name="renk" placeholder="Renk">
    <input name="adet" placeholder="Adet">
    <select name="depo">
        <option>MDF SATIŞ DEPOSU</option>
        <option>LAMİNANT DEPOSU</option>
        <option>KAPI DEPOSU</option>
        <option>HGLOSS DEPOSU</option>
        <option>SÜTÇÜ YANI</option>
        <option>HELVACI YANI</option>
        <option>RÖTBALANSÇI YANI</option>
        <option>KESİMHANE</option>
    </select>
    <button>EKLE</button>
    </form>

    <br>
    <a href="/kamera">📷 Kamera</a> |
    <a href="/excel">📊 Excel</a>

    {% for u in urunler %}
    <div class="card">
    <b>{{u[2]}}</b> ({{u[1]}})<br>
    {{u[3]}} | {{u[4]}}mm | {{u[5]}} | {{u[6]}} | {{u[7]}}<br>
    Adet: {{u[8]}} | {{u[9]}}<br>
    <a href="/sat/{{u[1]}}">SAT</a> |
    <img src="/static/{{u[1]}}.png" width="150">
    </div>
    {% endfor %}
    """, urunler=urunler)

# ---------------- SAT ----------------
@app.route("/sat/<kod>")
def sat(kod):
    with db() as con:
        con.execute("UPDATE urunler SET adet = adet - 1 WHERE barkod=?", (kod,))
    return redirect("/panel")

# ---------------- KAMERA ----------------
@app.route("/kamera")
def kamera():
    return render_template_string("""
    <script src="https://unpkg.com/html5-qrcode"></script>
    <h2>KAMERA OKUT</h2>
    <div id="reader" style="width:300px"></div>

    <script>
    function okundu(kod){
        new Audio("https://actions.google.com/sounds/v1/cartoon/beep.ogg").play();
        window.location = "/sat/" + kod;
    }

    new Html5Qrcode("reader").start(
        { facingMode: "environment" },
        { fps: 10, qrbox: 250 },
        okundu
    );
    </script>
    """)

# ---------------- EXCEL ----------------
@app.route("/excel")
def excel():
    wb = Workbook()
    ws = wb.active

    with db() as con:
        data = con.execute("SELECT * FROM urunler").fetchall()

    for i in data:
        ws.append(i)

    file = "rapor.xlsx"
    wb.save(file)
    return send_file(file, as_attachment=True)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
