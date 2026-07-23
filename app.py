from flask import Flask, request, render_template_string, redirect, send_file
import sqlite3
import random
import pandas as pd
import os

app = Flask(__name__)

# ---------------- DB ----------------
def init_db():
    with sqlite3.connect("stok.db") as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS urunler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            urun TEXT,
            depo TEXT,
            adet INTEGER,
            barkod TEXT UNIQUE
        )
        """)
init_db()

def barkod_olustur():
    return str(random.randint(100000000000, 999999999999))

# ---------------- HTML ----------------
HTML = """
<!DOCTYPE html>
<html>
<head>
<title>DEPO PRO</title>
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
.kirmizi { background:#ef4444; }
.mavi { background:#3b82f6; }
</style>
</head>

<body>

<h1>📦 STOK YÖNETİM PRO</h1>

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
<a href="/excel"><button>EXCEL</button></a>

<h2>ÜRÜNLER</h2>

{% for u in urunler %}
<div class="card">
<b>{{u[1]}}</b><br>
📦 {{u[2]}}<br>
🔢 {{u[3]}}<br>
🏷 {{u[4]}}<br>

<a href="/arttir/{{u[0]}}"><button class="mavi">+ ARTIR</button></a>
<a href="/azalt/{{u[0]}}"><button class="kirmizi">- AZALT</button></a>
<a href="/sil/{{u[0]}}"><button class="kirmizi">SİL</button></a>
</div>
{% endfor %}

</body>
</html>
"""

# ---------------- DB ----------------
def get_all():
    with sqlite3.connect("stok.db") as conn:
        return conn.execute("SELECT * FROM urunler").fetchall()

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template_string(HTML, urunler=get_all())

@app.route("/ekle", methods=["POST"])
def ekle():
    try:
        with sqlite3.connect("stok.db") as conn:
            conn.execute(
                "INSERT INTO urunler (urun,depo,adet,barkod) VALUES (?,?,?,?)",
                (
                    request.form["urun"],
                    request.form["depo"],
                    int(request.form["adet"]),
                    barkod_olustur()
                )
            )
    except:
        pass
    return redirect("/")

@app.route("/sil/<int:id>")
def sil(id):
    with sqlite3.connect("stok.db") as conn:
        conn.execute("DELETE FROM urunler WHERE id=?", (id,))
    return redirect("/")

@app.route("/arttir/<int:id>")
def arttir(id):
    with sqlite3.connect("stok.db") as conn:
        conn.execute("UPDATE urunler SET adet = adet + 1 WHERE id=?", (id,))
    return redirect("/")

@app.route("/azalt/<int:id>")
def azalt(id):
    with sqlite3.connect("stok.db") as conn:
        conn.execute("UPDATE urunler SET adet = CASE WHEN adet>0 THEN adet-1 ELSE 0 END WHERE id=?", (id,))
    return redirect("/")

@app.route("/ara")
def ara():
    q = request.args.get("q", "")

    with sqlite3.connect("stok.db") as conn:
        data = conn.execute(
            "SELECT * FROM urunler WHERE barkod LIKE ?",
            ("%" + q + "%",)
        ).fetchall()

    return render_template_string(HTML, urunler=data)

@app.route("/excel")
def excel():
    file = "stok.xlsx"

    with sqlite3.connect("stok.db") as conn:
        df = pd.read_sql_query("SELECT * FROM urunler", conn)

    if os.path.exists(file):
        os.remove(file)

    df.to_excel(file, index=False)

    return send_file(file, as_attachment=True)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
