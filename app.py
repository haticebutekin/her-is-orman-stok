from flask import Flask, request, redirect
import sqlite3, os

app = Flask(__name__)

conn = sqlite3.connect("db.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS urun(
id INTEGER PRIMARY KEY,
barkod TEXT,
ad TEXT,
cins TEXT,
ebat TEXT,
sinif TEXT,
renk TEXT,
adet INTEGER,
fiyat REAL)""")
conn.commit()

sepet = []

@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form["k"]=="admin" and request.form["s"]=="1234":
            return redirect("/pos")
    return """<h2>Giriş</h2>
    <form method=post>
    <input name=k placeholder=Kullanıcı>
    <input name=s type=password placeholder=Şifre>
    <button>Giriş</button></form>"""

@app.route("/pos", methods=["GET","POST"])
def pos():
    global sepet

    if request.method=="POST":
        barkod = request.form["barkod"]
        u = c.execute("SELECT * FROM urun WHERE barkod=?",(barkod,)).fetchone()
        if u:
            sepet.append({"ad":u[2],"fiyat":u[8]})
            c.execute("UPDATE urun SET adet=adet-1 WHERE id=?",(u[0],))
            conn.commit()

    toplam=0
    rows=""
    for u in sepet:
        toplam+=u["fiyat"]
        rows+=f"<tr><td>{u['ad']}</td><td>{u['fiyat']}₺</td></tr>"

    return f"""
<style>
body{{background:#0f172a;color:white;font-family:Arial}}
input{{width:100%;padding:20px;font-size:22px}}
button{{padding:20px;font-size:20px;border:none;border-radius:10px}}
.btn{{background:#22c55e;color:black;width:100%}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px}}
.toplam{{font-size:35px;color:#22c55e}}
</style>

<h2>🌲 ORMAN KASA</h2>

<form method=post>
<input name=barkod placeholder="Barkod okut">
</form>

<div class=grid>
<a href=/odeme><button class=btn>💰 ÖDE</button></a>
<a href=/ekle><button class=btn>➕ ÜRÜN</button></a>
<a href=/rapor><button class=btn>📊 RAPOR</button></a>
<a href=/pos><button class=btn>🔄 YENİ</button></a>
</div>

<table>{rows}</table>

<p class=toplam>TOPLAM: {toplam} ₺</p>
"""

@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method=="POST":
        c.execute("INSERT INTO urun VALUES(NULL,?,?,?,?,?,?,?,?)",
        (request.form["b"],request.form["a"],request.form["c"],
         request.form["e"],request.form["s"],request.form["r"],
         request.form["adet"],request.form["f"]))
        conn.commit()
        return redirect("/pos")

    return """
<h2>Ürün Ekle</h2>
<form method=post>
Barkod <input name=b><br>
Ad <input name=a><br>
Cins <input name=c><br>
Ebat(mm) <input name=e><br>
Sınıf <input name=s><br>
Renk <input name=r><br>
Adet <input name=adet><br>
Fiyat <input name=f><br>
<button>Kaydet</button>
</form>
"""

@app.route("/rapor")
def rapor():
    data=c.execute("SELECT * FROM urun").fetchall()
    html=""
    for u in data:
        html+=f"<tr><td>{u[2]}</td><td>{u[7]}</td></tr>"
    return f"<h2>Stok</h2><table border=1>{html}</table><a href=/pos>Geri</a>"

@app.route("/odeme")
def odeme():
    global sepet
    txt="ORMAN\n"
    toplam=0
    for u in sepet:
        txt+=f"{u['ad']} {u['fiyat']} TL\n"
        toplam+=u["fiyat"]
    txt+=f"\nTOPLAM:{toplam}"

    open("fis.txt","w").write(txt)
    try: os.startfile("fis.txt","print")
    except: pass

    sepet.clear()
    return "<h3>Satış tamam</h3><a href=/pos>Geri</a>"

app.run(host="0.0.0.0", port=5000)