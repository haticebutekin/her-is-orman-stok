from flask import Flask, render_template_string, request, redirect, session, jsonify
import sqlite3
import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# ------------------ DATABASE ------------------
def db():
    return sqlite3.connect("market.db")

def init_db():
    conn = db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        barcode TEXT,
        stock INTEGER,
        price REAL,
        type TEXT,
        size TEXT,
        class TEXT,
        color TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        total REAL,
        date TEXT
    )
    """)

    # default user
    c.execute("SELECT * FROM users")
    if not c.fetchone():
        c.execute("INSERT INTO users (username,password) VALUES ('admin','1234')")

    conn.commit()
    conn.close()

init_db()

# ------------------ LOGIN ------------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = db()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = u
            return redirect("/panel")

    return render_template_string("""
    <h2>Giriş</h2>
    <form method="post">
    <input name="username" placeholder="Kullanıcı"><br>
    <input name="password" type="password" placeholder="Şifre"><br>
    <button>Giriş</button>
    </form>
    """)

# ------------------ PANEL ------------------
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")

    return render_template_string("""
    <h2>Panel</h2>

    <a href="/urun">Ürün Ekle</a><br>
    <a href="/satis">Satış</a><br>
    <a href="/liste">Ürün Liste</a>
    """)

# ------------------ ÜRÜN EKLE ------------------
@app.route("/urun", methods=["GET","POST"])
def urun():
    if request.method == "POST":
        data = (
            request.form["name"],
            request.form["barcode"],
            request.form["stock"],
            request.form["price"],
            request.form["type"],
            request.form["size"],
            request.form["class"],
            request.form["color"]
        )

        conn = db()
        c = conn.cursor()
        c.execute("""
        INSERT INTO products 
        (name,barcode,stock,price,type,size,class,color)
        VALUES (?,?,?,?,?,?,?,?)
        """, data)

        conn.commit()
        conn.close()

    return render_template_string("""
    <h2>Ürün Ekle</h2>

    <form method="post">
    İsim <input name="name"><br>
    Barkod <input name="barcode" id="barcode"><br>
    Stok <input name="stock"><br>
    Fiyat <input name="price"><br>

    Cins <input name="type"><br>
    Ebat <input name="size"><br>
    Sınıf <input name="class"><br>
    Renk <input name="color"><br>

    <button>Kaydet</button>
    </form>

    <br>
    <button onclick="scan()">📷 Barkod Oku</button>

    <script src="https://unpkg.com/html5-qrcode"></script>
    <div id="reader" style="width:300px"></div>

    <script>
    function scan(){
        const qr = new Html5Qrcode("reader");
        qr.start(
            { facingMode: "environment" },
            { fps: 10, qrbox: 250 },
            (code) => {
                document.getElementById("barcode").value = code;
                qr.stop();
            }
        );
    }
    </script>
    """)

# ------------------ ÜRÜN LİSTE ------------------
@app.route("/liste")
def liste():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM products")
    data = c.fetchall()
    conn.close()

    html = "<h2>Ürünler</h2>"

    for d in data:
        html += f"""
        <div>
        {d[1]} | {d[2]} | {d[3]} adet | {d[4]} TL
        </div>
        """

    return html

# ------------------ SATIŞ ------------------
@app.route("/satis")
def satis():
    return render_template_string("""
    <h2>Satış</h2>

    Barkod: <input id="b"><button onclick="ekle()">Ekle</button>

    <ul id="list"></ul>
    <h3 id="toplam">0 TL</h3>

    <button onclick="scan()">📷 Oku</button>

    <script src="https://unpkg.com/html5-qrcode"></script>

    <script>
    let toplam = 0;

    function ekle(){
        let b = document.getElementById("b").value;

        fetch("/get/"+b)
        .then(r=>r.json())
        .then(d=>{
            let li = document.createElement("li");
            li.innerText = d.name + " - " + d.price;
            document.getElementById("list").appendChild(li);

            toplam += d.price;
            document.getElementById("toplam").innerText = toplam + " TL";
        });
    }

    function scan(){
        const qr = new Html5Qrcode("reader");
        qr.start(
            { facingMode: "environment" },
            { fps: 10, qrbox: 250 },
            (code) => {
                document.getElementById("b").value = code;
                ekle();
                qr.stop();
            }
        );
    }
    </script>

    <div id="reader" style="width:300px"></div>
    """)

# ------------------ API ------------------
@app.route("/get/<barcode>")
def get_product(barcode):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT name,price FROM products WHERE barcode=?", (barcode,))
    p = c.fetchone()
    conn.close()

    if p:
        return jsonify({"name":p[0],"price":p[1]})
    return jsonify({"name":"YOK","price":0})

# ------------------
if __name__ == "__main__":
    app.run(debug=True)
