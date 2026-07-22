from flask import Flask, request, redirect, session
import sqlite3, random, datetime

app = Flask(__name__)
app.secret_key = "1234"

conn = sqlite3.connect("db.db", check_same_thread=False)
c = conn.cursor()

# TABLO
c.execute("""
CREATE TABLE IF NOT EXISTS urun(
id INTEGER PRIMARY KEY,
barkod TEXT,
ad TEXT,
cins TEXT,
ebat TEXT,
renk TEXT,
yuzey TEXT,
fiyat REAL,
stok INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS satis(
id INTEGER PRIMARY KEY,
urun TEXT,
adet INTEGER,
toplam REAL,
tarih TEXT
)
""")

conn.commit()

def barkod_uret():
    return str(random.randint(100000000000,999999999999))

# ANA SAYFA (KASA)
@app.route("/")
def kasa():

    if "sepet" not in session:
        session["sepet"] = []

    urunler = c.execute("SELECT * FROM urun").fetchall()

    toplam = sum([x["toplam"] for x in session["sepet"]]) if session["sepet"] else 0

    html = """
    <html>
    <head>
    <script src="https://unpkg.com/html5-qrcode"></script>
    <script src="https://cdn.jsdelivr.net/npm/jsbarcode"></script>

    <style>
    body{background:#020617;color:white;font-family:Arial;padding:20px;}
    input,select,button{padding:10px;margin:5px;}
    .kutu{background:#0f172a;padding:10px;margin:10px;}
    </style>
    </head>

    <body>

    <h1>🛒 KASA EKRANI</h1>

    <button onclick="kamera()">📷 Barkod Oku</button>
    <div id="reader"></div>

    <form method="POST" action="/sepete">
    Barkod <input id="barkod" name="barkod">
    Adet <input name="adet" value="1">
    <button>Sepete Ekle</button>
    </form>

    <h2>🛒 Sepet</h2>
    """

    for s in session["sepet"]:
        html += f"{s['ad']} x{s['adet']} = {s['toplam']} TL<br>"

    html += f"<h3>TOPLAM: {toplam} TL</h3>"

    html += """
    <a href="/satis"><button>💰 SATIŞI TAMAMLA</button></a>

    <hr>

    <h2>➕ Ürün Ekle</h2>

    <form method="POST" action="/ekle">
    Barkod <input name="barkod" placeholder="boş bırak otomatik"><br>
    Ad <input name="ad"><br>
    Cins <input name="cins"><br>
    Ebat <input name="ebat"><br>
    Renk <input name="renk"><br>

    Yüzey
    <select name="yuzey">
        <option value="HG">HG</option>
        <option value="MAT">MAT</option>
    </select><br>

    Fiyat <input name="fiyat"><br>
    Stok <input name="stok"><br>

    <button>Kaydet</button>
    </form>

    <hr>

    <h2>📦 Ürünler</h2>
    """

    for u in urunler:
        html += f"""
        <div class='kutu'>
        {u[2]} | {u[3]} | {u[4]} | {u[5]} | {u[6]}<br>
        {u[7]} TL | stok:{u[8]}<br>
        Barkod: {u[1]}<br>
        <button onclick="etiket('{u[1]}','{u[2]}','{u[7]}')">🖨️ Etiket</button>
        </div>
        """

    html += """

    <div id="etiket" style="display:none;background:white;color:black;padding:20px;">
        <h3 id="ad"></h3>
        <svg id="barcode"></svg>
        <p id="fiyat"></p>
    </div>

    <script>
    function kamera(){
        let scanner = new Html5QrcodeScanner("reader",{fps:10});
        scanner.render((text)=>{
            document.getElementById("barkod").value = text;
            scanner.clear();
        });
    }

    function etiket(barkod, ad, fiyat){
        document.getElementById("etiket").style.display="block";
        document.getElementById("ad").innerText = ad;
        document.getElementById("fiyat").innerText = fiyat + " TL";
        JsBarcode("#barcode", barkod);
        window.print();
    }
    </script>

    </body></html>
    """

    return html


# ÜRÜN EKLE
@app.route("/ekle", methods=["POST"])
def ekle():
    barkod = request.form.get("barkod") or barkod_uret()
    ad = request.form.get("ad")
    cins = request.form.get("cins")
    ebat = request.form.get("ebat")
    renk = request.form.get("renk")
    yuzey = request.form.get("yuzey")
    fiyat = float(request.form.get("fiyat"))
    stok = int(request.form.get("stok"))

    c.execute("""
    INSERT INTO urun VALUES (NULL,?,?,?,?,?,?,?,?)
    """,(barkod,ad,cins,ebat,renk,yuzey,fiyat,stok))
    conn.commit()

    return redirect("/")

# SEPETE EKLE
@app.route("/sepete", methods=["POST"])
def sepete():
    barkod = request.form.get("barkod")
    adet = int(request.form.get("adet"))

    urun = c.execute("SELECT * FROM urun WHERE barkod=?", (barkod,)).fetchone()

    if urun:
        toplam = urun[7] * adet

        session["sepet"].append({
            "ad": urun[2],
            "adet": adet,
            "toplam": toplam,
            "barkod": barkod
        })
        session.modified = True

    return redirect("/")

# SATIŞ TAMAMLAMA
@app.route("/satis")
def satis():
    for s in session["sepet"]:
        urun = c.execute("SELECT * FROM urun WHERE barkod=?", (s["barkod"],)).fetchone()
        yeni = urun[8] - s["adet"]

        c.execute("UPDATE urun SET stok=? WHERE barkod=?", (yeni, s["barkod"]))
        c.execute("INSERT INTO satis VALUES (NULL,?,?,?,?)",
                  (s["ad"], s["adet"], s["toplam"], str(datetime.datetime.now())))

    conn.commit()
    session["sepet"] = []

    return """
    <h2>Satış tamamlandı</h2>
    <script>window.print()</script>
    <a href="/">Geri dön</a>
    """

if __name__ == "__main__":
    app.run(debug=True)
