from flask import Flask, render_template_string, request, redirect, send_file
import sqlite3
import pandas as pd
import barcode
from barcode.writer import ImageWriter
import os

app = Flask(__name__)

# klasör
if not os.path.exists("barcodes"):
    os.makedirs("barcodes")

# DB
def init_db():
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS stok (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barkod TEXT,
        cins TEXT,
        ebat TEXT,
        mm TEXT,
        sinif TEXT,
        renk TEXT,
        adet INTEGER
    )
    """)
    conn.commit()
    conn.close()

init_db()

# barkod üret
def barkod_uret(kod):
    EAN = barcode.get_barcode_class('code128')
    ean = EAN(kod, writer=ImageWriter())
    path = f"barcodes/{kod}"
    ean.save(path)
    return path + ".png"

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body { font-family: Arial; padding:10px; background:#f5f5f5;}
input,select,button { width:100%; padding:12px; margin:5px 0; font-size:16px;}
.card { background:white; padding:10px; margin:5px 0; border-radius:8px;}
img { width:100%; }
</style>
</head>
<body>

<h2>📦 Barkod Stok Sistemi</h2>

<form method="POST">
<input name="barkod" placeholder="Barkod (boş bırak otomatik)">
<input name="cins" placeholder="Malın Cinsi">
<input name="ebat" placeholder="Ebat">
<input name="mm" placeholder="MM">
<select name="sinif">
<option value="">Sınıf</option>
<option>HG</option>
<option>MAT</option>
</select>
<input name="renk" placeholder="Renk">
<input name="adet" type="number" placeholder="Adet">
<button type="submit">➕ Ekle & Barkod Oluştur</button>
</form>

<hr>

<a href="/excel"><button>📊 Excel İndir</button></a>

<hr>

{% for item in stok %}
<div class="card">
<b>{{item[1]}}</b><br>
{{item[2]}} | {{item[3]}} | {{item[4]}}<br>
Sınıf: {{item[5]}}<br>
Renk: {{item[6]}}<br>
Adet: {{item[7]}}<br><br>

<img src="/barcode/{{item[1]}}">
<a href="/barcode/{{item[1]}}" download>
<button>🖨️ Etiket İndir</button>
</a>

</div>
{% endfor %}

</body>
</html>
"""

@app.route("/", methods=["GET","POST"])
def index():
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()

    if request.method == "POST":

        barkod = request.form["barkod"]

        if barkod == "":
            barkod = "URUN" + str(len(c.execute("SELECT * FROM stok").fetchall()) + 1)

        barkod_uret(barkod)

        c.execute("INSERT INTO stok (barkod,cins,ebat,mm,sinif,renk,adet) VALUES (?,?,?,?,?,?,?)",
                  (barkod,
                   request.form["cins"],
                   request.form["ebat"],
                   request.form["mm"],
                   request.form["sinif"],
                   request.form["renk"],
                   request.form["adet"]))
        conn.commit()

    c.execute("SELECT * FROM stok")
    data = c.fetchall()
    conn.close()

    return render_template_string(HTML, stok=data)

@app.route("/barcode/<kod>")
def get_barcode(kod):
    return send_file(f"barcodes/{kod}.png", mimetype='image/png')

@app.route("/excel")
def excel():
    conn = sqlite3.connect("stok.db")
    df = pd.read_sql_query("SELECT * FROM stok", conn)
    file = "stok.xlsx"
    df.to_excel(file, index=False)
    conn.close()
    return send_file(file, as_attachment=True)

app.run(host="0.0.0.0", port=5000)
