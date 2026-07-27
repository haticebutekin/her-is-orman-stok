from flask import Flask, request, redirect, send_file, render_template_string
import sqlite3, os, uuid
from datetime import datetime
import barcode
from barcode.writer import ImageWriter
from openpyxl import Workbook

app = Flask(__name__)

DB = "veri.db"
STATIC = "static"

# --- DB ---
def db():
    return sqlite3.connect(DB)

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

# --- BARKOD ---
def barkod_olustur():
    return str(uuid.uuid4())[:12]

def barkod_png(kod):
    os.makedirs(STATIC, exist_ok=True)
    EAN = barcode.get_barcode_class('code128')
    ean = EAN(kod, writer=ImageWriter())
    yol = os.path.join(STATIC, f"{kod}")
    ean.save(yol)
    return f"/static/{kod}.png"

# --- LOGIN ---
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["kullanici"]=="admin" and request.form["sifre"]=="1234":
            return redirect("/panel")
    return """
    <style>
    body{background:#0f172a;color:white;font-family:Arial;text-align:center}
    input{padding:12px;margin:8px;border-radius:8px;border:none;width:220px}
    button{padding:12px 24px;border:none;border-radius:10px;background:#22c55e;color:white;font-size:16px}
    .card{margin-top:120px}
    </style>
    <div class='card'>
    <h2>🌲 HER İŞ ORMAN</h2>
    <form method='post'>
    <input name='kullanici' placeholder='Kullanıcı'><br>
    <input name='sifre' type='password' placeholder='Şifre'><br>
    <button>GİRİŞ</button>
    </form>
    </div>
    """

# --- PANEL ---
@app.route("/panel", methods=["GET","POST"])
def panel():
    if request.method == "POST":
        kod = barkod_olustur()
        img = barkod_png(kod)

        with db() as con:
            con.execute("""
            INSERT INTO urunler (barkod,isim,cins,ebat,kalinlik,sinif,yuzey,renk,adet,depo,tarih)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,(
                kod,
                request.form["isim"],
                request.form["cins"],
                request.form["ebat"],
                request.form["kalinlik"],
                request.form["sinif"],
                request.form["yuzey"],
                request.form["renk"],
                request.form["adet"],
                request.form["depo"],
                datetime.now().strftime("%Y-%m-%d %H:%M")
            ))
        return redirect("/panel")

    with db() as con:
        urunler = con.execute("SELECT * FROM urunler ORDER BY id DESC").fetchall()

    return render_template_string("""
<style>
body{background:#0f172a;color:white;font-family:Arial}
.header{background:#22c55e;padding:15px;text-align:center;font-size:22px}
.container{display:flex}
.left{width:40%;padding:10px}
.right{width:60%;padding:10px}
.card{background:#1e293b;padding:10px;border-radius:10px;margin-bottom:10px}
input,select{width:100%;padding:10px;margin:5px;border-radius:8px;border:none}
button{width:100%;padding:15px;margin-top:5px;border:none;border-radius:10px}
.btn-green{background:#22c55e}
.btn-red{background:#ef4444}
.btn-blue{background:#3b82f6}
table{width:100%}
th{background:#22c55e;color:black;padding:10px}
td{padding:10px;text-align:center}
tr:nth-child(even){background:#1e293b}
tr:nth-child(odd){background:#334155}
</style>

<div class="header">🌲 KASA PANEL</div>

<div class="container">

<div class="left">
<div class="card">
<form method="post">
<input name="isim" placeholder="İsim">
<input name="cins" placeholder="Cins">
<input name="ebat" placeholder="Ebat">
<input name="kalinlik" placeholder="Kalınlık">
<input name="sinif" placeholder="Sınıf">

<select name="yuzey">
<option>HG</option><option>MAT</option>
</select>

<input name="renk" placeholder="Renk">
<input name="adet" type="number" placeholder="Adet">

<select name="depo">
<option>MDF</option><option>KAPI</option>
</select>

<button class="btn-green">➕ EKLE</button>
</form>
</div>

<a href="/excel"><button class="btn-blue">📊 Excel</button></a>

</div>

<div class="right">
<table>
<tr><th>Barkod</th><th>İsim</th><th>Adet</th><th>İşlem</th></tr>

{% for u in urunler %}
<tr>
<td>{{u[1]}}</td>
<td>{{u[2]}}</td>
<td>{{u[9]}}</td>
<td>
<a href="/dus/{{u[1]}}"><button class="btn-red">➖</button></a>
<a href="/etiket/{{u[1]}}"><button class="btn-blue">🧾</button></a>
</td>
</tr>
{% endfor %}

</table>
</div>

</div>
""", urunler=urunler)

# --- STOK DÜŞ ---
@app.route("/dus/<kod>")
def dus(kod):
    with db() as con:
        con.execute("UPDATE urunler SET adet=adet-1 WHERE barkod=?", (kod,))
    return redirect("/panel")

# --- ETİKET ---
@app.route("/etiket/<kod>")
def etiket(kod):
    with db() as con:
        u = con.execute("SELECT * FROM urunler WHERE barkod=?", (kod,)).fetchone()
    return f"""
    <h2>{u[2]}</h2>
    <img src="/static/{kod}.png">
    <p>Adet: {u[9]}</p>
    """

# --- EXCEL ---
@app.route("/excel")
def excel():
    wb = Workbook()
    ws = wb.active
    ws.append(["Barkod","İsim","Adet","Depo"])

    with db() as con:
        for u in con.execute("SELECT * FROM urunler"):
            ws.append([u[1],u[2],u[9],u[10]])

    file = "stok.xlsx"
    wb.save(file)
    return send_file(file, as_attachment=True)

# --- MAIN ---
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
