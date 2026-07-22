from flask import Flask, request, redirect
import sqlite3

app = Flask(__name__)

# DB
conn = sqlite3.connect("db.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS urun(
id INTEGER PRIMARY KEY AUTOINCREMENT,
barkod TEXT,
ad TEXT,
cins TEXT,
ebat TEXT,
sinif TEXT,
renk TEXT,
yuzey TEXT,
adet INTEGER,
fiyat REAL
)
""")
conn.commit()


@app.route("/")
def home():
    urunler = c.execute("SELECT * FROM urun").fetchall()

    html = """
    <html>
    <head>
    <title>ORMAN KASA PRO</title>
    <style>
    body { background:#0f172a; color:white; font-family:Arial; padding:20px;}
    input,button { padding:10px; margin:5px; border-radius:8px; border:none;}
    input { width:150px;}
    button { background:#22c55e; color:white; cursor:pointer;}
    table { width:100%; margin-top:20px; border-collapse: collapse;}
    td,th { border:1px solid gray; padding:10px;}
    </style>
    </head>
    <body>

    <h1>🌲 ORMAN KASA PRO</h1>

    <form action="/ekle" method="POST">
    Barkod <input name="barkod"><br>
    Ad <input name="ad"><br>
    Cins <input name="cins"><br>
    Ebat <input name="ebat"><br>
    Sınıf <input name="sinif"><br>
    Renk <input name="renk"><br>
    Yüzey <input name="yuzey"><br>
    Adet <input name="adet" type="number"><br>
    Fiyat <input name="fiyat" type="number" step="0.01"><br>

    <button type="submit">➕ ÜRÜN EKLE</button>
    </form>

    <h2>📦 Ürünler</h2>
    <table>
    <tr>
    <th>Barkod</th><th>Ad</th><th>Cins</th><th>Ebat</th><th>Sınıf</th><th>Renk</th><th>Yüzey</th><th>Adet</th><th>Fiyat</th>
    </tr>
    """

    for u in urunler:
        html += f"<tr><td>{u[1]}</td><td>{u[2]}</td><td>{u[3]}</td><td>{u[4]}</td><td>{u[5]}</td><td>{u[6]}</td><td>{u[7]}</td><td>{u[8]}</td><td>{u[9]}</td></tr>"

    html += "</table></body></html>"
    return html


# 🔥 BURASI ÖNEMLİ (ÜRÜN EKLE FIX)
@app.route("/ekle", methods=["POST"])
def ekle():
    try:
        barkod = request.form.get("barkod")
        ad = request.form.get("ad")
        cins = request.form.get("cins")
        ebat = request.form.get("ebat")
        sinif = request.form.get("sinif")
        renk = request.form.get("renk")
        yuzey = request.form.get("yuzey")
        adet = request.form.get("adet")
        fiyat = request.form.get("fiyat")

        c.execute("""
        INSERT INTO urun (barkod, ad, cins, ebat, sinif, renk, yuzey, adet, fiyat)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (barkod, ad, cins, ebat, sinif, renk, yuzey, adet, fiyat))

        conn.commit()

    except Exception as e:
        return f"HATA: {e}"

    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
