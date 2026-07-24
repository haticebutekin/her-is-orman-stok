from flask import Flask, request, redirect, session, send_file
import sqlite3, io, base64, random, string
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DB ----------------
def get_db():
    return sqlite3.connect("database.db")

def init_db():
    db = get_db()
    c = db.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode TEXT,
        name TEXT,
        stock INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        username TEXT,
        password TEXT,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        action TEXT,
        time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("SELECT * FROM users")
    if not c.fetchall():
        c.execute("INSERT INTO users VALUES ('admin','1234','admin')")
        c.execute("INSERT INTO users VALUES ('personel','1234','personel')")

    db.commit()

init_db()

# ---------------- LOG ----------------
def log_yaz(user, action):
    db = get_db()
    c = db.cursor()
    c.execute("INSERT INTO logs (user, action) VALUES (?,?)", (user, action))
    db.commit()

# ---------------- BARKOD ÜRET ----------------
def generate_barcode():
    return ''.join(random.choices(string.digits, k=12))

def barcode_image(code):
    EAN = barcode.get_barcode_class('code128')
    rv = io.BytesIO()
    EAN(code, writer=ImageWriter()).write(rv)
    rv.seek(0)
    return rv

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        db = get_db()
        c = db.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?",
                  (request.form["username"], request.form["password"]))
        user = c.fetchone()

        if user:
            session["user"] = user[0]
            session["role"] = user[2]
            log_yaz(user[0], "Giriş yaptı")
            return redirect("/panel")

    return '''
    <style>
    body{font-family:sans-serif; text-align:center; margin-top:50px}
    input,button{padding:10px; margin:5px}
    </style>
    <h2>Giriş</h2>
    <form method="post">
        <input name="username" placeholder="Kullanıcı"><br>
        <input name="password" type="password" placeholder="Şifre"><br>
        <button>Giriş</button>
    </form>
    '''

# ---------------- PANEL ----------------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    html = f"<h2>👋 {session['user']}</h2>"
    html += "<a href='/barkod'>📷 Okut & Satış</a><br>"

    if session["role"] == "admin":
        html += "<a href='/ekle'>➕ Ürün Ekle</a><br>"
        html += "<a href='/urunler'>📦 Ürünler</a><br>"
        html += "<a href='/kullanicilar'>👥 Kullanıcı</a><br>"
        html += "<a href='/loglar'>📊 Loglar</a><br>"

    html += "<a href='/logout'>Çıkış</a>"
    return html

# ---------------- ÜRÜN EKLE ----------------
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if session.get("role") != "admin":
        return "Yetkin yok!"

    if request.method == "POST":
        code = generate_barcode()

        db = get_db()
        c = db.cursor()
        c.execute("INSERT INTO products VALUES (NULL,?,?,?)", (
            code,
            request.form["name"],
            request.form["stock"]
        ))
        db.commit()

        log_yaz(session["user"], f"Ürün eklendi: {request.form['name']}")

        return f"""
        <h3>Ürün eklendi</h3>
        Barkod: {code}<br><br>
        <img src="/barcode/{code}"><br><br>
        <button onclick="window.print()">🖨 Yazdır</button><br>
        <a href='/panel'>Geri</a>
        """

    return '''
    <h2>Ürün Ekle</h2>
    <form method="post">
        Ad: <input name="name"><br>
        Stok: <input name="stock"><br>
        <button>Kaydet</button>
    </form>
    '''

# ---------------- BARKOD GÖRSEL ----------------
@app.route("/barcode/<code>")
def barcode_view(code):
    return send_file(barcode_image(code), mimetype="image/png")

# ---------------- ÜRÜNLER ----------------
@app.route("/urunler")
def urunler():
    if session.get("role") != "admin":
        return "Yetkin yok!"

    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM products")
    data = c.fetchall()

    html = "<h2>Ürünler</h2>"
    for i in data:
        html += f"""
        {i[2]} | Stok: {i[3]} 
        <a href='/barcode/{i[1]}' target='_blank'>🧾 Etiket</a><br>
        """

    return html

# ---------------- BARKOD OKUMA ----------------
@app.route("/barkod")
def barkod():
    return """
    <h2>📷 Okut</h2>
    <div id="reader" style="width:300px;"></div>

    <script src="https://unpkg.com/html5-qrcode"></script>
    <script>
    function onScanSuccess(code) {
        fetch("/sat?code=" + code)
        .then(r=>r.text())
        .then(alert);
    }

    new Html5QrcodeScanner("reader",{fps:10,qrbox:250})
    .render(onScanSuccess);
    </script>
    """

# ---------------- SATIŞ / DÜŞÜM ----------------
@app.route("/sat")
def sat():
    if "user" not in session:
        return "Giriş yok"

    code = request.args.get("code")

    db = get_db()
    c = db.cursor()

    c.execute("SELECT * FROM products WHERE barcode=?", (code,))
    p = c.fetchone()

    if not p:
        return "Ürün yok"

    if p[3] <= 0:
        return "Stok yok"

    new_stock = p[3] - 1
    c.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, p[0]))
    db.commit()

    log_yaz(session["user"], f"Düşüm: {p[2]} | Kalan:{new_stock}")

    return f"{p[2]} satıldı. Kalan: {new_stock}"

# ---------------- KULLANICI ----------------
@app.route("/kullanicilar", methods=["GET","POST"])
def kullanicilar():
    if session.get("role") != "admin":
        return "Yetkin yok!"

    db = get_db()
    c = db.cursor()

    if request.method == "POST":
        c.execute("INSERT INTO users VALUES (?,?,?)", (
            request.form["username"],
            request.form["password"],
            request.form["role"]
        ))
        db.commit()

    c.execute("SELECT * FROM users")
    users = c.fetchall()

    html = "<h2>Kullanıcılar</h2>"
    for u in users:
        html += f"{u[0]} ({u[2]})<br>"

    html += '''
    <form method="post">
        <input name="username" placeholder="kullanıcı"><br>
        <input name="password" placeholder="şifre"><br>
        <select name="role">
            <option>admin</option>
            <option>personel</option>
        </select><br>
        <button>Ekle</button>
    </form>
    '''
    return html

# ---------------- LOG ----------------
@app.route("/loglar")
def loglar():
    if session.get("role") != "admin":
        return "Yetkin yok!"

    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM logs ORDER BY id DESC")
    logs = c.fetchall()

    html = "<h2>Loglar</h2>"
    for l in logs:
        html += f"{l[3]} | {l[1]} → {l[2]}<br>"

    return html

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    app.run()
