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
                    "fiyat": urun[7]
                })
                session["sepet"] = sepet

    toplam = sum(i["fiyat"] for i in session["sepet"])

    return render_template_string("""
    <h1>🧾 ORMAN KASA PRO</h1>

    <form method="post">
        Barkod: <input name="barkod" id="barkod">
        <button>Ekle</button>
    </form>

    <button onclick="kamera()">📷 Kamera ile oku</button>
    <div id="reader"></div>

    <h2>Sepet</h2>
    {% for i in sepet %}
        {{i.ad}} - {{i.fiyat}} ₺<br>
    {% endfor %}

    <h3>TOPLAM: {{toplam}} ₺</h3>

    <a href="/temizle">🧹 Sepeti Temizle</a>
    <br><br>
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

# 🧹 SEPET TEMİZLE
@app.route("/temizle")
def temizle():
    session["sepet"] = []
    return redirect("/")

# ➕ ÜRÜN EKLE (OTOMATİK BARKOD)
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method == "POST":
        barkod = str(random.randint(1000000000,9999999999))

        data = (
            barkod,
            request.form["ad"],
            request.form["cins"],
            request.form["ebat"],
            request.form["renk"],
            request.form["adet"],
            request.form["fiyat"]
        )

        with db() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO urun VALUES (NULL,?,?,?,?,?,?,?)", data)

        return f"""
        KAYDEDİLDİ ✅ <br>
        Barkod: {barkod} <br>
        <a href='/'>Kasa</a>
        """

    return """
    <h1>Ürün Ekle</h1>
    <form method="post">
        Ad: <input name="ad"><br>
        Cins: <input name="cins"><br>
        Ebat: <input name="ebat"><br>
        Renk: <input name="renk"><br>
        Adet: <input name="adet"><br>
        Fiyat: <input name="fiyat"><br>
        <button>Kaydet</button>
    </form>
    """

if __name__ == "__main__":
    app.run()
