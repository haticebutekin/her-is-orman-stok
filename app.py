from flask import Flask, render_template_string, request, redirect, session, jsonify
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
        unit TEXT,      -- HG / MAT
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

    return """
    <h2>Giriş</h2>
    <form method="post">
    Kullanıcı: <input name="u"><br>
    Şifre: <input name="p" type="password"><br>
    <button>Giriş</button>
    </form>
    """

# ================= PANEL =================
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    return render_template_string("""
    <h2>Panel</h2>

    <a href="/add">➕ Ürün Ekle</a><br>
    <a href="/stock">📦 Stok İşlem</a><br>
    <a href="/labels">🖨 Etiket Bas</a><br>

    <hr>

    <video id="cam" width="300" autoplay></video><br>
    <button onclick="startCam()">📷 Kamera Aç</button>

    <script src="https://unpkg.com/html5-qrcode"></script>
    <script>
    function startCam(){
        const html5QrCode = new Html5Qrcode("cam");
        html5QrCode.start(
            { facingMode: "environment" },
            { fps: 10 },
            (decodedText) => {
                alert("Barkod: " + decodedText);
            }
        );
    }
    </script>
    """)

# ================= ÜRÜN EKLE =================
@app.route("/add", methods=["GET","POST"])
def add():
    if request.method == "POST":
        data = (
            request.form["name"],
            request.form["type"],
            request.form["size"],
            request.form["unit"],   # HG / MAT
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

        return "OK"

    return """
    <h2>Ürün Ekle</h2>
    <form method="post">
    Ad: <input name="name"><br>
    Cins: <input name="type"><br>
    Ebat: <input name="size"><br>

    Birim:
    <select name="unit">
        <option>HG</option>
        <option>MAT</option>
    </select><br>

    Sınıf: <input name="class"><br>
    Renk: <input name="color"><br>
    Barkod: <input name="barcode"><br>

    <button>Kaydet</button>
    </form>
    """

# ================= STOK =================
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

        c.execute("SELECT id,quantity FROM stock WHERE product_id=? AND depo=?", (pid,depo))
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

        return "OK"

    return """
    <h2>Stok</h2>
    <form method="post">
    Barkod: <input name="barcode"><br>
    Depo:
    <select name="depo">
        <option>Depo1</option>
        <option>Depo2</option>
        <option>Depo3</option>
        <option>Depo4</option>
        <option>Depo5</option>
        <option>Depo6</option>
        <option>Depo7</option>
        <option>Depo8</option>
    </select><br>

    Adet: <input name="qty"><br>
    <button>Kaydet</button>
    </form>
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

        if not p:
            return "ÜRÜN YOK"

        html = "<script>window.print()</script>"

        for i in range(count):
            html += f"""
            <div style="border:1px solid #000; width:300px; margin:5px; padding:5px;">
            <b>{p[1]}</b><br>
            {p[2]} / {p[3]}<br>
            {p[4]}<br>
            {p[5]}<br>
            {p[6]}<br>
            <b>{p[7]}</b>
            </div>
            """

        return html

    return """
    <h2>Etiket</h2>
    <form method="post">
    Barkod: <input name="barcode"><br>
    Kaç Adet: <input name="count"><br>
    <button>Bas</button>
    </form>
    """

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
