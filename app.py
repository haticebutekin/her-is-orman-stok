from flask import Flask, render_template_string, request, redirect, session, send_file, jsonify
import sqlite3, os, csv
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = "secret123"

# klasör
if not os.path.exists("barcodes"):
    os.makedirs("barcodes")

# ---------------- DB ----------------
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

# ---------------- BARCODE ----------------
def barkod_uret(kod):
    EAN = barcode.get_barcode_class('code128')
    ean = EAN(kod, writer=ImageWriter())
    ean.save(f"barcodes/{kod}")

# ---------------- LOGIN ----------------
LOGIN_HTML = """
<h2>🔐 Giriş</h2>
<form method="POST">
<input name="user" placeholder="Kullanıcı">
<input name="pass" type="password" placeholder="Şifre">
<button>Giriş</button>
</form>
"""

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["user"] == "admin" and request.form["pass"] == "1234":
            session["ok"] = True
            return redirect("/")
    return LOGIN_HTML

def kontrol():
    return "ok" in session

# ---------------- HTML ----------------
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="manifest" href="/manifest.json">
<script src="https://unpkg.com/html5-qrcode"></script>

<style>
body { font-family:Arial; padding:10px; background:#f5f5f5;}
input,select,button { width:100%; padding:12px; margin:5px 0;}
.card { background:white; padding:10px; margin:5px; border-radius:8px;}
.red {background:#dc3545;color:white;padding:5px;}
.green {background:#28a745;color:white;padding:5px;}
.low {background:orange;color:white;padding:5px;}
</style>
</head>
<body>

<h2>📦 Stok Paneli</h2>

<form method="GET">
<input name="q" placeholder="Ara...">
<button>Ara</button>
</form>

<div id="reader"></div>

<form method="POST">
<input id="barkod" name="barkod" placeholder="Barkod" required>
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

<button>✔️ Kaydet</button>
</form>

<audio id="bip">
<source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg">
</audio>

<hr>

<a href="/excel"><button>📊 Excel indir</button></a>
<a href="/temizle"><button>🗑️ Tüm Stok Sıfırla</button></a>
<a href="/logout"><button>🚪 Çıkış</button></a>

<hr>

{% for i in stok %}
<div class="card">
<b>{{i[0]}}</b><br>
{{i[1]}} | {{i[2]}} | {{i[3]}}<br>

{% if i[6] <= 0 %}
<div class="red">STOK BİTTİ</div>
{% elif i[6] < 5 %}
<div class="low">AZ KALDI: {{i[6]}}</div>
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
new Html5QrcodeScanner("reader",{fps:10,qrbox:250}).render(onScanSuccess);

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}
</script>

</body>
</html>
"""

# ---------------- MAIN ----------------
@app.route("/", methods=["GET","POST"])
def index():
    if not kontrol():
        return redirect("/login")

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

    q = request.args.get("q")
    if q:
        c.execute("SELECT * FROM stok WHERE barkod LIKE ?", ('%'+q+'%',))
    else:
        c.execute("SELECT * FROM stok")

    data = c.fetchall()
    conn.close()

    return render_template_string(HTML, stok=data)

# ---------------- EXCEL ----------------
@app.route("/excel")
def excel():
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()
    c.execute("SELECT * FROM stok")
    data = c.fetchall()
    conn.close()

    with open("stok.csv","w",newline="",encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Barkod","Cins","Ebat","MM","Sınıf","Renk","Adet"])
        writer.writerows(data)

    return send_file("stok.csv", as_attachment=True)

# ---------------- TEMIZLE ----------------
@app.route("/temizle")
def temizle():
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()
    c.execute("DELETE FROM stok")
    conn.commit()
    conn.close()
    return redirect("/")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- BARCODE ----------------
@app.route("/barcode/<kod>")
def barcode_img(kod):
    return send_file(f"barcodes/{kod}.png")

# ---------------- PWA ----------------
@app.route("/manifest.json")
def manifest():
    return jsonify({
        "name": "Stok Barkod",
        "short_name": "Stok",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#28a745"
    })

@app.route("/sw.js")
def sw():
    return """
self.addEventListener('install', e => {
    e.waitUntil(
        caches.open('app').then(cache => cache.addAll(['/']))
    );
});
"""

# ---------------- RUN ----------------
app.run(host="0.0.0.0", port=5000)
