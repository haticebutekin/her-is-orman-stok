from flask import Flask, request, redirect, render_template_string
import psycopg2, sqlite3, os

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

# 🔥 AKILLI DATABASE SEÇİMİ
def db():
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL)
    else:
        return sqlite3.connect("db.db")

# TABLO
def tablo():
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
        conn.commit()

tablo()

# KASA
@app.route("/", methods=["GET","POST"])
def pos():
    sonuc = None
    if request.method == "POST":
        barkod = request.form["barkod"]

        with db() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM urun WHERE barkod=?", (barkod,))
            sonuc = c.fetchone()

    return render_template_string("""
    <h1>🧾 ORMAN KASA PRO</h1>

    <form method="post">
        Barkod: <input name="barkod" id="barkod">
        <button>Ara</button>
    </form>

    <button onclick="kamera()">📷 Kamera ile oku</button>
    <div id="reader"></div>

    {% if sonuc %}
        <h2>ÜRÜN</h2>
        Ad: {{sonuc[2]}}<br>
        Cins: {{sonuc[3]}}<br>
        Ebat: {{sonuc[4]}}<br>
        Renk: {{sonuc[5]}}<br>
        Adet: {{sonuc[6]}}<br>
        Fiyat: {{sonuc[7]}} ₺
    {% endif %}

    <hr>
    <a href="/ekle">➕ Ürün Ekle</a>

    <script src="https://unpkg.com/html5-qrcode"></script>
    <script>
    function kamera(){
        let html5QrCode = new Html5Qrcode("reader");
        html5QrCode.start(
            { facingMode: "environment" },
            { fps: 10 },
            (text) => {
                document.getElementById("barkod").value = text;
                html5QrCode.stop();
            }
        );
    }
    </script>
    """, sonuc=sonuc)

# ÜRÜN EKLE
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method == "POST":
        data = (
            request.form["barkod"],
            request.form["ad"],
            request.form["cins"],
            request.form["ebat"],
            request.form["renk"],
            request.form["adet"],
            request.form["fiyat"]
        )

        with db() as conn:
            c = conn.cursor()
            c.execute("INSERT INTO urun (barkod,ad,cins,ebat,renk,adet,fiyat) VALUES (?,?,?,?,?,?,?)", data)
            conn.commit()

        return redirect("/")

    return """
    <h1>Ürün Ekle</h1>
    <form method="post">
        Barkod: <input name="barkod"><br>
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
