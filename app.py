from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3, os, datetime
import barcode
from barcode.writer import ImageWriter
import qrcode

app = Flask(__name__)
app.secret_key = "secret123"

# 📁 klasörler
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
BARCODE_DIR = os.path.join(STATIC_DIR, "barcodes")
QR_DIR = os.path.join(STATIC_DIR, "qrcodes")

os.makedirs(BARCODE_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)

# 🏬 DEPOLAR
DEPOLAR = [
    "MDF SATIŞ DEPOSU",
    "LAMİNANT DEPOSU",
    "KAPI DEPOSU",
    "HGLOSS DEPOSU (MORAY YANI)",
    "SÜTÇÜ YANI",
    "HELVACI YANI",
    "RÖTBALANSÇI YANI",
    "KESİMHANE"
]

# 🧠 DB
def db():
    return sqlite3.connect("db.sqlite3")

def init_db():
    con = db()
    c = con.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY,
        name TEXT,
        type TEXT,
        size TEXT,
        quality TEXT,
        color TEXT,
        qty INTEGER,
        depo TEXT,
        barcode TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY,
        user TEXT,
        action TEXT,
        product TEXT,
        qty INTEGER,
        depo TEXT,
        time TEXT
    )""")

    con.commit()
    con.close()

init_db()

# 🔐 LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["user"]
        p = request.form["pass"]

        if u=="admin" and p=="123":
            session["user"]="admin"
            return redirect("/admin")
        elif u=="depocu" and p=="123":
            session["user"]="depocu"
            return redirect("/scan")
    return render_template("login.html")

# 👑 ADMIN PANEL
@app.route("/admin")
def admin():
    if session.get("user")!="admin":
        return redirect("/")
    con=db(); c=con.cursor()
    c.execute("SELECT * FROM products")
    data=c.fetchall()
    con.close()
    return render_template("admin.html", data=data, depolar=DEPOLAR)

# ➕ ÜRÜN EKLE
@app.route("/add", methods=["POST"])
def add():
    con=db(); c=con.cursor()

    name=request.form["name"]
    type_=request.form["type"]
    size=request.form["size"]
    quality=request.form["quality"]
    color=request.form["color"]
    qty=int(request.form["qty"])
    depo=request.form["depo"]

    code=str(int(datetime.datetime.now().timestamp()))

    # 📦 barkod
    b=barcode.get("code128", code, writer=ImageWriter())
    b.save(f"{BARCODE_DIR}/{code}")

    # 📱 qr
    img=qrcode.make(code)
    img.save(f"{QR_DIR}/{code}.png")

    c.execute("INSERT INTO products VALUES (NULL,?,?,?,?,?,?,?,?)",
              (name,type_,size,quality,color,qty,depo,code))

    con.commit(); con.close()
    return redirect("/admin")

# 📷 BARKOD OKUT
@app.route("/scan", methods=["GET","POST"])
def scan():
    if session.get("user")!="depocu":
        return redirect("/")

    if request.method=="POST":
        code=request.form["barcode"]

        con=db(); c=con.cursor()
        c.execute("SELECT * FROM products WHERE barcode=?",(code,))
        p=c.fetchone()
        con.close()

        if not p:
            return "❌ Ürün bulunamadı"

        return render_template("cikis.html", p=p)

    return render_template("scan.html")

# 🚚 ÇIKIŞ
@app.route("/cikis", methods=["POST"])
def cikis():
    if session.get("user")!="depocu":
        return redirect("/")

    code=request.form["barcode"]
    adet=int(request.form["adet"])

    con=db(); c=con.cursor()
    c.execute("SELECT qty,name,depo FROM products WHERE barcode=?",(code,))
    p=c.fetchone()

    if not p:
        return "Hata"

    yeni=p[0]-adet
    if yeni<0:
        return "❌ Stok yetersiz"

    c.execute("UPDATE products SET qty=? WHERE barcode=?",(yeni,code))

    # LOG
    c.execute("INSERT INTO logs VALUES(NULL,?,?,?,?,?,?)",
              ("depocu","ÇIKIŞ",p[1],adet,p[2],str(datetime.datetime.now())))

    con.commit(); con.close()

    return redirect("/scan")

# 📋 LOG
@app.route("/logs")
def logs():
    con=db(); c=con.cursor()
    c.execute("SELECT * FROM logs ORDER BY id DESC")
    data=c.fetchall()
    con.close()
    return render_template("logs.html", data=data)

app.run(debug=True)
