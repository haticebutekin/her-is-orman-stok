from flask import Flask, request, redirect, session
import sqlite3, random, datetime

app = Flask(__name__)
app.secret_key = "secret"

conn = sqlite3.connect("db.db", check_same_thread=False)
c = conn.cursor()

# TABLOLAR
c.execute("""CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY, username TEXT, password TEXT, role TEXT)""")

c.execute("""CREATE TABLE IF NOT EXISTS urun(
id INTEGER PRIMARY KEY,
barkod TEXT,
ad TEXT,
yuzey TEXT,
fiyat REAL,
stok INTEGER)""")

c.execute("""CREATE TABLE IF NOT EXISTS satis(
id INTEGER PRIMARY KEY,
barkod TEXT,
adet INTEGER,
tarih TEXT)""")

conn.commit()

# admin
c.execute("INSERT OR IGNORE INTO users VALUES (1,'admin','1234','admin')")
conn.commit()

def barkod():
    return str(random.randint(100000000000,999999999999))

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["u"]
        p = request.form["p"]
        user = c.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p)).fetchone()
        if user:
            session["user"] = u
            return redirect("/pos")
    return '''
    <h2>Giriş</h2>
    <form method=post>
    <input name=u placeholder="kullanıcı">
    <input name=p type=password placeholder="şifre">
    <button>Giriş</button>
    </form>
    '''

# POS
@app.route("/pos")
def pos():
    if "user" not in session:
        return redirect("/")

    urunler = c.execute("SELECT * FROM urun").fetchall()

    html = '''
    <html>
    <head>
    <script src="https://unpkg.com/html5-qrcode"></script>
    <script src="https://cdn.jsdelivr.net/npm/jsbarcode"></script>
    <style>
    body{background:#0f172a;color:white;font-family:Arial;padding:20px;}
    input,select,button{padding:10px;margin:5px;}
    button{background:#22c55e;color:white;}
    </style>
    </head>
    <body>

    <h1>🛒 POS</h1>

    <button onclick="kamera()">📷 Barkod Oku</button>
    <div id="reader"></div>

    <form method="POST" action="/sat">
    Barkod <input id="barkod" name="barkod">
    Adet <input name="adet" value="1">
    <button>Sat</button>
    </form>

    <h2>Ürünler</h2>
    '''

    for u in urunler:
        html += f"{u[2]} - {u[3]} - {u[4]} TL - stok:{u[5]}<br>"

    html += '''

    <hr>

    <h2>➕ Ürün Ekle</h2>

    <form method="POST" action="/ekle">
    Barkod <input name="barkod" placeholder="boş bırak otomatik"><br>
    Ad <input name="ad"><br>

    Yüzey
    <select name="yuzey">
        <option value="HG">HG</option>
        <option value="MAT">MAT</option>
    </select><br>

    Fiyat <input name="fiyat"><br>
    Stok <input name="stok"><br>

    <button>Kaydet</button>
    </form>

    <script>
    function kamera(){
        let scanner = new Html5QrcodeScanner("reader",{fps:10});
        scanner.render((text)=>{
            document.getElementById("barkod").value = text;
            scanner.clear();
        });
    }
    </script>

    </body>
    </html>
    '''
    return html

# ÜRÜN EKLE
@app.route("/ekle", methods=["POST"])
def ekle():
    barkod_v = request.form.get("barkod") or barkod()
    ad = request.form.get("ad")
    yuzey = request.form.get("yuzey")
    fiyat = request.form.get("fiyat")
    stok = request.form.get("stok")

    c.execute("INSERT INTO urun (barkod,ad,yuzey,fiyat,stok) VALUES (?,?,?,?,?)",
              (barkod_v,ad,yuzey,fiyat,stok))
    conn.commit()

    return redirect("/pos")

# SATIŞ + STOK DÜŞME
@app.route("/sat", methods=["POST"])
def sat():
    barkod_v = request.form.get("barkod")
    adet = int(request.form.get("adet"))

    urun = c.execute("SELECT * FROM urun WHERE barkod=?", (barkod_v,)).fetchone()

    if urun:
        yeni_stok = urun[5] - adet
        c.execute("UPDATE urun SET stok=? WHERE barkod=?", (yeni_stok, barkod_v))
        c.execute("INSERT INTO satis (barkod,adet,tarih) VALUES (?,?,?)",
                  (barkod_v,adet,str(datetime.datetime.now())))
        conn.commit()

    return redirect("/pos")

# RAPOR
@app.route("/rapor")
def rapor():
    data = c.execute("SELECT * FROM satis").fetchall()
    return "<br>".join([str(x) for x in data])

# FİŞ
@app.route("/fis")
def fis():
    return '''
    <h3>FİŞ</h3>
    <script>
    window.print()
    </script>
    '''

if __name__ == "__main__":
    app.run(debug=True)
