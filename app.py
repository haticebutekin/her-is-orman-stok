from flask import Flask, request, redirect, session
import sqlite3, uuid, datetime

app = Flask(__name__)
app.secret_key = "123"

# VERİTABANI
def db():
    return sqlite3.connect("db.sqlite3")

def kur():
    conn=db(); c=conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    username TEXT,
    password TEXT,
    role TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY,
    name TEXT,
    type TEXT,
    size TEXT,
    class TEXT,
    color TEXT,
    adet INTEGER,
    depo TEXT,
    barcode TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS hareket(
    id INTEGER PRIMARY KEY,
    user TEXT,
    islem TEXT,
    urun TEXT,
    adet INTEGER,
    depo TEXT,
    saat TEXT)""")

    # default kullanıcılar
    if not c.execute("SELECT * FROM users").fetchone():
        c.execute("INSERT INTO users VALUES(NULL,'admin','123','yonetici')")
        c.execute("INSERT INTO users VALUES(NULL,'depocu','123','depocu')")

    conn.commit(); conn.close()

kur()

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

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=request.form["u"]; p=request.form["p"]
        conn=db(); c=conn.cursor()
        user=c.execute("SELECT * FROM users WHERE username=? AND password=?",(u,p)).fetchone()
        conn.close()

        if user:
            session["user"]=u
            session["role"]=user[3]
            return redirect("/panel")
        return "Hatalı giriş"

    return """
    <h2>Giriş</h2>
    <form method=post>
    Kullanıcı<input name=u><br>
    Şifre<input type=password name=p><br>
    <button>GİR</button>
    </form>
    """

# PANEL
@app.route("/panel")
def panel():
    if "user" not in session: return redirect("/")
    return """
    <h2>PANEL</h2>
    <a href='/ekle'>ÜRÜN EKLE</a><br><br>
    <a href='/okut'>BARKOD ÇIKIŞ</a><br><br>
    <a href='/kamera'>KAMERA OKUT</a><br><br>
    <a href='/liste'>STOK LİSTE</a><br><br>
    <a href='/hareket'>HAREKET</a>
    """

# ÜRÜN EKLE
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if session.get("role")!="yonetici": return "Yetki yok"

    if request.method=="POST":
        data = (
            request.form["name"],
            request.form["type"],
            request.form["size"],
            request.form["class"],
            request.form["color"],
            int(request.form["adet"]),
            request.form["depo"],
            str(uuid.uuid4())[:12]
        )
        conn=db(); c=conn.cursor()
        c.execute("INSERT INTO products VALUES(NULL,?,?,?,?,?,?,?,?)",data)
        conn.commit(); conn.close()
        return "✅ EKLENDİ <br><a href='/panel'>Geri</a>"

    depo_options = "".join([f"<option>{d}</option>" for d in DEPOLAR])

    return f"""
    <h2>ÜRÜN EKLE</h2>
    <form method=post>
    Ad<input name=name><br>
    Cins<input name=type><br>
    Ebat<input name=size><br>
    HG/MAT<input name=class><br>
    Renk<input name=color><br>
    Adet<input name=adet><br>
    Depo<select name=depo>{depo_options}</select><br>
    <button>EKLE</button>
    </form>
    """

# STOK
@app.route("/liste")
def liste():
    conn=db(); c=conn.cursor()
    data=c.execute("SELECT * FROM products").fetchall()
    conn.close()

    html="<h2>STOK</h2>"
    for i in data:
        html+=f"{i[1]} | {i[6]} adet | {i[7]} | Barkod:{i[8]}<br>"
    return html

# BARKOD OKUT
@app.route("/okut", methods=["GET","POST"])
def okut():
    if session.get("role")!="depocu": return "Yetki yok"

    barkod = request.args.get("barkod")

    if request.method=="POST" or barkod:
        if not barkod:
            barkod=request.form["barkod"]

        adet=int(request.form.get("adet",1))

        conn=db(); c=conn.cursor()
        u=c.execute("SELECT * FROM products WHERE barcode=?",(barkod,)).fetchone()

        if not u:
            conn.close()
            return "❌ Ürün yok"

        if u[6] < adet:
            conn.close()
            return "❌ Stok yetersiz"

        yeni = u[6] - adet

        c.execute("UPDATE products SET adet=? WHERE barcode=?",(yeni,barkod))

        c.execute("INSERT INTO hareket VALUES(NULL,?,?,?,?,?,?)",
        (session["user"],"ÇIKIŞ",u[1],adet,u[7],datetime.datetime.now().strftime("%H:%M:%S")))

        conn.commit(); conn.close()

        return f"✅ {u[1]} çıkış yapıldı | Kalan:{yeni}"

    return """
    <h2>BARKOD ÇIKIŞ</h2>
    <form method=post>
    Barkod<input name=barkod><br>
    Adet<input name=adet value=1><br>
    <button>ÇIKIŞ</button>
    </form>
    """

# KAMERA
@app.route("/kamera")
def kamera():
    return """
    <h2>KAMERA OKUT</h2>
    <script src="https://unpkg.com/html5-qrcode"></script>
    <div id="reader" style="width:300px;"></div>

    <script>
    function onScanSuccess(decodedText) {
        window.location = "/okut?barkod=" + decodedText;
    }
    new Html5QrcodeScanner("reader", {fps:10}).render(onScanSuccess);
    </script>
    """

# HAREKET
@app.route("/hareket")
def hareket():
    conn=db(); c=conn.cursor()
    data=c.execute("SELECT * FROM hareket ORDER BY id DESC").fetchall()
    conn.close()

    html="<h2>HAREKET</h2>"
    for i in data:
        html+=f"{i[1]} | {i[2]} | {i[3]} | {i[4]} | {i[5]} | {i[6]}<br>"
    return html

# RUN
if __name__ == "__main__":
    app.run(debug=True)
