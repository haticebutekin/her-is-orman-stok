from flask import Flask, request, render_template_string, redirect, send_file
import sqlite3
import random
import pandas as pd

app = Flask(__name__)

# DB oluştur
def init_db():
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS urunler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        urun TEXT,
        depo TEXT,
        adet INTEGER,
        barkod TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

def barkod_olustur():
    return str(random.randint(100000000000, 999999999999))

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>DEPO YÖNETİM</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<style>
body { font-family: Arial; background:#0f172a; color:white; text-align:center; }
h1 { color:#38bdf8; }

input, select, button {
    padding:10px; margin:5px; border-radius:8px; border:none;
}

button { background:#22c55e; color:white; cursor:pointer; }

.card {
    background:#1e293b; margin:10px; padding:15px; border-radius:10px;
}
</style>
</head>

<body>

<h1>📦 STOK YÖNETİM</h1>

<form method="POST" action="/ekle">
<input name="urun" placeholder="Ürün adı" required><br>

<select name="depo">
<option>1.MDF SATIŞ DEPOSU</option>
<option>2.LAMİNANT DEPOSU</option>
<option>3.KAPI DEPOSU</option>
<option>4.HGLOSS DEPOSU MORAYIN YANINDAKİ DEPO</option>
<option>5.SÜTÇÜNÜN YANINDAKİ DEPO</option>
<option>6.HELVACININ ORDAKİ DEPO</option>
<option>7.RÖTBALANSÇININ ORDAKİ DEPO</option>
<option>8.KESİMHANEDEKİ DEPO</option>
</select><br>

<input type="number" name="adet" placeholder="Adet" required><br>

<button>EKLE</button>
</form>

<form method="GET" action="/ara">
<input name="q" placeholder="Barkod ara">
<button>ARA</button>
</form>

<button onclick="window.print()">YAZDIR</button>
<a href="/excel"><button>EXCEL İNDİR</button></a>

<h2>ÜRÜNLER</h2>

{% for u in urunler %}
<div class="card">
<b>{{u[1]}}</b><br>
📦 {{u[2]}}<br>
🔢 {{u[3]}}<br>
🏷 {{u[4]}}<br>

<a href="/sil/{{u[0]}}"><button>SİL</button></a>
</div>
{% endfor %}

</body>
</html>
"""

def get_all():
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()
    c.execute("SELECT * FROM urunler")
    data = c.fetchall()
    conn.close()
    return data

@app.route("/")
def index():
    return render_template_string(HTML, urunler=get_all())

@app.route("/ekle", methods=["POST"])
def ekle():
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()

    c.execute("INSERT INTO urunler (urun,depo,adet,barkod) VALUES (?,?,?,?)", (
        request.form["urun"],
        request.form["depo"],
        request.form["adet"],
        barkod_olustur()
    ))

    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/sil/<int:id>")
def sil(id):
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()
    c.execute("DELETE FROM urunler WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/")

@app.route("/ara")
def ara():
    q = request.args.get("q")

    conn = sqlite3.connect("stok.db")
    c = conn.cursor()
    c.execute("SELECT * FROM urunler WHERE barkod LIKE ?", ("%"+q+"%",))
    data = c.fetchall()
    conn.close()

    return render_template_string(HTML, urunler=data)

@app.route("/excel")
def excel():
    conn = sqlite3.connect("stok.db")
    df = pd.read_sql_query("SELECT * FROM urunler", conn)
    conn.close()

    file = "stok.xlsx"
    df.to_excel(file, index=False)

    return send_file(file, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
