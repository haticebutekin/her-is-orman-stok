from flask import Flask, request, redirect, session, render_template_string
import sqlite3
from datetime import datetime
from flask import session

cart = []

@app.route("/kasa")
def kasa():
    if "user" not in session:
        return redirect("/")

    return render_template_string("""
    <h1>🛒 KASA EKRANI</h1>

    <form method="post" action="/kasa_ekle">
        Barkod: <input name="barcode" autofocus>
        <button>EKLE</button>
    </form>

    <h2>Sepet</h2>
    <table border=1>
    <tr>
        <th>Ad</th><th>Cins</th><th>Ebat</th><th>Sınıf</th>
        <th>HG/Mat</th><th>Renk</th><th>Fiyat</th>
    </tr>

    {% for item in cart %}
    <tr>
        <td>{{item[1]}}</td>
        <td>{{item[2]}}</td>
        <td>{{item[3]}}</td>
        <td>{{item[4]}}</td>
        <td>{{item[5]}}</td>
        <td>{{item[6]}}</td>
        <td>{{item[7]}}</td>
    </tr>
    {% endfor %}
    </table>

    <h2>Toplam: {{total}} TL</h2>

    <form method="post" action="/satis_tamamla">
        <button style="font-size:20px;">SATIŞ TAMAMLA</button>
    </form>

    <a href="/panel">Panele dön</a>
    """, cart=cart, total=sum([x[7] for x in cart]))

@app.route("/kasa_ekle", methods=["POST"])
def kasa_ekle():
    barcode = request.form["barcode"]

    conn = sqlite3.connect("market.db")
    c = conn.cursor()

    c.execute("SELECT * FROM products WHERE barcode=?", (barcode,))
    urun = c.fetchone()

    if urun:
        cart.append(urun)

        # stok düş
        c.execute("UPDATE products SET stock = stock - 1 WHERE id=?", (urun[0],))
        conn.commit()

    conn.close()
    return redirect("/kasa")

@app.route("/satis_tamamla", methods=["POST"])
def satis_tamamla():
    global cart

    toplam = sum([x[7] for x in cart])

    conn = sqlite3.connect("market.db")
    c = conn.cursor()

    c.execute("INSERT INTO sales (total, date) VALUES (?, ?)",
              (toplam, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

    cart = []
    return redirect("/kasa")

app = Flask(__name__)
app.secret_key = "secret"

def db():
    return sqlite3.connect("pro.db")

# ---------------- SETUP ----------------
def setup():
    conn = db()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY,
        name TEXT,
        barcode TEXT,
        stock INTEGER,
        min_stock INTEGER,
        depo INTEGER
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS depots(
        id INTEGER PRIMARY KEY,
        name TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY,
        user TEXT,
        action TEXT,
        detail TEXT,
        date TEXT
    )""")

    # 🔥 SENİN DEPOLARIN
    depots = [
        (1, "MDF SATIŞ DEPOSU"),
        (2, "LAMİNANT DEPOSU"),
        (3, "KAPI DEPOSU"),
        (4, "HGLOSS DEPOSU (MORAY YANI)"),
        (5, "SÜTÇÜ YANI"),
        (6, "HELVACI YANI"),
        (7, "RÖTBALANSÇI YANI"),
        (8, "KESİMHANE")
    ]

    for d in depots:
        c.execute("INSERT OR IGNORE INTO depots(id,name) VALUES (?,?)", d)

    users = [
        ("admin","1234","admin"),
        ("depo","1234","depo")
    ]

    for u in users:
        c.execute("INSERT OR IGNORE INTO users(username,password,role) VALUES (?,?,?)", u)

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

    return """
    <h2>STOK SİSTEMİ</h2>
    <form method=post>
    <input name=u placeholder="Kullanıcı"><br>
    <input name=p type=password placeholder="Şifre"><br>
    <button>Giriş</button>
    </form>
    """

# ---------------- PANEL ----------------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    conn = db()
    c = conn.cursor()

    products = c.execute("""
    SELECT p.id, p.name, p.barcode, p.stock, p.min_stock, d.name
    FROM products p
    JOIN depots d ON p.depo = d.id
    """).fetchall()

    depots = c.execute("SELECT * FROM depots").fetchall()

    return render_template_string("""
    <h2>{{user}} ({{role}})</h2>

    <a href="/transfer">Transfer</a>
    <a href="/logs">Log</a>

    <hr>

    {% for p in products %}
    <div>
    {{p[1]}} | {{p[5]}} | Stok: {{p[3]}}
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

    <select name=depo>
    {% for d in depots %}
    <option value="{{d[0]}}">{{d[1]}}</option>
    {% endfor %}
    </select>

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

    <select name=depo>
    {% for d in depots %}
    <option value="{{d[0]}}">{{d[1]}}</option>
    {% endfor %}
    </select>

    <button>Ekle</button>
    </form>
    {% endif %}
    """, products=products, depots=depots, user=session["user"], role=session["role"])

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

    if p and p[3] > 0:
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

    conn = db()
    c = conn.cursor()
    depots = c.execute("SELECT * FROM depots").fetchall()

    if request.method=="POST":
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

    return render_template_string("""
    <h2>Transfer</h2>
    <form method=post>
    Barkod <input name=barcode><br>
    Miktar <input name=miktar><br>

    Nereden
    <select name=from>
    {% for d in depots %}
    <option value="{{d[0]}}">{{d[1]}}</option>
    {% endfor %}
    </select>

    Nereye
    <select name=to>
    {% for d in depots %}
    <option value="{{d[0]}}">{{d[1]}}</option>
    {% endfor %}
    </select>

    <button>Yap</button>
    </form>
    """, depots=depots)

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
