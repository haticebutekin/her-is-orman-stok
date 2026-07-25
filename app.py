from flask import Flask, request, redirect, render_template_string, send_file
import sqlite3, uuid, datetime, io
import barcode
from barcode.writer import ImageWriter
import qrcode
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

# ---------------- DB ----------------
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
    sinif TEXT,
    renk TEXT,
    kalinlik TEXT,
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
    tarih TEXT
    )""")

    con.commit()
    con.close()

kur()

DEPOLAR = [
"MDF SATIŞ","LAMİNANT","KAPI",
"HGLOSS","SÜTÇÜ","HELVACI",
"RÖTBALANSÇI","KESİMHANE"
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

# ---------------- ANA ----------------
@app.route("/", methods=["GET","POST"])
def index():
    con = db()
    cur = con.cursor()

    if request.method == "POST":
        barkod = str(uuid.uuid4())[:8]

        cur.execute("""INSERT INTO urun
        (ad,cins,ebat,sinif,renk,kalinlik,adet,depo,barkod)
        VALUES(?,?,?,?,?,?,?,?)""",
        (
            request.form["ad"],
            request.form["cins"],
            request.form["ebat"],
            request.form["sinif"],
            request.form["renk"],
            request.form["kalinlik"],
            request.form["adet"],
            request.form["depo"],
            barkod
        ))

        con.commit()

    urunler = cur.execute("SELECT * FROM urun").fetchall()

    html = """
    <h2>DEPO SİSTEMİ</h2>

    <h3>Ürün Ekle</h3>
    <form method="POST">
    Ad: <input name="ad"><br>
    Cins: <input name="cins"><br>
    Ebat: <input name="ebat"><br>
    Kalınlık (mm): <input name="kalinlik"><br>
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

    <button>Ekle</button>
    </form>

    <h3>Ürünler</h3>
    {% for u in urunler %}
    <p>
    {{u[1]}} | {{u[2]}} | {{u[3]}} | {{u[4]}} | {{u[5]}} |
    {{u[6]}}mm | {{u[7]}}adet

    | Barkod: {{u[8]}}

    | <a href="/etiket/{{u[8]}}">ETİKET</a>
    </p>
    {% endfor %}

    <a href="/cikis">Barkod ile Çıkış</a><br>
    <a href="/log">Hareketler</a>
    """

    return render_template_string(html, urunler=urunler, depolar=DEPOLAR)

# ---------------- ETİKET PDF ----------------
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
    elements.append(Paragraph(f"{u[4]} - {u[5]} - {u[6]}mm", styles["Normal"]))
    elements.append(Paragraph(f"Depo: {u[7]}", styles["Normal"]))

    # barcode
    b = barkod_uret(barkod)
    elements.append(Image(b, width=200, height=50))

    # qr
    q = qr_uret(barkod)
    elements.append(Image(q, width=100, height=100))

    doc.build(elements)

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="etiket.pdf")

# ---------------- ÇIKIŞ ----------------
@app.route("/cikis", methods=["GET","POST"])
def cikis():
    con = db()
    cur = con.cursor()

    if request.method == "POST":
        barkod = request.form["barkod"]
        adet = int(request.form["adet"])

        urun = cur.execute("SELECT * FROM urun WHERE barkod=?", (barkod,)).fetchone()

        if not urun:
            return "❌ Barkod bulunamadı"

        if urun[6] < adet:
            return "❌ Yetersiz stok"

        yeni = urun[6] - adet

        cur.execute("UPDATE urun SET adet=? WHERE id=?", (yeni, urun[0]))

        cur.execute("INSERT INTO log(user,islem,urun,adet,tarih) VALUES(?,?,?,?,?)",
        ("depocu","ÇIKIŞ",urun[1],adet,str(datetime.datetime.now())))

        con.commit()

        return "✅ Çıkış yapıldı"

    return """
    <h2>Barkod Çıkış</h2>
    <form method="POST">
    Barkod: <input name="barkod"><br>
    Adet: <input name="adet"><br>
    <button>Çıkış</button>
    </form>
    """

# ---------------- LOG ----------------
@app.route("/log")
def log():
    con = db()
    cur = con.cursor()
    logs = cur.execute("SELECT * FROM log").fetchall()

    html = "<h2>Hareketler</h2>"
    for l in logs:
        html += f"<p>{l[1]} | {l[2]} | {l[3]} | {l[4]} | {l[5]}</p>"

    return html


@app.route("/depocu", methods=["GET","POST"])
def depocu():
    con = db()
    cur = con.cursor()

    urun = None
    mesaj = ""

    if request.method == "POST":
        barkod = request.form.get("barkod")
        adet = request.form.get("adet")

        if barkod and not adet:
            # SADECE BARKOD → ÜRÜN BUL
            urun = cur.execute("SELECT * FROM urun WHERE barkod=?", (barkod,)).fetchone()
            if not urun:
                mesaj = "❌ Barkod bulunamadı"

        elif barkod and adet:
            # ÇIKIŞ YAP
            adet = int(adet)
            urun = cur.execute("SELECT * FROM urun WHERE barkod=?", (barkod,)).fetchone()

            if not urun:
                mesaj = "❌ Hatalı barkod"

            elif urun[7] < adet:
                mesaj = "❌ Yetersiz stok"

            else:
                yeni = urun[7] - adet

                cur.execute("UPDATE urun SET adet=? WHERE id=?", (yeni, urun[0]))

                cur.execute("""INSERT INTO log(user,islem,urun,adet,tarih)
                VALUES(?,?,?,?,?)""",
                ("depocu","ÇIKIŞ",urun[1],adet,str(datetime.datetime.now())))

                con.commit()
                mesaj = "✅ Çıkış yapıldı"
                urun = None

    html = """
    <h2>📦 DEPOCU EKRANI</h2>

    <form method="POST">
        <input name="barkod" placeholder="Barkod okut / yaz" style="width:100%; height:40px;"><br><br>
        <button style="width:100%; height:40px;">Ürünü Bul</button>
    </form>

    <br>
    <p style="color:red;">{{mesaj}}</p>

    {% if urun %}
    <hr>
    <h3>Ürün Bilgisi</h3>

    <p><b>Ad:</b> {{urun[1]}}</p>
    <p><b>Cins:</b> {{urun[2]}}</p>
    <p><b>Ebat:</b> {{urun[3]}}</p>
    <p><b>HG/MAT:</b> {{urun[4]}}</p>
    <p><b>Renk:</b> {{urun[5]}}</p>
    <p><b>Kalınlık:</b> {{urun[6]}} mm</p>
    <p><b>Stok:</b> {{urun[7]}}</p>
    <p><b>Depo:</b> {{urun[8]}}</p>

    <hr>

    <form method="POST">
        <input type="hidden" name="barkod" value="{{urun[9]}}">
        <input name="adet" placeholder="Çıkacak adet" style="width:100%; height:40px;"><br><br>
        <button style="width:100%; height:50px; background:green; color:white;">
        🚚 ÇIKIŞ YAP
        </button>
    </form>

    if __name__ == "__main__":
    app.run(debug=True)
    {% endif %}
    """

    return render_template_string(html, urun=urun, mesaj=mesaj)
