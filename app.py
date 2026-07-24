from flask import Flask, request, redirect, render_template_string
import sqlite3, uuid, datetime

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

# ---------------- ANA ----------------
@app.route("/", methods=["GET","POST"])
def index():
    con = db()
    cur = con.cursor()

    if request.method == "POST":
        barkod = str(uuid.uuid4())[:8]

        cur.execute("INSERT INTO urun(ad,adet,depo,barkod) VALUES(?,?,?,?)",
        (request.form["ad"], request.form["adet"], request.form["depo"], barkod))

        con.commit()

    urunler = cur.execute("SELECT * FROM urun").fetchall()

    html = """
    <h2>DEPO</h2>

    <h3>Ürün Ekle</h3>
    <form method="POST">
    Ad: <input name="ad"><br>
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
    <p>{{u[1]}} | {{u[2]}} adet | {{u[3]}} | Barkod: {{u[4]}}</p>
    {% endfor %}

    <a href="/cikis">Barkod ile Çıkış</a><br>
    <a href="/log">Hareketler</a>
    """

    return render_template_string(html, urunler=urunler, depolar=DEPOLAR)

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

        if urun[2] < adet:
            return "❌ Yetersiz stok"

        yeni = urun[2] - adet

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

if __name__ == "__main__":
    app.run(debug=True)
