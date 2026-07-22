from flask import Flask, render_template_string, request, redirect, session, send_file, jsonify
import sqlite3, os, csv, hashlib
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = "supersecret"

if not os.path.exists("barcodes"):
    os.makedirs("barcodes")

# ---------------- DB ----------------
def hash_pass(p):
    return hashlib.sha256(p.encode()).hexdigest()

def init_db():
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()

    # stok
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

    # kullanıcılar
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        role TEXT
    )
    """)

    # admin yoksa oluştur
    c.execute("SELECT * FROM users WHERE username='admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?,?,?)",
                  ("admin", hash_pass("1234"), "admin"))

    conn.commit()
    conn.close()

init_db()

# ---------------- BARCODE ----------------
def barkod_uret(kod):
    EAN = barcode.get_barcode_class('code128')
    ean = EAN(kod, writer=ImageWriter())
    ean.save(f"barcodes/{kod}")

# ---------------- AUTH ----------------
def login_required():
    return "user" in session

def admin_required():
    return session.get("role") == "admin"

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["user"]
        p = hash_pass(request.form["pass"])

        conn = sqlite3.connect("stok.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = u
            session["role"] = user[2]
            return redirect("/")

    return """
    <h2>🔐 Giriş</h2>
    <form method="POST">
    <input name="user" placeholder="Kullanıcı">
    <input name="pass" type="password" placeholder="Şifre">
    <button>Giriş</button>
    </form>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- HTML ----------------
HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://unpkg.com/html5-qrcode"></script>

<style>
body { font-family:Arial; background:#f5f5f5; padding:10px;}
.card { background:white; padding:10px; margin:5px; border-radius:8px;}
input,button,select { width:100%; padding:10px; margin:5px 0;}
.red {background:#dc3545;color:white;padding:5px;}
.green {background:#28a745;color:white;padding:5px;}
.low {background:orange;color:white;padding:5px;}
</style>
</head>
<body>

<h2>📊 Dashboard</h2>
<div class="card">Toplam Ürün: {{toplam}}</div>
<div class="card">Toplam Stok: {{stok_sum}}</div>

<hr>

<div id="reader"></div>

<form method="POST">
<input id="barkod" name="barkod" placeholder="Barkod" required>
<input name="cins" placeholder="Cins">
<input name="adet" type="number" placeholder="Adet">

<select name="islem">
<option value="ekle">Yeni</option>
<option value="artir">Artır</option>
<option value="azalt">Azalt</option>
</select>

<button>Kaydet</button>
</form>

<hr>

<a href="/excel"><button>Excel</button></a>
<a href="/logout"><button>Çıkış</button></a>

<hr>

{% for i in stok %}
<div class="card">
<b>{{i[0]}}</b> - {{i[1]}} <br>

{% if i[6] <= 0 %}
<div class="red">BİTTİ</div>
{% elif i[6] < 5 %}
<div class="low">AZ</div>
{% else %}
<div class="green">{{i[6]}}</div>
{% endif %}

<img src="/barcode/{{i[0]}}" width="100%">

{% if role == "admin" %}
<a href="/sil/{{i[0]}}"><button>Sil</button></a>
{% endif %}
</div>
{% endfor %}

<script>
function onScanSuccess(decodedText) {
document.getElementById('barkod').value = decodedText;
}
new Html5QrcodeScanner("reader",{fps:10,qrbox:250}).render(onScanSuccess);
</script>

</body>
</html>
"""

# ---------------- MAIN ----------------
@app.route("/", methods=["GET","POST"])
def index():
    if not login_required():
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
                      (barkod, request.form["cins"], "", "", "", "", adet))

        elif urun:
            stok = urun[6]
            stok = stok + adet if islem=="artir" else stok - adet
            c.execute("UPDATE stok SET adet=? WHERE barkod=?", (stok, barkod))

        conn.commit()

    c.execute("SELECT * FROM stok")
    data = c.fetchall()

    c.execute("SELECT COUNT(*) FROM stok")
    toplam = c.fetchone()[0]

    c.execute("SELECT SUM(adet) FROM stok")
    stok_sum = c.fetchone()[0] or 0

    conn.close()

    return render_template_string(HTML, stok=data, toplam=toplam, stok_sum=stok_sum, role=session.get("role"))

# ---------------- DELETE ----------------
@app.route("/sil/<kod>")
def sil(kod):
    if not admin_required():
        return "Yetkisiz"

    conn = sqlite3.connect("stok.db")
    c = conn.cursor()
    c.execute("DELETE FROM stok WHERE barkod=?", (kod,))
    conn.commit()
    conn.close()
    return redirect("/")

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
        writer.writerows(data)

    return send_file("stok.csv", as_attachment=True)

# ---------------- API ----------------
@app.route("/api/stok")
def api_stok():
    conn = sqlite3.connect("stok.db")
    c = conn.cursor()
    c.execute("SELECT * FROM stok")
    data = c.fetchall()
    conn.close()
    return jsonify(data)

# ---------------- BARCODE ----------------
@app.route("/barcode/<kod>")
def barcode_img(kod):
    return send_file(f"barcodes/{kod}.png")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
