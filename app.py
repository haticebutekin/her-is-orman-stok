from flask import Flask, request, redirect, session, render_template_string
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "super_secret"

# ---------------- DB ----------------
def db():
    return sqlite3.connect("pro.db")

def setup():
    conn = db()
    c = conn.cursor()

    # ürünler
    c.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY,
        name TEXT,
        barcode TEXT,
        stock INTEGER,
        min_stock INTEGER,
        depo INTEGER
    )
    """)

    # kullanıcılar
    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # loglar
    c.execute("""
    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY,
        user TEXT,
        action TEXT,
        detail TEXT,
        date TEXT
    )
    """)

    # satış
    c.execute("""
    CREATE TABLE IF NOT EXISTS sales(
        id INTEGER PRIMARY KEY,
        user TEXT,
        total INTEGER,
        date TEXT
    )
    """)

    # depolar
    c.execute("""
    CREATE TABLE IF NOT EXISTS depots(
        id INTEGER PRIMARY KEY,
        name TEXT
    )
    """)

    # 8 depo
    for i in range(1,9):
        c.execute("INSERT OR IGNORE INTO depots(id,name) VALUES (?,?)",(i,f"Depo {i}"))

    # kullanıcılar
    users = [
        ("ramazan","1234","depo"),
        ("orhan","1234","depo"),
        ("behic","1234","depo"),
        ("hatice","1234","admin"),
        ("ahmet","1234","admin"),
        ("berke","1234","muhasebe"),
        ("irem","1234","muhasebe"),
    ]

    for u in users:
        c.execute("INSERT OR IGNORE INTO users(username,password,role) VALUES (?,?,?)",u)

    conn.commit()
    conn.close()

setup()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u = request.form["u"]
        p = request.form["p"]

        conn = db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        user = c.fetchone()

        if user:
            session["user"]=u
            session["role"]=user[3]
            return redirect("/panel")

    return render_template_string("""
    <h2>HER İŞ ORMAN STOK PRO</h2>
    <form method=post>
    <input name=u placeholder="Kullanıcı"><br>
    <input name=p type=password placeholder="Şifre"><br>
    <button>Giriş</button>
    </form>
    """)

# ---------------- PANEL ----------------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    conn = db()
    c = conn.cursor()

    products = c.execute("SELECT * FROM products").fetchall()

    return render_template_string("""
    <h2>{{user}} ({{role}})</h2>

    <a href="/transfer">📦 Transfer</a>
    <a href="/report">📊 Rapor</a>
    <a href="/logs">📜 Log</a>

    <hr>

    {% for p in products %}
    <div>
    {{p[1]}} | Depo {{p[5]}} | Stok: {{p[3]}}
    {% if p[3] <= p[4] %}
        🔴 KRİTİK
    {% elif p[3] <= p[4]+5 %}
        🟡 AZALIYOR
    {% endif %}
    </div>
    {% endfor %}

    <hr>

    <h3>Barkod düş</h3>
    <form action="/scan" method=post>
    <input name=barcode placeholder="Barkod">
    <input name=depo placeholder="Depo No">
    <button>Düş</button>
    </form>

    {% if role == "admin" %}
    <hr>
    <h3>Ürün ekle</h3>
    <form action="/add" method=post>
    İsim <input name=name>
    Barkod <input name=barcode>
    Stok <input name=stock>
    Min <input name=min>
    Depo <input name=depo>
    <button>Ekle</button>
    </form>
    {% endif %}
    """, products=products, user=session["user"], role=session["role"])

# ---------------- ÜRÜN EKLE ----------------
@app.route("/add", methods=["POST"])
def add():
    if session.get("role") != "admin":
        return "Yetki yok"

    conn = db()
    c = conn.cursor()

    c.execute("INSERT INTO products(name,barcode,stock,min_stock,depo) VALUES (?,?,?,?,?)",
              (request.form["name"],
               request.form["barcode"],
               int(request.form["stock"]),
               int(request.form["min"]),
               int(request.form["depo"])))

    conn.commit()
    conn.close()
    return redirect("/panel")

# ---------------- BARKOD ----------------
@app.route("/scan", methods=["POST"])
def scan():
    conn = db()
    c = conn.cursor()

    barcode = request.form["barcode"]
    depo = request.form["depo"]

    p = c.execute("SELECT * FROM products WHERE barcode=? AND depo=?",
                  (barcode,depo)).fetchone()

    if p:
        c.execute("UPDATE products SET stock=stock-1 WHERE id=?", (p[0],))

        c.execute("INSERT INTO logs(user,action,detail,date) VALUES (?,?,?,?)",
                  (session["user"],"stok düşüldü",p[1],datetime.now()))

    conn.commit()
    conn.close()
    return redirect("/panel")

# ---------------- TRANSFER ----------------
@app.route("/transfer", methods=["GET","POST"])
def transfer():
    if session.get("role") != "admin":
        return "Yetki yok"

    if request.method=="POST":
        conn = db()
        c = conn.cursor()

        barkod = request.form["barcode"]
        miktar = int(request.form["miktar"])
        f = request.form["from"]
        t = request.form["to"]

        p = c.execute("SELECT * FROM products WHERE barcode=? AND depo=?",(barkod,f)).fetchone()

        if p and p[3] >= miktar:
            c.execute("UPDATE products SET stock=stock-? WHERE id=?",(miktar,p[0]))

            hedef = c.execute("SELECT * FROM products WHERE barcode=? AND depo=?",(barkod,t)).fetchone()

            if hedef:
                c.execute("UPDATE products SET stock=stock+? WHERE id=?",(miktar,hedef[0]))
            else:
                c.execute("INSERT INTO products(name,barcode,stock,min_stock,depo) VALUES (?,?,?,?,?)",
                          (p[1],p[2],miktar,p[4],t))

            c.execute("INSERT INTO logs(user,action,detail,date) VALUES (?,?,?,?)",
                      (session["user"],"transfer",barkod,datetime.now()))

            conn.commit()
            conn.close()
            return redirect("/panel")

    return """
    <h2>Transfer</h2>
    <form method=post>
    Barkod <input name=barcode><br>
    Miktar <input name=miktar><br>
    Nereden <input name=from><br>
    Nereye <input name=to><br>
    <button>Yap</button>
    </form>
    """

# ---------------- RAPOR ----------------
@app.route("/report")
def report():
    conn = db()
    c = conn.cursor()

    gunluk = c.execute("SELECT date(date), COUNT(*) FROM logs GROUP BY date(date)").fetchall()
    kullanici = c.execute("SELECT user, COUNT(*) FROM logs GROUP BY user").fetchall()

    return render_template_string("""
    <h2>Rapor</h2>

    <h3>Günlük</h3>
    {% for g in gunluk %}
    <div>{{g[0]}} : {{g[1]}}</div>
    {% endfor %}

    <h3>Kullanıcı</h3>
    {% for k in kullanici %}
    <div>{{k[0]}} : {{k[1]}}</div>
    {% endfor %}

    <a href="/panel">Geri</a>
    """, gunluk=gunluk, kullanici=kullanici)

# ---------------- LOG ----------------
@app.route("/logs")
def logs():
    conn = db()
    c = conn.cursor()

    data = c.execute("SELECT * FROM logs ORDER BY id DESC").fetchall()

    return render_template_string("""
    <h2>Log</h2>
    {% for l in data %}
    <div>{{l[1]}} | {{l[2]}} | {{l[3]}} | {{l[4]}}</div>
    {% endfor %}
    <a href="/panel">Geri</a>
    """, data=data)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
