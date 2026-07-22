from flask import Flask, request, redirect, render_template_string
import psycopg2
import os

app = Flask(__name__)

# PostgreSQL bağlantı (Render otomatik verecek)
DATABASE_URL = os.environ.get("DATABASE_URL")

def db():
    return psycopg2.connect(DATABASE_URL)

# TABLO OLUŞTUR
with db() as conn:
    with conn.cursor() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS urun(
            id SERIAL PRIMARY KEY,
            barkod TEXT,
            ad TEXT,
            cins TEXT,
            ebat TEXT,
            renk TEXT,
            adet INTEGER,
            fiyat FLOAT
        )
        """)

# ANA SAYFA (KASA)
@app.route("/", methods=["GET", "POST"])
def pos():
    sonuc = None
    if request.method == "POST":
        barkod = request.form["barkod"]

        with db() as conn:
            with conn.cursor() as c:
                c.execute("SELECT * FROM urun WHERE barkod=%s", (barkod,))
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
    """ , sonuc=sonuc)

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
            with conn.cursor() as c:
                c.execute("""
                INSERT INTO urun (barkod,ad,cins,ebat,renk,adet,fiyat)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, data)

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
