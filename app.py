from flask import Flask, request, redirect, session, render_template_string, send_file
import sqlite3
import os
import pandas as pd
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DB ----------------
def get_db():
    return sqlite3.connect("db.sqlite", check_same_thread=False)

db = get_db()
cur = db.cursor()

# tablolar
cur.execute("""
CREATE TABLE IF NOT EXISTS urun(
id INTEGER PRIMARY KEY,
isim TEXT,
barkod TEXT UNIQUE,
adet INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
username TEXT,
password TEXT,
role TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS log(
id INTEGER PRIMARY KEY,
kullanici TEXT,
barkod TEXT,
islem TEXT,
tarih TEXT
)
""")

db.commit()

# ilk admin
cur.execute("SELECT * FROM users WHERE username='admin'")
if not cur.fetchone():
    cur.execute("INSERT INTO users VALUES (NULL,'admin','1234','admin')")
    db.commit()

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["u"]
        p = request.form["p"]

        cur.execute("SELECT role FROM users WHERE username=? AND password=?", (u,p))
        user = cur.fetchone()

        if user:
            session["user"] = u
            session["role"] = user[0]
            return redirect("/")
        return "Hatalı giriş"

    return """
    <h2>Login</h2>
    <form method="post">
    Kullanıcı: <input name="u"><br>
    Şifre: <input name="p" type="password"><br>
    <button>Giriş</button>
    </form>
    """

# ---------------- HOME ----------------
@app.route("/")
def index():
    if "user" not in session:
        return redirect("/login")

    return f"""
    <h2>Hoşgeldin {session['user']} ({session['role']})</h2>

    <a href='/ekle'>Ürün Ekle</a><br><br>
    <a href='/excel'>Excel Yükle</a><br><br>
    <a href='/kamera/giris'>📥 Giriş</a><br><br>
    <a href='/kamera/cikis'>📤 Çıkış</a><br><br>
    <a href='/liste'>Ürün Liste</a><br><br>
    <a href='/logout'>Çıkış Yap</a>
    """

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- ÜRÜN EKLE ----------------
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method == "POST":
        isim = request.form["isim"]
        barkod_kod = request.form["barkod"]
        adet = int(request.form["adet"])

        try:
            cur.execute("INSERT INTO urun (isim,barkod,adet) VALUES (?,?,?)",
                        (isim,barkod_kod,adet))
            db.commit()
        except:
            return "Barkod zaten var"

        return redirect(f"/barkod/{barkod_kod}")

    return """
    <h2>Ürün Ekle</h2>
    <form method="post">
    İsim: <input name="isim"><br>
    Barkod: <input name="barkod"><br>
    Adet: <input name="adet" type="number"><br><br>
    <button>Ekle</button>
    </form>
    """

# ---------------- BARKOD ----------------
@app.route("/barkod/<kod>")
def barkod_olustur(kod):
    os.makedirs("static", exist_ok=True)

    EAN = barcode.get_barcode_class('code128')
    ean = EAN(kod, writer=ImageWriter())

    path = f"static/{kod}"
    ean.save(path)

    return f"""
    <h2>Barkod</h2>
    <img src='/{path}.png'><br><br>
    <a href='/{path}.png' download>İndir</a><br><br>
    <a href='/'>Ana Menü</a>
    """

# ---------------- EXCEL ----------------
@app.route("/excel", methods=["GET","POST"])
def excel():
    if request.method == "POST":
        file = request.files["file"]
        df = pd.read_excel(file)

        for _, row in df.iterrows():
            try:
                cur.execute(
                    "INSERT INTO urun (isim,barkod,adet) VALUES (?,?,?)",
                    (row["isim"], str(row["barkod"]), int(row["adet"]))
                )
            except:
                pass

        db.commit()
        return "Yüklendi"

    return """
    <h2>Excel Yükle</h2>
    <form method="post" enctype="multipart/form-data">
    <input type="file" name="file">
    <button>Yükle</button>
    </form>
    """

# ---------------- LİSTE ----------------
@app.route("/liste")
def liste():
    cur.execute("SELECT * FROM urun")
    data = cur.fetchall()

    html = "<h2>Ürünler</h2>"
    for u in data:
        html += f"{u[1]} | {u[2]} | {u[3]}<br>"

    return html + "<br><a href='/'>Geri</a>"

# ---------------- HIZLI İŞLEM ----------------
@app.route("/hizli_islem", methods=["POST"])
def hizli_islem():
    barkod_kod = request.json.get("barkod")
    tip = request.json.get("tip")

    if session.get("role") == "depo" and tip != "cikis":
        return {"ok": False}

    cur.execute("SELECT isim, adet FROM urun WHERE barkod=?", (barkod_kod,))
    veri = cur.fetchone()

    if not veri:
        return {"ok": False}

    isim, adet = veri

    if tip == "cikis":
        if adet <= 0:
            return {"ok": False}
        adet -= 1
    else:
        adet += 1

    cur.execute("UPDATE urun SET adet=? WHERE barkod=?", (adet, barkod_kod))

    cur.execute("""
    INSERT INTO log (kullanici,barkod,islem,tarih)
    VALUES (?,?,?,datetime('now'))
    """, (session["user"], barkod_kod, tip))

    db.commit()

    return {"ok": True, "isim": isim, "adet": adet}

# ---------------- KAMERA ----------------
@app.route("/kamera/<tip>")
def kamera(tip):
    return render_template_string("""
    <h2>Barkod Okut</h2>

    <video id="video" width="300" autoplay></video>
    <h1 id="isim">Hazır</h1>
    <h2 id="stok"></h2>

    <script src="https://unpkg.com/@zxing/library@latest"></script>

    <script>
    const codeReader = new ZXing.BrowserBarcodeReader()

    let lock = false
    let last = ""

    codeReader.decodeFromVideoDevice(null, 'video', async (result, err) => {
        if (result && !lock) {

            let barkod = result.text
            if (barkod === last) return;

            lock = true
            last = barkod

            let res = await fetch("/hizli_islem", {
                method:"POST",
                headers:{"Content-Type":"application/json"},
                body: JSON.stringify({
                    barkod: barkod,
                    tip: "{{tip}}"
                })
            })

            let data = await res.json()

            if (data.ok) {
                document.body.style.background = "white"
                isim.innerText = data.isim
                stok.innerText = "Kalan: " + data.adet
                navigator.vibrate(100)
            } else {
                document.body.style.background = "red"
                isim.innerText = "HATALI ÜRÜN"
                stok.innerText = ""
            }

            setTimeout(()=>{lock=false},400)
        }
    })
    </script>
    """, tip=tip)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
