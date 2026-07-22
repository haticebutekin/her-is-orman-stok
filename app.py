from flask import Flask, request, redirect, render_template_string, session
import sqlite3, random

app = Flask(__name__)
app.secret_key = "123"

def db():
    return sqlite3.connect("db.db")

# TABLO
with db() as conn:
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS urun(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barkod TEXT,
        ad TEXT,
        cins TEXT,
        ebat TEXT,
        renk TEXT,
        yuzey TEXT,
        sinif TEXT,
        adet INTEGER,
        fiyat REAL
    )
    """)

# 🧾 KASA
@app.route("/", methods=["GET","POST"])
def pos():
    if "sepet" not in session:
        session["sepet"] = []

    if request.method == "POST":
        barkod = request.form["barkod"]

        with db() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM urun WHERE barkod=?", (barkod,))
            urun = c.fetchone()

            if urun:
                sepet = session["sepet"]
                sepet.append({
                    "ad": urun[2],
                    "fiyat": urun[9]
                })
                session["sepet"] = sepet

    toplam = sum(i["fiyat"] for i in session["sepet"])

    return render_template_string("""
    <h1>🧾 ORMAN KASA PRO</h1>

    <form method="post">
        Barkod: <input name="barkod" id="barkod">
        <button>Ekle</button>
    </form>

    <button onclick="kamera()">📷 Kamera</button>
    <div id="reader"></div>

    <h2>Sepet</h2>
    {% for i in sepet %}
        {{i.ad}} - {{i.fiyat}} ₺<br>
    {% endfor %}

    <h3>TOPLAM: {{toplam}} ₺</h3>

    <a href="/fis">🧾 Fiş</a> |
    <a href="/liste">📦 Ürünler</a> |
    <a href="/temizle">🧹 Temizle</a> |
    <a href="/ekle">➕ Ürün Ekle</a>

    <script src="https://unpkg.com/html5-qrcode"></script>
    <script>
    function kamera(){
        let q = new Html5Qrcode("reader");
        q.start({ facingMode: "environment" }, { fps: 10 }, (text)=>{
            document.getElementById("barkod").value = text;
            q.stop();
        });
    }
    </script>
    """, sepet=session["sepet"], toplam=toplam)

# 🧾 FİŞ
@app.route("/fis")
def fis():
    sepet = session.get("sepet", [])
    toplam = sum(i["fiyat"] for i in sepet)

    text = "ORMAN KASA PRO\n\n"
    for i in sepet:
        text += f"{i['ad']} - {i['fiyat']} TL\n"
    text += f"\nTOPLAM: {toplam} TL"

    return f"<pre>{text}</pre><script>window.print()</script>"

# 📦 ÜRÜNLER
@app.route("/liste")
def liste():
    with db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM urun")
        data = c.fetchall()

    html = "<h1>ÜRÜNLER</h1>"

    for i in data:
        html += f"""
        <div style='border:1px solid #ccc;padding:10px;margin:10px'>
        <b>{i[2]}</b><br>
        Barkod: {i[1]}<br>
        <img src='https://barcode.tec-it.com/barcode.ashx?data={i[1]}&code=EAN13'><br>

        Cins: {i[3]}<br>
        Ebat: {i[4]}<br>
        Renk: {i[5]}<br>
        Yüzey: {i[6]}<br>
        <b>Marka: {i[7]}</b><br>
        Fiyat: {i[9]} TL
        </div>
        """

    html += "<a href='/'>Kasa</a>"
    return html

# ➕ ÜRÜN EKLE
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method == "POST":

        barkod = "20" + str(random.randint(100000000,999999999))

        data = (
            barkod,
            request.form["ad"],
            request.form["cins"],
            request.form["ebat"],
            request.form["renk"],
            request.form["yuzey"],
            request.form["sinif"],  # MARKA
            request.form["adet"],
            request.form["fiyat"]
        )

        with db() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO urun VALUES (NULL,?,?,?,?,?,?,?,?,?)", data)

        return f"""
        <h2>✅ ÜRÜN KAYDEDİLDİ</h2>
        <h1>BARKOD: {barkod}</h1>
        <img src='https://barcode.tec-it.com/barcode.ashx?data={barkod}&code=EAN13'><br>
        <a href='/liste'>📦 Ürünler</a>
        """

    return """
    <h1>Ürün Ekle</h1>
    <form method="post">
        Ad: <input name="ad"><br>
        Cins: <input name="cins"><br>
        Ebat: <input name="ebat"><br>
        Renk: <input name="renk"><br>

        Yüzey:
        <select name="yuzey">
            <option>HG</option>
            <option>MAT</option>
        </select><br>

        Marka:
        <input name="sinif"><br>

        Adet: <input name="adet"><br>
        Fiyat: <input name="fiyat"><br>

        <button>Kaydet</button>
    </form>
    """

# 🧹 TEMİZLE
@app.route("/temizle")
def temizle():
    session["sepet"] = []
    return redirect("/")

if __name__ == "__main__":
    app.run()
