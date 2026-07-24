from flask import Flask, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DB ----------------
def get_db():
    return sqlite3.connect("database.db")

def init_db():
    db = get_db()
    c = db.cursor()

    # ürün tablosu
    c.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barcode TEXT,
        name TEXT,
        type TEXT,
        size TEXT,
        quality TEXT,
        surface TEXT,
        color TEXT,
        stock INTEGER,
        depot TEXT
    )
    """)

    # kullanıcı
    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        username TEXT,
        password TEXT,
        role TEXT
    )
    """)

    # log
    c.execute("""
    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        action TEXT,
        time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # default kullanıcı
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
    <h2>Giriş</h2>
    <form method="post">
        Kullanıcı: <input name="username"><br>
        Şifre: <input name="password" type="password"><br>
        <button>Giriş</button>
    </form>
    '''

# ---------------- PANEL ----------------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    html = f"<h2>Hoşgeldin {session['user']}</h2>"
    html += "<a href='/urunler'>Ürünler</a><br>"
    html += "<a href='/barkod'>📷 Barkod Oku</a><br>"

    if session["role"] == "admin":
        html += "<a href='/ekle'>Ürün Ekle</a><br>"
        html += "<a href='/kullanicilar'>Kullanıcılar</a><br>"
        html += "<a href='/loglar'>📊 Loglar</a><br>"

    html += "<a href='/logout'>Çıkış</a>"

    return html

# ---------------- ÜRÜN EKLE ----------------
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if session.get("role") != "admin":
        return "Yetkin yok!"

    if request.method == "POST":
        db = get_db()
        c = db.cursor()

        c.execute("INSERT INTO products VALUES (NULL,?,?,?,?,?,?,?,?,?)", (
            request.form["barcode"],
            request.form["name"],
            request.form["type"],
            request.form["size"],
            request.form["quality"],
            request.form["surface"],
            request.form["color"],
            request.form["stock"],
            request.form["depot"]
        ))

        db.commit()

        log_yaz(session["user"], f"Ürün ekledi: {request.form['name']}")

        return redirect("/urunler")

    return '''
    <h2>Ürün Ekle</h2>
    <form method="post">
        Barkod: <input name="barcode"><br>
        Ad: <input name="name"><br>
        Tip: <input name="type"><br>
        Ebat: <input name="size"><br>
        Kalite: <input name="quality"><br>
        Yüzey: <input name="surface"><br>
        Renk: <input name="color"><br>
        Stok: <input name="stock"><br>
        Depo: <input name="depot"><br>
        <button>Kaydet</button>
    </form>
    '''

# ---------------- ÜRÜNLER ----------------
@app.route("/urunler")
def urunler():
    if "user" not in session:
        return redirect("/")

    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM products")
    data = c.fetchall()

    log_yaz(session["user"], "Ürünleri görüntüledi")

    html = "<h2>Ürünler</h2>"

    for i in data:
        html += f"{i[2]} | Barkod: {i[1]} | Stok: {i[8]}<br>"

    html += "<br><a href='/panel'>Geri</a>"
    return html

# ---------------- BARKOD ----------------
@app.route("/barkod")
def barkod():
    return """
    <h2>Barkod Oku</h2>

    <div id="reader" style="width:300px;"></div>
    <p id="result"></p>

    <script src="https://unpkg.com/html5-qrcode"></script>

    <script>
    function onScanSuccess(decodedText) {
        document.getElementById("result").innerText = "OKUNDU: " + decodedText;

        fetch("/log_barkod?data=" + decodedText)
        .then(r=>r.text())
        .then(t=>alert(t));
    }

    let scanner = new Html5QrcodeScanner("reader", { fps: 10, qrbox: 250 });
    scanner.render(onScanSuccess);
    </script>
    """

# ---------------- BARKOD → SATIŞ ----------------
@app.route("/log_barkod")
def log_barkod():
    data = request.args.get("data")

    db = get_db()
    c = db.cursor()

    c.execute("SELECT * FROM products WHERE barcode=?", (data,))
    product = c.fetchone()

    if not product:
        log_yaz(session["user"], f"Ürün yok: {data}")
        return "ÜRÜN BULUNAMADI ❌"

    stock = product[8]

    if stock <= 0:
        log_yaz(session["user"], f"Stok yok: {product[2]}")
        return f"STOK YOK ❌ ({product[2]})"

    new_stock = stock - 1
    c.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, product[0]))
    db.commit()

    log_yaz(session["user"], f"SATIŞ: {product[2]} | Kalan: {new_stock}")

    return f"SATILDI ✅ {product[2]} | Kalan stok: {new_stock}"

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

        log_yaz(session["user"], f"Kullanıcı ekledi: {request.form['username']}")

    c.execute("SELECT * FROM users")
    users = c.fetchall()

    html = "<h2>Kullanıcılar</h2>"

    for u in users:
        html += f"{u[0]} ({u[2]})<br>"

    html += '''
    <h3>Ekle</h3>
    <form method="post">
        Kullanıcı: <input name="username"><br>
        Şifre: <input name="password"><br>
        Rol:
        <select name="role">
            <option>admin</option>
            <option>personel</option>
        </select><br>
        <button>Ekle</button>
    </form>
    '''

    return html

# ---------------- LOGLAR ----------------
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

    html += "<br><a href='/panel'>Geri</a>"
    return html

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()
