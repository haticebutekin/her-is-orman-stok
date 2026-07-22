from flask import Flask, render_template_string, request, redirect, session
import sqlite3
import barcode
from barcode.writer import ImageWriter
import os

app = Flask(__name__)
app.secret_key = "1234"

# DB
conn = sqlite3.connect("db.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS kullanicilar(
id INTEGER PRIMARY KEY,
username TEXT,
password TEXT,
rol TEXT)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS urunler(
id INTEGER PRIMARY KEY,
ad TEXT,
cins TEXT,
stok INTEGER,
kritik INTEGER,
barkod TEXT)
""")

conn.commit()

# DEFAULT USER
c.execute("SELECT * FROM kullanicilar")
if not c.fetchall():
    c.execute("INSERT INTO kullanicilar VALUES (NULL,'admin','1234','admin')")
    conn.commit()

# BARKOD
def barkod_olustur(kod):
    EAN = barcode.get_barcode_class('code128')
    ean = EAN(kod, writer=ImageWriter())
    filename = f"static/{kod}"
    ean.save(filename)
    return filename + ".png"

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["u"]
        p = request.form["p"]
        c.execute("SELECT * FROM kullanicilar WHERE username=? AND password=?", (u,p))
        user = c.fetchone()
        if user:
            session["user"] = user[1]
            session["rol"] = user[3]
            return redirect("/panel")
    return """
    <h2>Login</h2>
    <form method=post>
    <input name=u placeholder=Kullanıcı>
    <input name=p placeholder=Şifre>
    <button>Giriş</button>
    </form>
    """

# PANEL
@app.route("/panel")
def panel():
    if "user" not in session:
        return redirect("/")
    c.execute("SELECT * FROM urunler")
    data = c.fetchall()
    return render_template_string("""
    <h2>Hoşgeldin {{user}}</h2>

    <a href="/ekle">Ürün Ekle</a> |
    <a href="/cikis">Çıkış</a>

    <hr>

    <h3>Barkod Okut</h3>
    <input id="barkod" autofocus onkeypress="okut(event)">
    <audio id="bip">
      <source src="https://www.soundjay.com/buttons/beep-07.mp3">
    </audio>

    <script>
    function okut(e){
        if(e.key === "Enter"){
            let b = document.getElementById("barkod").value;
            document.getElementById("bip").play();
            window.location="/sat/"+b;
        }
    }
    </script>

    <hr>

    <table border=1>
    <tr><th>Ad</th><th>Cins</th><th>Stok</th><th>Barkod</th><th>Durum</th><th>İşlem</th></tr>
    {% for u in data %}
    <tr>
    <td>{{u[1]}}</td>
    <td>{{u[2]}}</td>
    <td>{{u[3]}}</td>
    <td>{{u[5]}}</td>
    <td>
        {% if u[3] <= u[4] %}
            <span style="color:red;">⚠ Kritik</span>
        {% else %}
            OK
        {% endif %}
    </td>
    <td>
    <a href="/art/{{u[0]}}">+</a>
    <a href="/azalt/{{u[0]}}">-</a>
    </td>
    </tr>
    {% endfor %}
    </table>
    """, data=data, user=session["user"])

# EKLE
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method == "POST":
        ad = request.form["ad"]
        cins = request.form["cins"]
        stok = int(request.form["stok"])
        kritik = int(request.form["kritik"])

        barkod = str(ad[:3] + cins[:3] + str(stok))
        barkod_olustur(barkod)

        c.execute("INSERT INTO urunler VALUES(NULL,?,?,?,?,?)",
                  (ad,cins,stok,kritik,barkod))
        conn.commit()

        return redirect("/panel")

    return """
    <h2>Ürün Ekle</h2>
    <form method=post>
    Ad: <input name=ad><br>
    Cins:
    <select name=cins>
        <option>Glosslak</option>
        <option>122 Vario HGloss</option>
        <option>Kapı</option>
        <option>Laminant</option>
        <option>MDF Lam</option>
        <option>Ham MDF</option>
        <option>Arkalık</option>
    </select><br>
    Stok: <input name=stok><br>
    Kritik: <input name=kritik><br>
    <button>Ekle</button>
    </form>
    """

# SAT (BARKOD)
@app.route("/sat/<b>")
def sat(b):
    c.execute("SELECT * FROM urunler WHERE barkod=?", (b,))
    u = c.fetchone()
    if u:
        yeni = u[3] - 1
        c.execute("UPDATE urunler SET stok=? WHERE id=?", (yeni,u[0]))
        conn.commit()
    return redirect("/panel")

# ART
@app.route("/art/<id>")
def art(id):
    c.execute("UPDATE urunler SET stok = stok + 1 WHERE id=?", (id,))
    conn.commit()
    return redirect("/panel")

# AZALT
@app.route("/azalt/<id>")
def azalt(id):
    c.execute("SELECT * FROM urunler WHERE id=?", (id,))
    u = c.fetchone()
    yeni = u[3] - 1
    c.execute("UPDATE urunler SET stok=? WHERE id=?", (yeni,id))
    conn.commit()
    return redirect("/panel")

# ÇIKIŞ
@app.route("/cikis")
def cikis():
    session.clear()
    return redirect("/")

# RUN
if __name__ == "__main__":
    if not os.path.exists("static"):
        os.mkdir("static")
    app.run(debug=True)
