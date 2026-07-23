from flask import Flask, render_template_string, request, redirect, session
import sqlite3, random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# ================= DB =================
def db():
    return sqlite3.connect("db.sqlite")

def init():
    conn = db()
    c = conn.cursor()

    c.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT,password TEXT)")
    c.execute("""CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY,
    name TEXT,type TEXT,size TEXT,unit TEXT,class TEXT,color TEXT,
    barcode TEXT UNIQUE,min_stock INTEGER)""")
    c.execute("CREATE TABLE IF NOT EXISTS stock(id INTEGER PRIMARY KEY,product_id INTEGER,depo TEXT,quantity INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY,user TEXT,action TEXT,product TEXT,depo TEXT,qty INTEGER,date TEXT)")

    c.execute("INSERT OR IGNORE INTO users VALUES (1,'admin','1234')")
    conn.commit()
    conn.close()

init()

# ================= BARKOD =================
def generate_barcode():
    conn = db()
    c = conn.cursor()
    while True:
        code = "869" + "".join([str(random.randint(0,9)) for _ in range(9)])
        c.execute("SELECT * FROM products WHERE barcode=?", (code,))
        if not c.fetchone():
            return code

# ================= STYLE =================
style = """
<style>
body {font-family:Arial;background:#f4f6f9;margin:0;}
.container {max-width:1200px;margin:auto;padding:20px;}
.card {background:white;padding:20px;border-radius:10px;margin-bottom:20px;box-shadow:0 5px 15px rgba(0,0,0,0.1);}
input,select,button {padding:10px;margin:5px;border-radius:6px;border:1px solid #ccc;}
button {background:#007bff;color:white;border:none;}
.menu a {display:block;background:#007bff;color:white;padding:10px;margin:5px 0;text-decoration:none;border-radius:6px;}
table {width:100%;border-collapse:collapse;}
th,td {padding:10px;border-bottom:1px solid #ddd;}
th {background:#007bff;color:white;}
.label {border:1px solid #000;width:280px;padding:5px;margin:5px;display:inline-block;}
</style>
"""

depolar = [
"1.MDF SATIŞ DEPOSU",
"2.LAMİNANT DEPOSU",
"3.KAPI DEPOSU",
"4.HGLOSS DEPOSU (MORAY YANI)",
"5.SÜTÇÜ YANI DEPO",
"6.HELVACI YANI DEPO",
"7.RÖTBALANS YANI DEPO",
"8.KESİMHANE DEPOSU"
]

# ================= LOGIN =================
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["u"]
        p = request.form["p"]

        c = db().cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        if c.fetchone():
            session["user"] = u
            return redirect("/panel")

    return style + """
    <div class=container><div class=card>
    <h2>Giriş</h2>
    <form method=post>
    <input name=u placeholder=Kullanıcı>
    <input name=p type=password placeholder=Şifre>
    <button>Giriş</button>
    </form></div></div>
    """

# ================= PANEL =================
@app.route("/panel")
def panel():
    if "user" not in session: return redirect("/")
    return style + """
    <div class=container><div class=card>
    <h2>Panel</h2>
    <div class=menu>
    <a href=/add>➕ Ürün</a>
    <a href=/stock_in>📥 Stok Giriş</a>
    <a href=/stock_out>📤 Stok Çıkış</a>
    <a href=/list>📊 Stok</a>
    <a href=/labels>🖨 Etiket</a>
    </div></div></div>
    """

# ================= ÜRÜN =================
@app.route("/add", methods=["GET","POST"])
def add():
    if request.method == "POST":
        barcode = request.form["barcode"]
        if barcode == "":
            barcode = generate_barcode()

        data = (
            request.form["name"],
            request.form["type"],
            request.form["size"],
            request.form["unit"],
            request.form["class"],
            request.form["color"],
            barcode,
            request.form["min"]
        )

        conn = db()
        c = conn.cursor()
        c.execute("INSERT INTO products(name,type,size,unit,class,color,barcode,min_stock) VALUES (?,?,?,?,?,?,?,?)", data)
        conn.commit()

        return redirect("/labels?b="+barcode)

    return style + """
    <div class=container><div class=card>
    <h2>Ürün</h2>
    <form method=post>
    <input name=name placeholder=Ad>
    <input name=type placeholder=Cins>
    <input name=size placeholder=Ebat>
    <select name=unit><option>HG</option><option>MAT</option></select>
    <input name=class placeholder=Sınıf>
    <input name=color placeholder=Renk>
    <input name=barcode placeholder="Boş bırak otomatik barkod">
    <input name=min placeholder="Min stok">
    <button>Kaydet</button>
    </form></div></div>
    """

# ================= STOK =================
@app.route("/stock_in", methods=["GET","POST"])
def stock_in():
    if request.method == "POST":
        b = request.form["barcode"]
        d = request.form["depo"]
        q = int(request.form["qty"])

        conn = db()
        c = conn.cursor()
        c.execute("SELECT id,name FROM products WHERE barcode=?", (b,))
        p = c.fetchone()

        if not p: return "ÜRÜN YOK"
        pid,name = p

        c.execute("SELECT id FROM stock WHERE product_id=? AND depo=?", (pid,d))
        s = c.fetchone()

        if s:
            c.execute("UPDATE stock SET quantity=quantity+? WHERE id=?", (q,s[0]))
        else:
            c.execute("INSERT INTO stock(product_id,depo,quantity) VALUES (?,?,?)",(pid,d,q))

        c.execute("INSERT INTO logs(user,action,product,depo,qty,date) VALUES (?,?,?,?,?,?)",
                  (session["user"],"GİRİŞ",name,d,q,str(datetime.now())))

        conn.commit()
        return redirect("/list")

    ops = "".join([f"<option>{x}</option>" for x in depolar])

    return style + f"""
    <div class=container><div class=card>
    <h2>Stok Giriş</h2>

    <button onclick="start()">📷 Kamera</button>
    <div id="reader"></div>

    <form method=post>
    <input id=barcode name=barcode placeholder=Barkod>
    <select name=depo>{ops}</select>
    <input name=qty placeholder=Adet>
    <button>Kaydet</button>
    </form>

    <script src="https://unpkg.com/html5-qrcode"></script>
    <script>
    function start(){
        const html5QrCode = new Html5Qrcode("reader");
        html5QrCode.start({facingMode:"environment"},{{fps:10}},(txt)=>{
            document.getElementById("barcode").value=txt;
        });
    }
    </script>

    </div></div>
    """

# ================= STOK LİSTE =================
@app.route("/list")
def list_page():
    q = request.args.get("q","")

    conn = db()
    c = conn.cursor()
    c.execute("""
    SELECT p.name,p.barcode,s.depo,s.quantity
    FROM stock s JOIN products p ON p.id=s.product_id
    WHERE p.name LIKE ? OR p.barcode LIKE ?
    """,(f"%{q}%",f"%{q}%"))

    data = c.fetchall()

    rows = ""
    for d in data:
        rows += f"<tr><td>{d[0]}</td><td>{d[1]}</td><td>{d[2]}</td><td>{d[3]}</td></tr>"

    return style + f"""
    <div class=container><div class=card>
    <h2>Stok</h2>
    <form><input name=q placeholder=Ara value="{q}"></form>
    <table>
    <tr><th>Ürün</th><th>Barkod</th><th>Depo</th><th>Adet</th></tr>
    {rows}
    </table>
    </div></div>
    """

# ================= ETİKET =================
@app.route("/labels")
def labels():
    b = request.args.get("b")

    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE barcode=?", (b,))
    p = c.fetchone()

    html = "<script>window.print()</script>"

    html += f"""
    <div class=label>
    <b>{p[1]}</b><br>
    {p[2]} / {p[3]}<br>
    {p[4]}<br>
    {p[5]}<br>
    {p[6]}<br>
    <img src="https://barcode.tec-it.com/barcode.ashx?data={p[7]}&code=EAN13"><br>
    {p[7]}
    </div>
    """

    return html

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
