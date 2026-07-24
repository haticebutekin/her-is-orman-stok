from flask import Flask, request, redirect, render_template_string, send_file, session
import sqlite3, uuid, io, datetime
import barcode
from barcode.writer import ImageWriter
import qrcode
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
def db():
    return sqlite3.connect("db.sqlite3")

def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS urunler(
        id INTEGER PRIMARY KEY,
        ad TEXT,
        cins TEXT,
        ebat TEXT,
        sinif TEXT,
        renk TEXT,
        adet INTEGER,
        depo TEXT,
        barkod TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS log(
        id INTEGER PRIMARY KEY,
        user TEXT,
        islem TEXT,
        urun TEXT,
        depo TEXT,
        adet INTEGER,
        tarih TEXT
    )""")

    con.commit()
    con.close()

init_db()

# ---------------- SABİT DEPOLAR ----------------
DEPOLAR = [
    "MDF SATIŞ",
    "LAMİNANT",
    "KAPI",
    "HGLOSS (MORAY)",
    "SÜTÇÜ",
    "HELVACI",
    "RÖTBALANSÇI",
    "KESİMHANE"
]

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = request.form["user"]
        if user == "admin":
            session["role"] = "admin"
        else:
            session["role"] = "depocu"
        session["user"] = user
        return redirect("/")
    return """
    <h2>Giriş</h2>
    <form method="POST">
    Kullanıcı: <input name="user">
    <button>Giriş</button>
    </form>
    """

# ---------------- ANA SAYFA ----------------
@app.route("/", methods=["GET","POST"])
def index():
    if "role" not in session:
        return redirect("/login")

    con = db()
    cur = con.cursor()

    if request.method == "POST" and session["role"]=="admin":
        barkod_no = str(uuid.uuid4())[:8]

        cur.execute("INSERT INTO urunler(ad,cins,ebat,sinif,renk,adet,depo,barkod) VALUES(?,?,?,?,?,?,?,?)",
        (
            request.form["ad"],
            request.form["cins"],
            request.form["ebat"],
            request.form["sinif"],
            request.form["renk"],
            request.form["adet"],
            request.form["depo"],
            barkod_no
        ))

        con.commit()

    urunler = cur.execute("SELECT * FROM urunler").fetchall()

    html = """
    <h2>DEPO SİSTEMİ</h2>

    <p>Giriş: {{user}} ({{role}})</p>

    {% if role=='admin' %}
    <h3>Ürün Ekle</h3>
    <form method="POST">
    Ad: <input name="ad"><br>
    Cins: <input name="cins"><br>
    Ebat: <input name="ebat"><br>
    HG/MAT: <input name="sinif"><br>
    Renk: <input name="renk"><br>
    Adet: <input name="adet"><br>

    Depo:
    <select name="depo">
    {% for d in depolar %}
    <option>{{d}}</option>
    {% endfor %}
    </select><br><br>

    <button>Ekle</button>
    </form>
    {% endif %}

    <h3>Ürünler</h3>
    {% for u in urunler %}
    <p>{{u[1]}} | {{u[2]}} | {{u[3]}} | {{u[4]}} | {{u[5]}} | {{u[6]}} adet | {{u[7]}} | Barkod: {{u[8]}}</p>
    {% endfor %}

    <br>
    <a href="/cikis">Barkod ile Çıkış</a> |
    <a href="/log">Hareketler</a>
    """

    return render_template_string(html, urunler=urunler, depolar=DEPOLAR, user=session["user"], role=session["role"])

# ---------------- BARKOD ÇIKIŞ ----------------
@app.route("/cikis", methods=["GET","POST"])
def cikis():
    if "role" not in session:
        return redirect("/login")

    con = db()
    cur = con.cursor()

    if request.method == "POST":
        barkod = request.form["barkod"]
        adet = int(request.form["adet"])

        urun = cur.execute("SELECT * FROM urunler WHERE barkod=?", (barkod,)).fetchone()

        if not urun:
            return "HATALI BARKOD"

        if urun[6] < adet:
            return "YETERSİZ STOK"

        yeni = urun[6] - adet

        cur.execute("UPDATE urunler SET adet=? WHERE id=?", (yeni, urun[0]))

        cur.execute("INSERT INTO log(user,islem,urun,depo,adet,tarih) VALUES(?,?,?,?,?,?)",
        (
            session["user"],
            "ÇIKIŞ",
            urun[1],
            urun[7],
            adet,
            str(datetime.datetime.now())
        ))

        con.commit()

    return """
    <h2>Barkod ile Çıkış</h2>
    <form method="POST">
    Barkod: <input name="barkod"><br>
    Adet: <input name="adet"><br>
    <button>Çıkış Yap</button>
    </form>
    """

# ---------------- LOG ----------------
@app.route("/log")
def log():
    con = db()
    cur = con.cursor()
    logs = cur.execute("SELECT * FROM log").fetchall()

    html = "<h2>Hareket Geçmişi</h2>"
    for l in logs:
        html += f"<p>{l[1]} | {l[2]} | {l[3]} | {l[4]} | {l[5]} | {l[6]}</p>"

    return html

# ---------------- BARKOD + QR PDF ----------------
@app.route("/etiket/<barkod_no>")
def etiket(barkod_no):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"Barkod: {barkod_no}", styles["Normal"]))

    # BARCODE
    CODE128 = barcode.get_barcode_class('code128')
    b = CODE128(barkod_no, writer=ImageWriter())
    bio = io.BytesIO()
    b.write(bio)
    bio.seek(0)

    elements.append(Image(bio, width=200, height=50))

    # QR
    qr = qrcode.make(barkod_no)
    qrbio = io.BytesIO()
    qr.save(qrbio)
    qrbio.seek(0)

    elements.append(Image(qrbio, width=100, height=100))

    elements.append(Spacer(1,20))

    doc.build(elements)

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="etiket.pdf")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
