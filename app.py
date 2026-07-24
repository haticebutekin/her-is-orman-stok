from flask import Flask, request, redirect, session
import sqlite3
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "HER_IS_STOK_PRO"


# --------------------
# DATABASE
# --------------------

def db():
    return sqlite3.connect("stok.db")


def setup():

    con=db()
    c=con.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    password TEXT,
    role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS depots(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT
    )
    """)


    c.execute("""
    CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    type TEXT,
    size TEXT,
    class_name TEXT,
    surface TEXT,
    color TEXT,
    barcode TEXT UNIQUE,
    stock INTEGER,
    depot INTEGER
    )
    """)


    c.execute("""
    CREATE TABLE IF NOT EXISTS logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user TEXT,
    action TEXT,
    date TEXT
    )
    """)


    # kullanıcı

    if not c.execute("SELECT * FROM users").fetchone():

        c.execute("""
        INSERT INTO users
        VALUES(NULL,'admin','1234','admin')
        """)

        c.execute("""
        INSERT INTO users
        VALUES(NULL,'depocu','1234','depo')
        """)



    # 8 depo

    depolar=[
    "MDF SATIŞ DEPOSU",
    "LAMİNANT DEPOSU",
    "KAPI DEPOSU",
    "HGLOSS DEPOSU (MORAY YANI)",
    "SÜTÇÜ YANI",
    "HELVACI YANI",
    "RÖTBALANSÇI YANI",
    "KESİMHANE"
    ]


    if not c.execute("SELECT * FROM depots").fetchone():

        for d in depolar:
            c.execute(
            "INSERT INTO depots(name) VALUES(?)",
            (d,)
            )


    con.commit()
    con.close()



setup()



def barkod():

    return str(
        random.randint(
        100000000000,
        999999999999)
    )



def log(islem):

    con=db()

    con.execute("""
    INSERT INTO logs
    VALUES(NULL,?,?,?)
    """,
    (
    session.get("user"),
    islem,
    datetime.now()
    ))

    con.commit()
    con.close()



# --------------------
# LOGIN
# --------------------

@app.route("/",methods=["GET","POST"])
def login():

    if request.method=="POST":

        u=request.form["user"]
        p=request.form["pass"]


        con=db()

        data=con.execute("""
        SELECT * FROM users
        WHERE username=? AND password=?
        """,
        (u,p)).fetchone()

        con.close()


        if data:

            session["user"]=u
            session["role"]=data[3]

            return redirect("/panel")


    return """

    <h2>HER İŞ STOK PRO</h2>

    <form method=post>

    Kullanıcı:
    <input name=user><br>

    Şifre:
    <input name=pass><br>

    <button>
    Giriş
    </button>

    </form>

    """



# --------------------
# PANEL
# --------------------

@app.route("/panel")
def panel():

    return """

    <h1>STOK PRO</h1>

    <a href="/urun">Ürün Ekle</a><br>
    <a href="/liste">Ürünler</a><br>
    <a href="/log">İşlemler</a>

    """



# --------------------
# ÜRÜN EKLE
# --------------------

@app.route("/urun",methods=["GET","POST"])
def urun():

    con=db()

    depolar=con.execute(
    "SELECT * FROM depots"
    ).fetchall()


    if request.method=="POST":


        kod=barkod()


        con.execute("""
        INSERT INTO products
        VALUES(NULL,?,?,?,?,?,?,?,?,?)
        """,
        (

        request.form["name"],
        request.form["type"],
        request.form["size"],
        request.form["class"],
        request.form["surface"],
        request.form["color"],
        kod,
        request.form["stock"],
        request.form["depot"]

        ))


        con.commit()

        log(
        "Yeni ürün eklendi Barkod:"+kod
        )


        return "Kaydedildi Barkod:"+kod



    sec=""

    for d in depolar:

        sec+=f"""
        <option value="{d[0]}">
        {d[1]}
        </option>
        """



    return f"""

<h2>Ürün Kartı</h2>


<form method=post>


Mal adı:
<input name=name><br>


Cins:
<input name=type><br>


Ebat mm:
<input name=size><br>


Sınıf:
<input name=class><br>


HG / MAT:

<select name=surface>

<option>HG</option>

<option>MAT</option>

</select>

<br>


Renk:
<input name=color>

<br>


Adet:
<input name=stock>


<br>


Depo:

<select name=depot>

{sec}

</select>


<br>


<button>
Kaydet
</button>


</form>


"""



# --------------------
# LİSTE
# --------------------

@app.route("/liste")
def liste():

    con=db()

    data=con.execute(
    "SELECT * FROM products"
    ).fetchall()


    html="<h2>Ürünler</h2>"


    for p in data:

        html+=f"""

        {p[1]}
        |
        {p[7]}
        |
        {p[5]}
        |
        {p[8]}
        adet

        <hr>

        """


    return html




@app.route("/log")
def logs():

    con=db()

    data=con.execute(
    "SELECT * FROM logs"
    ).fetchall()


    html="<h2>Kim Ne Yaptı</h2>"


    for x in data:

        html+=f"""
        {x[1]}
        -
        {x[2]}
        -
        {x[3]}
        <br>
        """


    return html




if __name__=="__main__":

    app.run(
    host="0.0.0.0",
    port=10000
    )
