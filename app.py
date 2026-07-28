from flask import Flask, request, redirect, session, render_template_string, send_file
import sqlite3, os, datetime, shutil

app = Flask(__name__)
app.secret_key = "lvl4"

DB = "data.db"

def db():
    return sqlite3.connect(DB)

def init():
    con = db()
    cur = con.cursor()

    # kullanıcılar
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    username TEXT,
    password TEXT,
    role TEXT
    )""")

    # firmalar
    cur.execute("""CREATE TABLE IF NOT EXISTS firmalar(
    id INTEGER PRIMARY KEY,
    isim TEXT
    )""")

    # ürün
    cur.execute("""CREATE TABLE IF NOT EXISTS urun(
    id INTEGER PRIMARY KEY,
    firma_id INTEGER,
    barkod TEXT,
    isim TEXT,
    adet INTEGER,
    kritik INTEGER
    )""")

    # hareket
    cur.execute("""CREATE TABLE IF NOT EXISTS hareket(
    id INTEGER PRIMARY KEY,
    barkod TEXT,
    tip TEXT,
    adet INTEGER,
    tarih TEXT
    )""")

    # cari
    cur.execute("""CREATE TABLE IF NOT EXISTS cari(
    id INTEGER PRIMARY KEY,
    isim TEXT,
    borc INTEGER,
    alacak INTEGER
    )""")

    # admin
    cur.execute("SELECT * FROM users WHERE username='admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users VALUES(NULL,'admin','123','admin')")

    con.commit()
    con.close()

init()

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=request.form["u"]
        p=request.form["p"]

        con=db()
        cur=con.cursor()
        cur.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p))
        user=cur.fetchone()
        con.close()

        if user:
            session["user"]=u
            session["role"]=user[3]
            return redirect("/panel")

    return """
    <h2>LEVEL 4 ERP</h2>
    <form method=post>
    <input name=u placeholder=Kullanıcı>
    <input name=p type=password placeholder=Şifre>
    <button>Giriş</button>
    </form>
    """

# PANEL
@app.route("/panel", methods=["GET","POST"])
def panel():
    if not session.get("user"):
        return redirect("/")

    con=db()
    cur=con.cursor()

    if request.method=="POST":
        isim=request.form["isim"]
        adet=int(request.form["adet"])
        kritik=int(request.form["kritik"])

        barkod="HER-"+str(datetime.datetime.now().timestamp())

        cur.execute("INSERT INTO urun VALUES(NULL,1,?,?,?,?)",
                    (barkod,isim,adet,kritik))
        con.commit()

    urunler=cur.execute("SELECT * FROM urun").fetchall()

    html="""
    <h2>STOK ERP</h2>

    <form method=post>
    Ürün <input name=isim>
    Adet <input name=adet>
    Kritik <input name=kritik>
    <button>Ekle</button>
    </form>

    <hr>
    <a href="/cari">Cari</a> |
    <a href="/rapor">Rapor</a> |
    <a href="/yedek">Yedek</a>

    <hr>
    """

    for u in urunler:
        renk="red" if u[4]<=u[5] else "green"

        html+=f"""
        <div style='border:1px solid #ccc;margin:5px;padding:5px;background:{renk}'>
        {u[3]} | {u[2]} | Adet: {u[4]}
        <a href='/islem/{u[2]}/giris'>➕</a>
        <a href='/islem/{u[2]}/cikis'>➖</a>
        </div>
        """

    return html

# İŞLEM
@app.route("/islem/<kod>/<tip>")
def islem(kod,tip):
    con=db()
    cur=con.cursor()

    cur.execute("SELECT adet FROM urun WHERE barkod=?", (kod,))
    a=cur.fetchone()[0]

    yeni=a+1 if tip=="giris" else max(a-1,0)

    cur.execute("UPDATE urun SET adet=? WHERE barkod=?", (yeni,kod))
    cur.execute("INSERT INTO hareket VALUES(NULL,?,?,?,?)",
                (kod,tip,1,str(datetime.datetime.now())))
    con.commit()
    con.close()

    return redirect("/panel")

# CARİ
@app.route("/cari", methods=["GET","POST"])
def cari():
    con=db()
    cur=con.cursor()

    if request.method=="POST":
        cur.execute("INSERT INTO cari VALUES(NULL,?,?,?)",
                    (request.form["isim"],0,0))
        con.commit()

    data=cur.execute("SELECT * FROM cari").fetchall()

    html="<h2>Cari</h2><form method=post><input name=isim><button>Ekle</button></form><hr>"

    for c in data:
        html+=f"{c[1]} | Borç:{c[2]} | Alacak:{c[3]}<br>"

    return html

# RAPOR
@app.route("/rapor")
def rapor():
    con=db()
    cur=con.cursor()

    toplam=cur.execute("SELECT SUM(adet) FROM urun").fetchone()[0]
    hareket=cur.execute("SELECT COUNT(*) FROM hareket").fetchone()[0]

    return f"<h2>Toplam Stok: {toplam}<br>Hareket: {hareket}</h2>"

# YEDEK
@app.route("/yedek")
def yedek():
    shutil.copy(DB,"backup.db")
    return send_file("backup.db",as_attachment=True)

# RUN
if __name__=="__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)
