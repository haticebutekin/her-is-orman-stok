from flask import Flask, request, redirect, session
import sqlite3, random

app = Flask(__name__)
app.secret_key = "1234"

conn = sqlite3.connect("db.db", check_same_thread=False)
c = conn.cursor()

# 🔥 FULL TABLO
c.execute("""
CREATE TABLE IF NOT EXISTS urun(
id INTEGER PRIMARY KEY,
barkod TEXT,
ad TEXT,
cins TEXT,
ebat TEXT,
renk TEXT,
yuzey TEXT,
fiyat REAL,
stok INTEGER
)
""")
conn.commit()

def barkod():
    return str(random.randint(100000000000,999999999999))

# ANA SAYFA
@app.route("/")
def home():
    urunler = c.execute("SELECT * FROM urun").fetchall()

    html = """
    <html>
    <head>
    <style>
    body{background:#0f172a;color:white;font-family:Arial;padding:20px;}
    input,select,button{padding:8px;margin:5px;}
    table{width:100%;border-collapse:collapse;}
    td,th{border:1px solid gray;padding:8px;}
    </style>
    </head>

    <body>

    <h1>🌲 ORMAN KASA PRO</h1>

    <h2>➕ ÜRÜN EKLE</h2>

    <form method="POST" action="/ekle">
    Barkod <input name="barkod"><br>
    Ad <input name="ad"><br>
    Cins <input name="cins"><br>
    Ebat <input name="ebat"><br>
    Renk <input name="renk"><br>

    Yüzey
    <select name="yuzey">
        <option value="HG">HG</option>
        <option value="MAT">MAT</option>
    </select><br>

    Fiyat <input name="fiyat"><br>
    Stok <input name="stok"><br>

    <button>Kaydet</button>
    </form>

    <h2>📦 Ürünler</h2>

    <table>
    <tr>
    <th>Barkod</th>
    <th>Ad</th>
    <th>Cins</th>
    <th>Ebat</th>
    <th>Renk</th>
    <th>Yüzey</th>
    <th>Fiyat</th>
    <th>Stok</th>
    </tr>
    """

    for u in urunler:
        html += f"""
        <tr>
        <td>{u[1]}</td>
        <td>{u[2]}</td>
        <td>{u[3]}</td>
        <td>{u[4]}</td>
        <td>{u[5]}</td>
        <td>{u[6]}</td>
        <td>{u[7]}</td>
        <td>{u[8]}</td>
        </tr>
        """

    html += "</table></body></html>"
    return html

# ÜRÜN EKLE
@app.route("/ekle", methods=["POST"])
def ekle():
    barkod_v = request.form.get("barkod") or barkod()
    ad = request.form.get("ad")
    cins = request.form.get("cins")
    ebat = request.form.get("ebat")
    renk = request.form.get("renk")
    yuzey = request.form.get("yuzey")
    fiyat = request.form.get("fiyat")
    stok = request.form.get("stok")

    c.execute("""
    INSERT INTO urun (barkod,ad,cins,ebat,renk,yuzey,fiyat,stok)
    VALUES (?,?,?,?,?,?,?,?)
    """,(barkod_v,ad,cins,ebat,renk,yuzey,fiyat,stok))

    conn.commit()

    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
