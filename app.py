from flask import Flask, render_template_string, request, send_file
import sqlite3, os
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)

if not os.path.exists("barcodes"):
    os.makedirs("barcodes")

# DB
def init_db():
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS stok (
        barkod TEXT PRIMARY KEY,
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
    ean.save(f"barcodes/{kod}")

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://unpkg.com/html5-qrcode"></script>

<style>
body { font-family:Arial; padding:10px; background:#f5f5f5;}
input,select,button { width:100%; padding:12px; margin:5px 0;}
.card { background:white; padding:10px; margin:5px; border-radius:8px;}
.red {background:#dc3545;color:white;padding:5px;}
.green {background:#28a745;color:white;padding:5px;}
</style>
</head>
<body>

<h2>📦 Barkod Stok</h2>

<div id="reader"></div>

<form method="POST">
<input id="barkod" name="barkod" placeholder="Barkod">
<input name="cins" placeholder="Cins">
<input name="ebat" placeholder="Ebat">
<input name="mm" placeholder="MM">

<select name="sinif">
<option>HG</option>
<option>MAT</option>
</select>

<input name="renk" placeholder="Renk">
<input name="adet" type="number" placeholder="Adet">

<select name="islem">
<option value="ekle">Yeni</option>
<option value="artir">Artır</option>
<option value="azalt">Azalt</option>
</select>

<button>✔ Kaydet</button>
</form>

<audio id="bip">
<source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg">
</audio>

<hr>

<a href="/etiket"><button>🧾 A4 Etiket Çıktı</button></a>
<a href="/excel"><button>📊 Excel</button></a>

<hr>

{% for i in stok %}
<div class="card">
<b>{{i[0]}}</b><br>
{{i[1]}} | {{i[2]}} | {{i[3]}}<br>
{{i[4]}} | {{i[5]}}<br>

{% if i[6] <= 0 %}
<div class="red">STOK BİTTİ</div>
{% else %}
<div class="green">Stok: {{i[6]}}</div>
{% endif %}

<img src="/barcode/{{i[0]}}" width="100%">
</div>
{% endfor %}

<script>
function onScanSuccess(decodedText) {
document.getElementById('barkod').value = decodedText;
document.getElementById('bip').play();
}

new Html5QrcodeScanner("reader",{fps:10,qrbox:250})
.render(onScanSuccess);
</script>

</body>
</html>
"""

@app.route("/", methods=["GET","POST"])
def index():
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()

    if request.method == "POST":
        barkod = request.form["barkod"]
        adet = int(request.form["adet"] or 0)
        islem = request.form["islem"]

        c.execute("SELECT * FROM stok WHERE barkod=?", (barkod,))
        urun = c.fetchone()

        if islem == "ekle":
            barkod_uret(barkod)
            c.execute("INSERT OR IGNORE INTO stok VALUES (?,?,?,?,?,?,?)",
                      (barkod,
                       request.form["cins"],
                       request.form["ebat"],
                       request.form["mm"],
                       request.form["sinif"],
                       request.form["renk"],
                       adet))

        elif urun:
            stok = urun[6]
            if islem == "artir":
                stok += adet
            else:
                stok -= adet
            c.execute("UPDATE stok SET adet=? WHERE barkod=?", (stok, barkod))

        conn.commit()

    c.execute("SELECT * FROM stok")
    data = c.fetchall()
    conn.close()

    return render_template_string(HTML, stok=data)

@app.route("/barcode/<kod>")
def barcode_img(kod):
    return send_file(f"barcodes/{kod}.png")


@app.route("/etiket")
def etiket():
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()
    c.execute("SELECT * FROM stok")
    data = c.fetchall()
    conn.close()

    html = "<h1>Etiketler</h1>"
    for i in data:
        html += f"""
        <div style='width:200px;float:left;border:1px solid #000;margin:5px;padding:5px;text-align:center'>
        <b>{i[1]}</b><br>
        <img src='/barcode/{i[0]}' width='180'><br>
        {i[0]}
        </div>
        """
    return html

app.run(host="0.0.0.0", port=5000)
