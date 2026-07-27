from flask import Flask, request, redirect, render_template_string
import sqlite3

app = Flask(__name__)
DB = "veri.db"

# ---------------- DB ----------------
def db():
    return sqlite3.connect(DB)

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS urun (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barkod TEXT,
            isim TEXT,
            fiyat REAL,
            stok INTEGER
        )""")

init_db()

# ---------------- PANEL ----------------
@app.route("/")
def panel():
    return render_template_string("""
    <style>
    body{
        margin:0;
        font-family:Arial;
        background: linear-gradient(135deg,#0f172a,#020617);
        color:white;
        text-align:center;
    }

    h1{padding:20px;}

    .container{width:90%;margin:auto;}

    .btn{
        display:block;
        padding:25px;
        margin:15px 0;
        border-radius:12px;
        font-size:22px;
        text-decoration:none;
        color:white;
        font-weight:bold;
        transition:0.2s;
    }

    .btn:hover{transform:scale(1.02);opacity:0.9;}

    .blue{background:linear-gradient(90deg,#3b82f6,#06b6d4);}
    .green{background:linear-gradient(90deg,#22c55e,#16a34a);}
    .orange{background:linear-gradient(90deg,#f97316,#f59e0b);}
    .purple{background:linear-gradient(90deg,#6366f1,#8b5cf6);}
    .red{background:linear-gradient(90deg,#ef4444,#dc2626);}
    </style>

    <h1>📦 STOK PANEL</h1>

    <div class="container">
        <a href="/urun_ekle" class="btn blue">➕ ÜRÜN EKLE</a>
        <a href="/satis" class="btn green">🛒 SATIŞ (KASA)</a>
        <a href="/stok" class="btn purple">📦 STOK</a>
    </div>
    """)

# ---------------- ÜRÜN EKLE ----------------
@app.route("/urun_ekle", methods=["GET","POST"])
def urun_ekle():
    if request.method == "POST":
        barkod = request.form["barkod"]
        isim = request.form["isim"]
        fiyat = request.form["fiyat"]
        stok = request.form["stok"]

        with db() as con:
            con.execute("INSERT INTO urun (barkod,isim,fiyat,stok) VALUES (?,?,?,?)",
                        (barkod,isim,fiyat,stok))

        return redirect("/")

    return render_template_string("""
    <style>
    body{background:#0f172a;color:white;font-family:Arial;text-align:center}
    input,button{padding:10px;margin:5px;width:90%}
    </style>

    <h2>Ürün Ekle</h2>

    <form method="post">
        <input name="barkod" placeholder="Barkod">
        <input name="isim" placeholder="Ürün adı">
        <input name="fiyat" placeholder="Fiyat">
        <input name="stok" placeholder="Stok">
        <button>Kaydet</button>
    </form>
    """)

# ---------------- STOK ----------------
@app.route("/stok")
def stok():
    with db() as con:
        data = con.execute("SELECT * FROM urun").fetchall()

    html = "<h2>STOK</h2>"
    for u in data:
        html += f"<div>{u[2]} - {u[3]} ₺ - {u[4]} adet</div>"

    return html

# ---------------- KASA ----------------
sepet = {}

@app.route("/satis", methods=["GET","POST"])
def satis():
    global sepet

    if request.method == "POST":
        barkod = request.form["barkod"]

        with db() as con:
            urun = con.execute("SELECT * FROM urun WHERE barkod=?",(barkod,)).fetchone()

        if urun:
            if barkod not in sepet:
                sepet[barkod] = {"isim":urun[2],"fiyat":urun[3],"adet":1}
            else:
                sepet[barkod]["adet"] += 1

    toplam = sum(v["fiyat"]*v["adet"] for v in sepet.values())

    return render_template_string("""
    <style>
    body{background:#020617;color:white;font-family:Arial}
    input,button{padding:15px;width:100%;margin:5px;font-size:18px}
    .box{background:#1e293b;padding:10px;margin:5px;border-radius:10px}
    .toplam{font-size:25px;color:#22c55e}
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

    <div class="toplam">TOPLAM: {{toplam}} ₺</div>

    <a href="/temizle"><button>🗑 Sepeti Temizle</button></a>
    """, sepet=sepet, toplam=toplam)

# ---------------- TEMİZLE ----------------
@app.route("/temizle")
def temizle():
    global sepet
    sepet = {}
    return redirect("/satis")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()
