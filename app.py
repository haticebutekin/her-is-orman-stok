from flask import Flask, request, redirect, session, render_template_string
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

def db():
    return sqlite3.connect("system.db")

def init():
    con = db()
    c = con.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS depots(id INTEGER PRIMARY KEY, name TEXT)")
    c.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY,
        name TEXT, barcode TEXT, price REAL, stock INTEGER,
        type TEXT, size TEXT, class TEXT,
        hg TEXT, surface TEXT, color TEXT,
        depot_id INTEGER)""")
    c.execute("CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY, user TEXT, action TEXT, date TEXT)")

    if not c.execute("SELECT * FROM users").fetchone():
        c.execute("INSERT INTO users VALUES(NULL,'admin','1234','admin')")

    con.commit()
    con.close()

init()

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["u"]
        p = request.form["p"]

        con=db();c=con.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        user=c.fetchone()

        if user:
            session["user"]=u
            session["role"]=user[3]
            return redirect("/panel")

    return """
    <style>
    body{background:#111;color:white;font-family:Arial;text-align:center}
    input,button{padding:10px;margin:5px;border-radius:8px;border:none}
    button{background:#00c853;color:white}
    </style>
    <h1>GİRİŞ</h1>
    <form method=post>
    <input name=u placeholder=Kullanıcı><br>
    <input name=p type=password placeholder=Şifre><br>
    <button>Giriş</button>
    </form>
    """

# PANEL
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    return f"""
    <style>
    body{{background:#0d0d0d;color:white;font-family:Arial}}
    .card{{background:#1e1e1e;padding:20px;margin:10px;border-radius:12px;display:inline-block}}
    a{{color:white;text-decoration:none}}
    </style>

    <h2>Hoşgeldin {session['user']}</h2>

    <div class=card><a href='/products'>📦 Ürünler</a></div>
    <div class=card><a href='/add_product'>➕ Ürün Ekle</a></div>
    <div class=card><a href='/depots'>🏬 Depolar</a></div>
    <div class=card><a href='/logs'>📊 Loglar</a></div>
    """

# DEPOLAR
@app.route("/depots", methods=["GET","POST"])
def depots():
    if request.method=="POST":
        name=request.form["name"]
        con=db();c=con.cursor()
        c.execute("INSERT INTO depots VALUES(NULL,?)",(name,))
        con.commit();con.close()

    con=db();c=con.cursor()
    data=c.execute("SELECT * FROM depots").fetchall()
    con.close()

    html="<h2>Depolar</h2><form method=post><input name=name><button>Ekle</button></form>"
    for d in data:
        html+=f"<p>{d[1]}</p>"
    return html

@app.route("/scan")
def scan():
    return """
    <html>
    <head>
    <script src="https://unpkg.com/html5-qrcode"></script>
    </head>

    <body style="background:black;color:white;text-align:center">
    <h2>Barkod Okut</h2>

    <div id="reader" style="width:300px;margin:auto"></div>

    <form id="form" method="POST" action="/find_product">
        <input type="hidden" name="barcode" id="barcode">
    </form>

    <script>
    function onScanSuccess(decodedText) {
        document.getElementById("barcode").value = decodedText;
        document.getElementById("form").submit();
    }

    let scanner = new Html5QrcodeScanner("reader", { fps: 10, qrbox: 250 });
    scanner.render(onScanSuccess);
    </script>
    </body>
    </html>
    """

@app.route("/find_product", methods=["POST"])
def find_product():
    barcode = request.form["barcode"]

    con=db();c=con.cursor()
    c.execute("SELECT * FROM products WHERE barcode=?", (barcode,))
    p = c.fetchone()
    con.close()

    if p:
        return f"""
        <h2>Ürün Bulundu</h2>
        <b>{p[1]}</b><br>
        Fiyat: {p[3]}<br>
        Stok: {p[4]}<br>
        HG: {p[8]}<br>
        Yüzey: {p[9]}<br>
        <br>
        <a href="/scan">Yeni Tara</a>
        """
    else:
        return "<h2>Ürün bulunamadı</h2><a href='/scan'>Tekrar dene</a>"

# ÜRÜN EKLE
@app.route("/add_product", methods=["GET","POST"])
def add_product():
    if request.method=="POST":
        data=(
            request.form["name"], request.form["barcode"],
            request.form["price"], request.form["stock"],
            request.form["type"], request.form["size"],
            request.form["class"], request.form["hg"],
            request.form["surface"], request.form["color"],
            request.form["depot"]
        )

        con=db();c=con.cursor()
        c.execute("INSERT INTO products VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?)",data)

        c.execute("INSERT INTO logs VALUES(NULL,?,?,?)",
                  (session["user"],"Ürün ekledi",datetime.now()))
        con.commit();con.close()

    con=db();c=con.cursor()
    depots=c.execute("SELECT * FROM depots").fetchall()
    con.close()

    opt=""
    for d in depots:
        opt+=f"<option value={d[0]}>{d[1]}</option>"

    return f"""
    <style>
    body{{background:#121212;color:white;font-family:Arial}}
    input,select{{margin:5px;padding:8px;border-radius:8px}}
    button{{background:#00c853;color:white;padding:10px;border:none}}
    </style>

    <h2>Ürün Ekle</h2>
    <form method=post>
    İsim<input name=name><br>
    Barkod<input name=barcode><br>
    Fiyat<input name=price><br>
    Stok<input name=stock><br>
    Cins<input name=type><br>
    Ebat(mm)<input name=size><br>
    Sınıf<input name=class><br>

    HG<select name=hg>
        <option>Evet</option>
        <option>Hayır</option>
    </select><br>

    Yüzey<select name=surface>
        <option>Mat</option>
        <option>Parlak</option>
    </select><br>

    Renk<input name=color><br>

    Depo<select name=depot>{opt}</select><br>

    <button>Kaydet</button>
    </form>
    """

# ÜRÜNLER
@app.route("/products")
def products():
    con=db();c=con.cursor()
    data=c.execute("SELECT * FROM products").fetchall()
    con.close()

    html="<h2>Ürünler</h2>"
    for p in data:
        html+=f"""
        <div style='background:#1e1e1e;padding:10px;margin:10px;border-radius:10px'>
        <div class=card><a href='/scan'>📷 Barkod Okut</a></div>
        <b>{p[1]}</b><br>
        HG: {p[8]} | Yüzey: {p[9]}<br>
        Depo: {p[11]} | Stok: {p[4]}
        </div>
        """
    return html

# LOG
@app.route("/logs")
def logs():
    con=db();c=con.cursor()
    data=c.execute("SELECT * FROM logs").fetchall()
    con.close()

    html="<h2>Loglar</h2>"
    for l in data:
        html+=f"<p>{l[1]} - {l[2]} - {l[3]}</p>"
    return html

app.run(host="0.0.0.0", port=10000)
