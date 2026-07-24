from flask import Flask, request, redirect, session, send_file
import sqlite3
import random
from datetime import datetime
import os


app = Flask(__name__)
app.secret_key = "HERIS_STOK_PRO_SECRET"


# =====================
# DATABASE
# =====================

def db():
    return sqlite3.connect("stok.db")


def init_db():

    con = db()
    c = con.cursor()


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
        barcode TEXT,
        stock INTEGER,
        depot TEXT
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


    # Kullanıcı

    if c.execute(
        "SELECT * FROM users"
    ).fetchone() is None:

        c.execute("""
        INSERT INTO users
        (username,password,role)
        VALUES
        ('admin','1234','admin')
        """)


        c.execute("""
        INSERT INTO users
        (username,password,role)
        VALUES
        ('depocu','1234','depo')
        """)



    # Depolar

    depolar=[
        "DEPO 1",
        "DEPO 2",
        "DEPO 3",
        "DEPO 4",
        "DEPO 5",
        "DEPO 6",
        "DEPO 7",
        "DEPO 8"
    ]


    for d in depolar:

        kontrol=c.execute(
            "SELECT * FROM depots WHERE name=?",
            (d,)
        ).fetchone()


        if kontrol is None:

            c.execute("""
            INSERT INTO depots(name)
            VALUES(?)
            """,
            (d,))



    con.commit()
    con.close()



init_db()



# =====================
# YARDIMCI
# =====================

def barkod():

    return str(
        random.randint(
            100000000000,
            999999999999
        )
    )



def log(islem):

    con=db()

    con.execute("""
    INSERT INTO logs
    (user,action,date)
    VALUES(?,?,?)
    """,
    (
    session.get("user"),
    islem,
    datetime.now()
    ))

    con.commit()
    con.close()



# =====================
# LOGIN
# =====================

@app.route("/",methods=["GET","POST"])
def login():


    if request.method=="POST":


        username=request.form["username"]
        password=request.form["password"]


        con=db()


        user=con.execute("""
        SELECT * FROM users
        WHERE username=? AND password=?
        """,
        (
        username,
        password
        )).fetchone()


        con.close()


        if user:

            session["user"]=user[1]
            session["role"]=user[3]

            return redirect("/panel")



    return """

    <h1>
    HER İŞ STOK PRO
    </h1>


    <form method="post">

    Kullanıcı:
    <input name="username">

    <br><br>

    Şifre:
    <input name="password" type="password">

    <br><br>

    <button>
    GİRİŞ
    </button>


    </form>

    """



# =====================
# PANEL
# =====================

@app.route("/panel")
def panel():

    if "user" not in session:
        return redirect("/")


    return """

<h1>
HER İŞ STOK PRO
</h1>


<a href="/urun">
Yeni Ürün
</a>

<br><br>


<a href="/liste">
Ürün Liste
</a>


<br><br>


<a href="/cikis">
Depo Çıkış
</a>


<br><br>


<a href="/log">
Hareketler
</a>


"""

# =====================
# ÜRÜN EKLE
# =====================

@app.route("/urun", methods=["GET","POST"])
def urun():

    if "user" not in session:
        return redirect("/")


    con=db()


    depolar=con.execute("""
    SELECT name FROM depots
    """).fetchall()



    if request.method=="POST":


        yeni=barkod()


        con.execute("""
        INSERT INTO products
        (
        name,
        type,
        size,
        class_name,
        surface,
        color,
        barcode,
        stock,
        depot
        )
        VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (
        request.form["name"],
        request.form["type"],
        request.form["size"],
        request.form["class_name"],
        request.form["surface"],
        request.form["color"],
        yeni,
        request.form["stock"],
        request.form["depot"]
        ))


        con.commit()
        con.close()


        log(
        "Yeni ürün eklendi barkod: "+yeni
        )


        return f"""

        <h2>
        Ürün Kaydedildi
        </h2>

        Barkod:
        {yeni}

        <br><br>

        <a href="/panel">
        Panel
        </a>

        """



    secenek=""


    for d in depolar:

        secenek += f"""

        <option>
        {d[0]}
        </option>

        """



    con.close()



    return f"""

<h2>
YENİ ÜRÜN
</h2>


<form method="post">


Mal Adı:

<input name="name">

<br><br>


Mal Cinsi:

<input name="type">

<br><br>


Ebat (mm):

<input name="size">

<br><br>


Sınıf:

<input name="class_name">

<br><br>


Yüzey:

<select name="surface">

<option>
HG
</option>

<option>
MAT
</option>

</select>


<br><br>


Renk:

<input name="color">


<br><br>


Adet:

<input name="stock">


<br><br>


Depo:

<select name="depot">

{secenek}

</select>


<br><br>


<button>
KAYDET
</button>


</form>

"""




# =====================
# ÜRÜN LİSTE
# =====================

@app.route("/liste")
def liste():

    if "user" not in session:
        return redirect("/")


    con=db()


    urunler=con.execute("""
    SELECT * FROM products
    ORDER BY id DESC
    """).fetchall()


    con.close()


    html="""

<h2>
STOK LİSTESİ
</h2>

"""


    for u in urunler:


        html+=f"""

<hr>


<b>{u[1]}</b>

<br>

Cins:
{u[2]}

<br>

Ebat:
{u[3]} mm

<br>

Sınıf:
{u[4]}

<br>

Yüzey:
{u[5]}

<br>

Renk:
{u[6]}

<br>

Barkod:
{u[7]}

<br>

Stok:
{u[8]}

<br>

Depo:
{u[9]}


"""



    return html





# =====================
# DEPO ÇIKIŞ
# =====================

@app.route("/cikis",methods=["GET","POST"])
def cikis():


    if request.method=="POST":


        bark=request.form["barcode"]

        adet=int(
            request.form["adet"]
        )


        con=db()


        urun=con.execute("""
        SELECT * FROM products
        WHERE barcode=?
        """,
        (bark,)
        ).fetchone()



        if urun is None:

            con.close()

            return "Barkod bulunamadı"



        if urun[8] < adet:

            con.close()

            return "Yetersiz stok"



        con.execute("""
        UPDATE products

        SET stock=stock-?

        WHERE id=?

        """,
        (
        adet,
        urun[0]
        ))


        con.commit()
        con.close()



        log(
        f"{urun[1]} {adet} adet çıkış"
        )


        return """

<h2>
Çıkış Tamamlandı
</h2>

<a href="/panel">
Panel
</a>

"""



    return """

<h2>
DEPO ÇIKIŞ
</h2>


<form method="post">


Barkod:

<input name="barcode"
autofocus>


<br><br>


Adet:

<input name="adet">


<br><br>


<button>
ÇIKIŞ YAP
</button>


</form>


"""
    # =====================
# HAREKET LOG
# =====================

@app.route("/log")
def hareketler():

    if "user" not in session:
        return redirect("/")


    con=db()

    kayitlar=con.execute("""
    SELECT * FROM logs
    ORDER BY id DESC
    """).fetchall()

    con.close()


    html="""

<h2>
KİM NE YAPTI
</h2>

"""


    for k in kayitlar:

        html+=f"""

<hr>

Kullanıcı:
{k[1]}

<br>

İşlem:
{k[2]}

<br>

Tarih:
{k[3]}

"""


    return html




# =====================
# KAMERA BARKOD
# =====================

@app.route("/kamera")
def kamera():

    return """

<script src="https://unpkg.com/html5-qrcode"></script>


<h2>
KAMERA BARKOD OKUTMA
</h2>


<div id="reader"
style="width:300px">
</div>


<script>


function okundu(kod){

window.location.href =
"/barkod/"+kod;

}


let scan =
new Html5QrcodeScanner(
"reader",
{
fps:10,
qrbox:250
}
);


scan.render(okundu);


</script>

"""





@app.route("/barkod/<kod>")
def barkod_bul(kod):


    con=db()


    urun=con.execute("""
    SELECT * FROM products
    WHERE barcode=?
    """,
    (kod,)
    ).fetchone()


    con.close()



    if urun is None:

        return """

<h2>
Ürün bulunamadı
</h2>

"""



    return f"""

<h2>
ÜRÜN BULUNDU
</h2>


Mal:
{urun[1]}

<br>

Cins:
{urun[2]}

<br>

Ebat:
{urun[3]} mm

<br>

HG/MAT:
{urun[5]}

<br>

Renk:
{urun[6]}

<br>

Depo:
{urun[9]}

<br>

Stok:
{urun[8]}


"""





# =====================
# ETİKET SAYFASI
# =====================

@app.route("/etiket/<int:id>")
def etiket(id):


    con=db()


    urun=con.execute("""
    SELECT * FROM products
    WHERE id=?
    """,
    (id,)
    ).fetchone()


    con.close()


    if urun is None:

        return "Ürün yok"



    return f"""

<h2>
ETİKET
</h2>


HER İŞ STOK PRO


<br><br>


Mal:

{urun[1]}


<br>


Ebat:

{urun[3]} mm


<br>


HG/MAT:

{urun[5]}


<br>


Renk:

{urun[6]}


<br>


BARKOD:

<b>
{urun[7]}
</b>


"""





# =====================
# ÇALIŞTIR
# =====================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000
    )
