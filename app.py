from flask import Flask, request, redirect, render_template_string, send_file
import sqlite3, uuid, datetime, io
import barcode
from barcode.writer import ImageWriter
import qrcode
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

# ---------------- DATABASE ----------------
def db():
    return sqlite3.connect("db.sqlite3")

def kur():
    con = db()
    cur = con.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS urun(
    id INTEGER PRIMARY KEY,
    ad TEXT,
    cins TEXT,
    ebat TEXT,
    kalinlik TEXT,
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
    adet INTEGER,
    depo TEXT,
    tarih TEXT
    )""")

    con.commit()
    con.close()

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

# ---------------- BARKOD ----------------
def barkod_uret(text):
    CODE128 = barcode.get_barcode_class('code128')
    buffer = io.BytesIO()
    code = CODE128(text, writer=ImageWriter())
    code.write(buffer)
    buffer.seek(0)
    return buffer

# ---------------- QR ----------------
def qr_uret(text):
    qr = qrcode.make(text)
    buffer = io.BytesIO()
    qr.save(buffer)
    buffer.seek(0)
    return buffer

# ---------------- ANA SAYFA ----------------
@app.route("/", methods=["GET","POST"])
def index():
    con = db()
    cur = con.cursor()

    if request.method == "POST":
        barkod = str(uuid.uuid4())[:8]

        cur.execute("""INSERT INTO urun
        (ad,cins,ebat,kalinlik,sinif,renk,adet,depo,barkod)
        VALUES(?,?,?,?,?,?,?,?,?)""",
        (
            request.form["ad"],
            request.form["cins"],
            request.form["ebat"],
            request.form["kalinlik"],
            request.form["sinif"],
            request.form["renk"],
            request.form["adet"],
            request.form["depo"],
            barkod
        ))
        con.commit()

    urunler = cur.execute("SELECT * FROM urun").fetchall()

    html = """
    <h2>ÜRÜN EKLE</h2>
    <form method="POST">
    Ad: <input name="ad"><br>
    Cins: <input name="cins"><br>
    Ebat: <input name="ebat"><br>
    Kalınlık(mm): <input name="kalinlik"><br>

    HG/MAT:
    <select name="sinif">
        <option>HG</option>
        <option>MAT</option>
    </select><br>

    Renk: <input name="renk"><br>
    Adet: <input name="adet"><br>

    Depo:
    <select name="depo">
    {% for d in depolar %}
        <option>{{d}}</option>
    {% endfor %}
    </select><br><br>

    <button>EKLE</button>
    </form>

    <hr>

    <h3>ÜRÜNLER</h3>
    {% for u in urunler %}
    <p>
    {{u[1]}} | {{u[2]}} | {{u[3]}} | {{u[4]}}mm | {{u[5]}} | {{u[6]}} |
    {{u[7]}} adet | {{u[8]}}

    | Barkod: {{u[9]}}
    | <a href="/etiket/{{u[9]}}">ETİKET</a>
    </p>
    {% endfor %}

    <br>
    <a href="/depocu">📦 DEPOCU EKRANI</a><br>
    <a href="/log">📋 HAREKETLER</a>
    """

    return render_template_string(html, urunler=urunler, depolar=DEPOLAR)

# ---------------- ETİKET ----------------
@app.route("/etiket/<barkod>")
def etiket(barkod):
    con = db()
    cur = con.cursor()
    u = cur.execute("SELECT * FROM urun WHERE barkod=?", (barkod,)).fetchone()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    elements = []
    elements.append(Paragraph(f"{u[1]}", styles["Normal"]))
    elements.append(Paragraph(f"{u[2]} - {u[3]}", styles["Normal"]))
    elements.append(Paragraph(f"{u[4]}mm - {u[5]} - {u[6]}", styles["Normal"]))
    elements.append(Paragraph(f"Depo: {u[8]}", styles["Normal"]))

    elements.append(Image(barkod_uret(barkod), width=200, height=50))
    elements.append(Image(qr_uret(barkod), width=100, height=100))

    doc.build(elements)

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="etiket.pdf")

# ---------------- DEPOCU ----------------
@app.route("/depocu", methods=["GET","POST"])
def depocu():
    con = db()
    cur = con.cursor()

    urun = None
    mesaj = ""

    if request.method == "POST":
        barkod = request.form.get("barkod")
        adet = request.form.get("adet")

        urun = cur.execute("SELECT * FROM urun WHERE barkod=?", (barkod,)).fetchone()

        if not urun:
            mesaj = "❌ Barkod bulunamadı"

        elif adet:
            adet = int(adet)

            if urun[7] < adet:
                mesaj = "❌ Yetersiz stok"
            else:
                yeni = urun[7] - adet
                cur.execute("UPDATE urun SET adet=? WHERE id=?", (yeni, urun[0]))

                cur.execute("""INSERT INTO log
                (user,islem,urun,adet,depo,tarih)
                VALUES(?,?,?,?,?,?)""",
                ("depocu","ÇIKIŞ",urun[1],adet,urun[8],str(datetime.datetime.now())))

                con.commit()
                mesaj = "✅ Çıkış yapıldı"
                urun = None

    html = """
    <h2>📦 DEPOCU PANELİ</h2>

    <form method="POST">
        <input name="barkod" placeholder="Barkod okut"><br><br>
        <button>ÜRÜN BUL</button>
    </form>

    <p style="color:red;">{{mesaj}}</p>

    {% if urun %}
    <hr>
    <p><b>{{urun[1]}}</b></p>
    <p>{{urun[2]}} - {{urun[3]}}</p>
    <p>{{urun[4]}}mm - {{urun[5]}}</p>
    <p>{{urun[6]}} | Stok: {{urun[7]}}</p>
    <p>Depo: {{urun[8]}}</p>

    <form method="POST">
        <input type="hidden" name="barkod" value="{{urun[9]}}">
        <input name="adet" placeholder="Adet"><br><br>
        <button>🚚 ÇIKIŞ</button>
    </form>
    {% endif %}
    """

    return render_template_string(html, urun=urun, mesaj=mesaj)

# ---------------- LOG ----------------
@app.route("/log")
def log():
    con = db()
    cur = con.cursor()
    logs = cur.execute("SELECT * FROM log").fetchall()

    html = "<h2>HAREKETLER</h2>"
    for l in logs:
        html += f"<p>{l[1]} | {l[2]} | {l[3]} | {l[4]} | {l[5]} | {l[6]}</p>"

    return html

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
