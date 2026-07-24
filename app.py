from flask import Flask, request, redirect, render_template_string, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# DB
def db():
    return sqlite3.connect("system.db")

# TABLOLAR
def init():
    con = db()
    c = con.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS depots (
        id INTEGER PRIMARY KEY,
        name TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY,
        name TEXT,
        barcode TEXT,
        price REAL,
        stock INTEGER,
        type TEXT,
        size TEXT,
        class TEXT,
        hg TEXT,
        surface TEXT,
        color TEXT,
        depot_id INTEGER
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY,
        total REAL,
        user TEXT,
        date TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY,
        user TEXT,
        action TEXT,
        date TEXT
    )""")

    # admin
    c.execute("SELECT * FROM users")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (NULL,'admin','1234')")

    con.commit()
    con.close()

init()

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["u"]
        p = request.form["p"]

        con = db()
        c = con.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        user = c.fetchone()

        if user:
            session["user"] = u
            return redirect("/panel")

    return """
    <h2>Login</h2>
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
    return """
    <h2>Panel</h2>
    <a href='/add_product'>Ürün Ekle</a><br>
    <a href='/products'>Ürünler</a><br>
    <a href='/sale'>Satış</a><br>
    <a href='/logs'>Loglar</a><br>
    <a href='/depots'>Depolar</a><br>
    """

# DEPO
@app.route("/depots", methods=["GET","POST"])
def depots():
    if request.method=="POST":
        name = request.form["name"]
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

# ÜRÜN EKLE
@app.route("/add_product", methods=["GET","POST"])
def add_product():
    if request.method=="POST":
        data = (
            request.form["name"],
            request.form["barcode"],
            request.form["price"],
            request.form["stock"],
            request.form["type"],
            request.form["size"],
            request.form["class"],
            request.form["hg"],
            request.form["surface"],
            request.form["color"],
            request.form["depot"]
        )

        con=db();c=con.cursor()
        c.execute("""INSERT INTO products VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?)""",data)

        c.execute("INSERT INTO logs VALUES(NULL,?,?,?)",
                  (session["user"],"Ürün eklendi",datetime.now()))
        con.commit();con.close()

    con=db();c=con.cursor()
    depots=c.execute("SELECT * FROM depots").fetchall()
    con.close()

    options=""
    for d in depots:
        options+=f"<option value={d[0]}>{d[1]}</option>"

    return f"""
    <h2>Ürün Ekle</h2>
    <form method=post>
    İsim<input name=name><br>
    Barkod<input name=barcode><br>
    Fiyat<input name=price><br>
    Stok<input name=stock><br>
    Cins<input name=type><br>
    Ebat<input name=size><br>
    Sınıf<input name=class><br>
    HG<select name=hg><option>Evet</option><option>Hayır</option></select><br>
    Yüzey<select name=surface><option>Mat</option><option>Parlak</option></select><br>
    Renk<input name=color><br>
    Depo<select name=depot>{options}</select><br>
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
        html+=f"<p>{p[1]} | {p[10]} | HG:{p[8]} | Depo:{p[11]}</p>"
    return html

# SATIŞ
@app.route("/sale", methods=["GET","POST"])
def sale():
    if request.method=="POST":
        total=request.form["total"]
        con=db();c=con.cursor()
        c.execute("INSERT INTO sales VALUES(NULL,?,?,?)",
                  (total,session["user"],datetime.now()))

        c.execute("INSERT INTO logs VALUES(NULL,?,?,?)",
                  (session["user"],"Satış yaptı",datetime.now()))
        con.commit();con.close()

    return """
    <h2>Satış</h2>
    <form method=post>
    Toplam<input name=total>
    <button>Sat</button>
    </form>
    """

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
