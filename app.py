from flask import Flask, request, redirect, session, render_template_string
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
def get_db():
    return sqlite3.connect("market.db")

def init_db():
    db = get_db()
    c = db.cursor()

    # USERS (ROL SİSTEMİ)
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    # PRODUCTS (FULL DETAY)
    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        type TEXT,
        size INTEGER,
        quality TEXT,
        surface TEXT,
        color TEXT,
        stock INTEGER,
        depot TEXT
    )
    """)

    # DEFAULT USERS
    c.execute("SELECT * FROM users")
    if not c.fetchall():
        c.execute("INSERT INTO users VALUES (NULL,'admin','1234','admin')")
        c.execute("INSERT INTO users VALUES (NULL,'personel','1234','staff')")

    db.commit()
    db.close()

init_db()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        db = get_db()
        c = db.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        user = c.fetchone()

        if user:
            session["user"] = user[1]
            session["role"] = user[3]
            return redirect("/panel")

    return render_template_string("""
    <h2>Giriş</h2>
    <form method="post">
        Kullanıcı: <input name="username"><br>
        Şifre: <input name="password"><br>
        <button>Giriş</button>
    </form>
    """)

# ---------------- PANEL ----------------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    return render_template_string("""
    <h1>Hoşgeldin {{user}}</h1>
    <p>Rol: {{role}}</p>

    <a href="/urunler">Ürünler</a><br>
    <a href="/ekle">Ürün Ekle</a><br>

    {% if role == "admin" %}
        <a href="/kullanicilar">Kullanıcı Yönetimi</a><br>
    {% endif %}

    <a href="/logout">Çıkış</a>
    """, user=session["user"], role=session["role"])

# ---------------- ÜRÜN LİSTE ----------------
@app.route("/urunler")
def urunler():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM products")
    data = c.fetchall()

    html = "<h2>Ürünler</h2>"
    html += "<table border=1><tr><th>Adı</th><th>Cinsi</th><th>MM</th><th>Sınıf</th><th>Yüzey</th><th>Renk</th><th>Stok</th><th>Depo</th></tr>"

    for d in data:
        html += f"<tr><td>{d[1]}</td><td>{d[2]}</td><td>{d[3]}</td><td>{d[4]}</td><td>{d[5]}</td><td>{d[6]}</td><td>{d[7]}</td><td>{d[8]}</td></tr>"

    html += "</table><br><a href='/panel'>Geri</a>"
    return html

# ---------------- ÜRÜN EKLE ----------------
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        name = request.form["name"]
        type_ = request.form["type"]
        size = request.form["size"]
        quality = request.form["quality"]
        surface = request.form["surface"]
        color = request.form["color"]
        stock = request.form["stock"]
        depot = request.form["depot"]

        db = get_db()
        c = db.cursor()
        c.execute("INSERT INTO products VALUES (NULL,?,?,?,?,?,?,?,?)",
                  (name,type_,size,quality,surface,color,stock,depot))
        db.commit()

    return render_template_string("""
    <h2>Ürün Ekle</h2>
    <form method="post">
        Adı: <input name="name"><br>
        Cinsi: <input name="type"><br>
        Kaç MM: <input name="size"><br>
        Sınıf: <input name="quality"><br>
        HGLOSS / MAT: <input name="surface"><br>
        Renk: <input name="color"><br>
        Stok: <input name="stock"><br>

        Depo:
        <select name="depot">
            <option>MDF SATIŞ DEPOSU</option>
            <option>LAMİNANT DEPOSU</option>
            <option>KAPI DEPOSU</option>
            <option>HGLOSS DEPOSU</option>
            <option>SÜTÇÜ YANI</option>
            <option>HELVACI YANI</option>
            <option>RÖTBALANSÇI YANI</option>
            <option>KESİMHANE</option>
        </select><br>

        <button>Kaydet</button>
    </form>
    <a href="/panel">Geri</a>
    """)

# ---------------- KULLANICI YÖNETİMİ ----------------
@app.route("/kullanicilar", methods=["GET","POST"])
def kullanicilar():
    if session.get("role") != "admin":
        return "Yetkisiz!"

    db = get_db()
    c = db.cursor()

    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]
        r = request.form["role"]
        c.execute("INSERT INTO users VALUES (NULL,?,?,?)", (u,p,r))
        db.commit()

    c.execute("SELECT * FROM users")
    users = c.fetchall()

    html = "<h2>Kullanıcılar</h2>"
    for u in users:
        html += f"{u[1]} - {u[3]}<br>"

    html += """
    <h3>Yeni Kullanıcı</h3>
    <form method="post">
        Kullanıcı: <input name="username"><br>
        Şifre: <input name="password"><br>
        Rol:
        <select name="role">
            <option>admin</option>
            <option>staff</option>
        </select><br>
        <button>Ekle</button>
    </form>
    <a href='/panel'>Geri</a>
    """

    return html

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
