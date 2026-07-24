from flask import Flask, render_template_string, request, redirect, session
import sqlite3, datetime

app = Flask(__name__)
app.secret_key = "secret123"

cart = []

def init_db():
    conn = sqlite3.connect("market.db")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        type TEXT,
        size TEXT,
        class TEXT,
        hg TEXT,
        color TEXT,
        stock INTEGER,
        price REAL,
        barcode TEXT,
        depo TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        total REAL,
        date TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )""")

    c.execute("SELECT * FROM users")
    if not c.fetchall():
        c.execute("INSERT INTO users VALUES (NULL,'admin','1234')")

    conn.commit()
    conn.close()

init_db()

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = sqlite3.connect("market.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        if c.fetchone():
            session["user"] = u
            return redirect("/panel")
        conn.close()

    return """
    <style>
    body{background:#0f172a;color:white;text-align:center;font-family:sans-serif}
    input,button{padding:10px;margin:5px;border-radius:8px;border:none}
    button{background:#22c55e;color:white}
    </style>
    <h1>🔐 GİRİŞ</h1>
    <form method="post">
    <input name="username" placeholder="Kullanıcı"><br>
    <input name="password" placeholder="Şifre"><br>
    <button>GİRİŞ</button>
    </form>
    """

# PANEL
@app.route("/panel")
def panel():
    return """
    <h1>📊 PANEL</h1>
    <a href="/urun">Ürün Ekle</a><br>
    <a href="/liste">Liste</a><br>
    <a href="/kasa">Kasa</a>
    """

# ÜRÜN EKLE
@app.route("/urun", methods=["GET","POST"])
def urun():
    if request.method == "POST":
        data = tuple(request.form.values())

        conn = sqlite3.connect("market.db")
        c = conn.cursor()
        c.execute("""INSERT INTO products
        (name,type,size,class,hg,color,stock,price,barcode,depo)
        VALUES (?,?,?,?,?,?,?,?,?,?)""", data)
        conn.commit()
        conn.close()

    return """
    <h2>Ürün</h2>
    <form method="post">
    Ad<input name="name"><br>
    Cins<input name="type"><br>
    Ebat<input name="size"><br>
    Sınıf<input name="class"><br>
    HG/Mat<input name="hg"><br>
    Renk<input name="color"><br>
    Stok<input name="stock"><br>
    Fiyat<input name="price"><br>
    Barkod<input name="barcode"><br>
    <select name="depo">
    <option>MDF SATIŞ DEPOSU</option>
    <option>LAMİNANT DEPOSU</option>
    <option>KAPI DEPOSU</option>
    <option>HGLOSS DEPOSU (MORAY YANI)</option>
    <option>SÜTÇÜ YANI</option>
    <option>HELVACI YANI</option>
    <option>RÖTBALANSÇI YANI</option>
    <option>KESİMHANE</option>
    </select><br>
    <button>KAYDET</button>
    </form>
    """

# LİSTE
@app.route("/liste")
def liste():
    conn = sqlite3.connect("market.db")
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    data = c.fetchall()
    conn.close()

    html = "<h2>Ürünler</h2><table border=1>"
    for x in data:
        html += f"<tr><td>{x}</td></tr>"
    html += "</table>"
    return html

# 🛒 PRO KASA
@app.route("/kasa")
def kasa():
    total = sum([x[8] for x in cart]) if cart else 0

    return render_template_string("""
    <style>
    body{margin:0;font-family:sans-serif;background:#111;color:white}
    .container{display:flex}
    .left{width:70%;padding:20px}
    .right{width:30%;background:#1f2937;padding:20px}
    input{width:100%;padding:15px;font-size:20px;border-radius:10px;border:none}
    table{width:100%;margin-top:10px}
    td{padding:10px;border-bottom:1px solid gray}
    .total{font-size:30px;color:#22c55e}
    button{width:100%;padding:15px;margin-top:10px;border:none;border-radius:10px;background:#22c55e;color:white;font-size:20px}
    </style>

    <div class="container">
        <div class="left">
            <h1>🛒 KASA</h1>
            <form method="post" action="/kasa_ekle">
                <input name="barcode" placeholder="Barkod okut..." autofocus>
            </form>

            <table>
            {% for x in cart %}
                <tr>
                    <td>{{x[1]}}</td>
                    <td>{{x[2]}}</td>
                    <td>{{x[3]}}</td>
                    <td>{{x[6]}}</td>
                    <td>{{x[8]}} TL</td>
                </tr>
            {% endfor %}
            </table>
        </div>

        <div class="right">
            <h2>Toplam</h2>
            <div class="total">{{total}} TL</div>

            <form method="post" action="/satis">
                <button>✔ SATIŞ TAMAMLA</button>
            </form>
        </div>
    </div>
    """, cart=cart, total=total)

# EKLE
@app.route("/kasa_ekle", methods=["POST"])
def kasa_ekle():
    barcode = request.form["barcode"]

    conn = sqlite3.connect("market.db")
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE barcode=?", (barcode,))
    urun = c.fetchone()

    if urun:
        cart.append(urun)
        c.execute("UPDATE products SET stock=stock-1 WHERE id=?", (urun[0],))
        conn.commit()

    conn.close()
    return redirect("/kasa")

# SATIŞ
@app.route("/satis", methods=["POST"])
def satis():
    global cart
    total = sum([x[8] for x in cart])

    conn = sqlite3.connect("market.db")
    c = conn.cursor()
    c.execute("INSERT INTO sales (total,date) VALUES (?,?)",
              (total, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()

    cart = []
    return redirect("/kasa")

if __name__ == "__main__":
    app.run(debug=True)
