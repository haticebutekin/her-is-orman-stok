from flask import Flask, render_template_string, request, redirect, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# ================= DB =================
def init_db():
    conn = sqlite3.connect("db.sqlite")
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY,
        name TEXT,
        type TEXT,
        size TEXT,
        unit TEXT,
        class TEXT,
        color TEXT,
        barcode TEXT UNIQUE
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY,
        product_id INTEGER,
        depo TEXT,
        quantity INTEGER
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY,
        user TEXT,
        action TEXT,
        product TEXT,
        depo TEXT,
        quantity INTEGER,
        date TEXT
    )""")

    c.execute("INSERT OR IGNORE INTO users VALUES (1,'admin','1234')")
    conn.commit()
    conn.close()

init_db()

# ================= STYLE =================
style = """
<style>
body { font-family: Arial; background:#f4f6f9; margin:0; }
.container { max-width:900px; margin:auto; padding:20px; }
.card { background:white; padding:20px; border-radius:10px; box-shadow:0 5px 15px rgba(0,0,0,0.1); margin-bottom:20px;}
input,select,button { width:100%; padding:10px; margin:5px 0; border-radius:6px; border:1px solid #ccc;}
button { background:#007bff; color:white; border:none; cursor:pointer;}
button:hover { background:#0056b3;}
h2 { margin-top:0;}
.menu a { display:block; padding:10px; background:#007bff; color:white; text-decoration:none; margin:5px 0; border-radius:6px;}
.menu a:hover { background:#0056b3;}
.label { border:1px solid #000; width:300px; padding:5px; margin:5px;}
</style>
"""

# ================= LOGIN =================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["u"]
        p = request.form["p"]

        conn = sqlite3.connect("db.sqlite")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = u
            return redirect("/panel")

    return style + """
    <div class="container">
        <div class="card">
        <h2>Giriş</h2>
        <form method="post">
        <input name="u" placeholder="Kullanıcı">
        <input name="p" type="password" placeholder="Şifre">
        <button>Giriş</button>
        </form>
        </div>
    </div>
    """

# ================= PANEL =================
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    return style + """
    <div class="container">
        <div class="card">
        <h2>Panel</h2>
        <div class="menu">
            <a href="/add">➕ Ürün Ekle</a>
            <a href="/stock">📦 Stok İşlem</a>
            <a href="/labels">🖨 Etiket Bas</a>
        </div>
        </div>
    </div>
    """

# ================= ÜRÜN EKLE =================
@app.route("/add", methods=["GET","POST"])
def add():
    if request.method == "POST":
        data = (
            request.form["name"],
            request.form["type"],
            request.form["size"],
            request.form["unit"],
            request.form["class"],
            request.form["color"],
            request.form["barcode"]
        )

        conn = sqlite3.connect("db.sqlite")
        c = conn.cursor()
        c.execute("""INSERT INTO products 
        (name,type,size,unit,class,color,barcode)
        VALUES (?,?,?,?,?,?,?)""", data)
        conn.commit()
        conn.close()

        return redirect("/panel")

    return style + """
    <div class="container">
    <div class="card">
    <h2>Ürün Ekle</h2>
    <form method="post">
    <input name="name" placeholder="Ürün adı">
    <input name="type" placeholder="Cins">
    <input name="size" placeholder="Ebat">

    <select name="unit">
        <option>HG</option>
        <option>MAT</option>
    </select>

    <input name="class" placeholder="Sınıf">
    <input name="color" placeholder="Renk">
    <input name="barcode" placeholder="Barkod">

    <button>Kaydet</button>
    </form>
    </div>
    </div>
    """

# ================= STOK =================
depolar = [
"1.MDF SATIŞ DEPOSU",
"2.LAMİNANT DEPOSU",
"3.KAPI DEPOSU",
"4.HGLOSS DEPOSU (MORAYIN YANI)",
"5.SÜTÇÜ YANI DEPO",
"6.HELVACI YANI DEPO",
"7.RÖTBALANS YANI DEPO",
"8.KESİMHANE DEPOSU"
]

@app.route("/stock", methods=["GET","POST"])
def stock():
    if request.method == "POST":
        barcode = request.form["barcode"]
        depo = request.form["depo"]
        qty = int(request.form["qty"])

        conn = sqlite3.connect("db.sqlite")
        c = conn.cursor()

        c.execute("SELECT id,name FROM products WHERE barcode=?", (barcode,))
        p = c.fetchone()

        if not p:
            return "ÜRÜN YOK"

        pid, pname = p

        c.execute("SELECT id FROM stock WHERE product_id=? AND depo=?", (pid,depo))
        s = c.fetchone()

        if s:
            c.execute("UPDATE stock SET quantity=quantity+? WHERE id=?", (qty,s[0]))
        else:
            c.execute("INSERT INTO stock (product_id,depo,quantity) VALUES (?,?,?)",(pid,depo,qty))

        c.execute("""INSERT INTO logs 
        (user,action,product,depo,quantity,date)
        VALUES (?,?,?,?,?,?)""",
        (session["user"],"EKLE",pname,depo,qty,str(datetime.now())))

        conn.commit()
        conn.close()

        return redirect("/panel")

    options = "".join([f"<option>{d}</option>" for d in depolar])

    return style + f"""
    <div class="container">
    <div class="card">
    <h2>Stok İşlem</h2>
    <form method="post">
    <input name="barcode" placeholder="Barkod">

    <select name="depo">
    {options}
    </select>

    <input name="qty" placeholder="Adet">
    <button>Kaydet</button>
    </form>
    </div>
    </div>
    """

# ================= ETİKET =================
@app.route("/labels", methods=["GET","POST"])
def labels():
    if request.method == "POST":
        barcode = request.form["barcode"]
        count = int(request.form["count"])

        conn = sqlite3.connect("db.sqlite")
        c = conn.cursor()
        c.execute("SELECT * FROM products WHERE barcode=?", (barcode,))
        p = c.fetchone()
        conn.close()

        html = "<script>window.print()</script><div style='display:flex;flex-wrap:wrap;'>"

        for i in range(count):
            html += f"""
            <div class="label">
            <b>{p[1]}</b><br>
            {p[2]} / {p[3]}<br>
            {p[4]}<br>
            {p[5]}<br>
            {p[6]}<br>
            <b>{p[7]}</b>
            </div>
            """

        html += "</div>"
        return html

    return style + """
    <div class="container">
    <div class="card">
    <h2>Etiket Bas</h2>
    <form method="post">
    <input name="barcode" placeholder="Barkod">
    <input name="count" placeholder="Kaç adet">
    <button>Bas</button>
    </form>
    </div>
    </div>
    """

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
