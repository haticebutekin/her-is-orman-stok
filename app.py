from flask import Flask, request, render_template_string, redirect, session, send_file
import sqlite3, random, pandas as pd, os

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DB ----------------
def init_db():
    with sqlite3.connect("db.db") as conn:
        c = conn.cursor()

        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            username TEXT,
            password TEXT,
            role TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS urunler(
            id INTEGER PRIMARY KEY,
            urun TEXT,
            depo TEXT,
            adet INTEGER,
            barkod TEXT UNIQUE
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS satis(
            id INTEGER PRIMARY KEY,
            barkod TEXT,
            adet INTEGER
        )""")

        # default kullanıcı
        c.execute("INSERT OR IGNORE INTO users VALUES (1,'admin','1234','admin')")

init_db()

def barkod():
    return str(random.randint(100000000000,999999999999))

# ---------------- LOGIN ----------------
LOGIN = """
<h2>Giriş</h2>
<form method="POST">
<input name="u" placeholder="Kullanıcı"><br>
<input name="p" placeholder="Şifre"><br>
<button>GİRİŞ</button>
</form>
"""

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        with sqlite3.connect("db.db") as conn:
            c = conn.cursor()
            user = c.execute("SELECT * FROM users WHERE username=? AND password=?",
                             (request.form["u"], request.form["p"])).fetchone()
            if user:
                session["user"]=user[1]
                session["role"]=user[3]
                return redirect("/")
    return LOGIN

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- MAIN UI ----------------
HTML = """
<h1>📦 STOK PRO</h1>
<a href="/logout">Çıkış</a>

<form method="POST" action="/ekle">
<input name="urun" placeholder="Ürün"><br>

<select name="depo">
<option>1.MDF</option>
<option>2.LAMİNANT</option>
<option>3.KAPI</option>
</select><br>

<input name="adet" type="number"><br>
<button>EKLE</button>
</form>

<form method="GET" action="/satis">
<input name="barkod" id="barcode" placeholder="Barkod">
<button>SAT</button>
</form>

<button onclick="startScan()">📷 OKUT</button>

<script src="https://unpkg.com/html5-qrcode"></script>
<script>
function startScan(){
    const scanner = new Html5Qrcode("reader");
    scanner.start({ facingMode: "environment" }, { fps: 10 },
    (txt)=>{
        document.getElementById("barcode").value = txt;
        scanner.stop();
    });
}
</script>

<div id="reader"></div>

<a href="/excel">EXCEL</a>

<hr>

{% for u in urunler %}
<div>
{{u[1]}} | {{u[2]}} | {{u[3]}} | {{u[4]}}

<a href="/arttir/{{u[0]}}">+</a>
<a href="/azalt/{{u[0]}}">-</a>

{% if session['role']=="admin" %}
<a href="/sil/{{u[0]}}">SİL</a>
{% endif %}
</div>
{% endfor %}
"""

# ---------------- ROUTES ----------------
def get_all():
    with sqlite3.connect("db.db") as conn:
        return conn.execute("SELECT * FROM urunler").fetchall()

@app.route("/")
def home():
    if "user" not in session:
        return redirect("/login")
    return render_template_string(HTML, urunler=get_all(), session=session)

@app.route("/ekle", methods=["POST"])
def ekle():
    with sqlite3.connect("db.db") as conn:
        conn.execute("INSERT INTO urunler (urun,depo,adet,barkod) VALUES (?,?,?,?)",
                     (request.form["urun"], request.form["depo"],
                      request.form["adet"], barkod()))
    return redirect("/")

@app.route("/arttir/<int:id>")
def arttir(id):
    with sqlite3.connect("db.db") as conn:
        conn.execute("UPDATE urunler SET adet=adet+1 WHERE id=?", (id,))
    return redirect("/")

@app.route("/azalt/<int:id>")
def azalt(id):
    with sqlite3.connect("db.db") as conn:
        conn.execute("UPDATE urunler SET adet=adet-1 WHERE id=? AND adet>0", (id,))
    return redirect("/")

@app.route("/sil/<int:id>")
def sil(id):
    if session.get("role")!="admin":
        return "Yetki yok"
    with sqlite3.connect("db.db") as conn:
        conn.execute("DELETE FROM urunler WHERE id=?", (id,))
    return redirect("/")

# ---------------- SATIŞ ----------------
@app.route("/satis")
def satis():
    barkod = request.args.get("barkod")

    with sqlite3.connect("db.db") as conn:
        c = conn.cursor()

        urun = c.execute("SELECT * FROM urunler WHERE barkod=?", (barkod,)).fetchone()

        if urun and urun[3] > 0:
            c.execute("UPDATE urunler SET adet=adet-1 WHERE barkod=?", (barkod,))
            c.execute("INSERT INTO satis (barkod,adet) VALUES (?,1)", (barkod,))
            conn.commit()

    return redirect("/")

# ---------------- EXCEL ----------------
@app.route("/excel")
def excel():
    file="stok.xlsx"
    with sqlite3.connect("db.db") as conn:
        df = pd.read_sql_query("SELECT * FROM urunler", conn)

    if os.path.exists(file):
        os.remove(file)

    df.to_excel(file, index=False)
    return send_file(file, as_attachment=True)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
