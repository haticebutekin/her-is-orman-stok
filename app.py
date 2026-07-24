from flask import Flask, request, redirect, session, render_template_string, jsonify, send_file
import sqlite3
import random
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "HER_IS_STOK_PRO_SECRET"


# =========================
# DATABASE
# =========================

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
        barcode TEXT UNIQUE,
        price REAL,
        stock INTEGER,
        type TEXT,
        size TEXT,
        class_name TEXT,
        hg TEXT,
        mat TEXT,
        color TEXT,
        depot INTEGER
    )
    """)


    c.execute("""
    CREATE TABLE IF NOT EXISTS stock_moves(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        depot INTEGER,
        quantity INTEGER,
        action TEXT,
        username TEXT,
        date TEXT
    )
    """)


    c.execute("""
    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        action TEXT,
        date TEXT
    )
    """)


    c.execute("""
    CREATE TABLE IF NOT EXISTS sales(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        total REAL,
        payment TEXT,
        username TEXT,
        date TEXT
    )
    """)


    # admin
    if not c.execute("SELECT * FROM users").fetchone():

        c.execute("""
        INSERT INTO users(username,password,role)
        VALUES('admin','1234','admin')
        """)


    # depo

    if not c.execute("SELECT * FROM depots").fetchone():

        c.execute("""
        INSERT INTO depots(name)
        VALUES('Ana Depo')
        """)


    con.commit()
    con.close()



init_db()



# =========================
# YARDIMCI
# =========================

def barcode_create():

    return str(random.randint(100000000000,999999999999))


def log(text):

    con=db()

    con.execute("""
    INSERT INTO logs(username,action,date)
    VALUES(?,?,?)
    """,
    (
        session.get("user"),
        text,
        datetime.now()
    ))

    con.commit()
    con.close()



# =========================
# LOGIN
# =========================


@app.route("/", methods=["GET","POST"])
def login():

    if request.method=="POST":

        username=request.form["username"]
        password=request.form["password"]


        con=db()

        user=con.execute("""
        SELECT * FROM users
        WHERE username=? AND password=?
        """,
        (username,password)).fetchone()


        con.close()


        if user:

            session["user"]=username
            session["role"]=user[3]

            log("Giriş yaptı")

            return redirect("/panel")


    return """

    <html>

    <body style="
    background:#111;
    color:white;
    text-align:center;
    font-family:Arial">

    <h1>HER İŞ STOK PRO</h1>

    <form method="post">

    <input name="username"
    placeholder="Kullanıcı"><br><br>

    <input name="password"
    type="password"
    placeholder="Şifre"><br><br>


    <button>
    Giriş
    </button>

    </form>

    </body>

    </html>

    """




# =========================
# PANEL
# =========================


@app.route("/panel")
def panel():

    if "user" not in session:
        return redirect("/")


    return """

    <html>

    <body style="
    background:#0f172a;
    color:white;
    font-family:Arial">


    <h1>🚀 STOK PRO PANEL</h1>


    <a href="/product_add">
    ➕ Ürün Ekle
    </a>
    <br><br>


    <a href="/products">
    📦 Ürünler
    </a>
    <br><br>


    <a href="/depot">
    🏬 Depolar
    </a>
    <br><br>


    <a href="/logs">
    👤 Kim Ne Yaptı
    </a>


    </body>

    </html>

    """



# =========================
# DEPO
# =========================


@app.route("/depot",methods=["GET","POST"])
def depot():

    con=db()


    if request.method=="POST":

        con.execute("""
        INSERT INTO depots(name)
        VALUES(?)
        """,
        (request.form["name"],))

        con.commit()


    data=con.execute("""
    SELECT * FROM depots
    """).fetchall()


    con.close()


    html="""

    <h2>Depolar</h2>


    <form method=post>

    <input name=name
    placeholder="Depo adı">

    <button>Ekle</button>

    </form>

    """


    for d in data:

        html+=f"""
        <p>
        🏬 {d[1]}
        </p>
        """


    return html





# =========================
# ÜRÜN EKLE
# =========================


@app.route("/product_add",methods=["GET","POST"])
def product_add():


    if request.method=="POST":


        barkod=barcode_create()


        data=(

        request.form["name"],
        barkod,
        request.form["price"],
        request.form["stock"],
        request.form["type"],
        request.form["size"],
        request.form["class_name"],
        request.form["hg"],
        request.form["mat"],
        request.form["color"],
        request.form["depot"]

        )


        con=db()


        con.execute("""
        INSERT INTO products
        (
        name,barcode,price,stock,
        type,size,class_name,
        hg,mat,color,depot
        )

        VALUES
        (?,?,?,?,?,?,?,?,?,?,?)
        """,data)



        con.commit()
        con.close()


        log(
        "Yeni ürün eklendi Barkod:"+barkod
        )


        return f"""
        Ürün kaydedildi<br>
        Barkod:{barkod}
        <br>
        <a href="/panel">
        Panel
        </a>
        """


    return """

<h2>Ürün Kartı</h2>


<form method=post>


Ürün Adı
<input name=name><br>


Fiyat
<input name=price><br>


Adet
<input name=stock><br>


Mal Cinsi
<input name=type><br>


Ebat (mm)
<input name=size><br>


Sınıf
<input name=class_name><br>



HG

<select name=hg>

<option>Evet</option>
<option>Hayır</option>

</select>
<br>


MAT

<select name=mat>

<option>Evet</option>
<option>Hayır</option>

</select>

<br>


Renk

<input name=color>


<br>


Depo No

<input name=depot value="1">


<br>


<button>
Kaydet
</button>


</form>


"""
   # =========================
# ÜRÜN LİSTE
# =========================

@app.route("/products")
def products():

    con=db()

    data=con.execute("""
    SELECT * FROM products
    """).fetchall()

    con.close()


    html="""

    <h2>📦 Ürünler</h2>

    """

    for p in data:

        html+=f"""

        <div style="
        background:#222;
        color:white;
        padding:15px;
        margin:10px;
        border-radius:10px">


        <b>{p[1]}</b><br>

        Barkod:
        {p[2]}<br>

        Ebat:
        {p[6]} mm<br>

        HG:
        {p[8]} |

        MAT:
        {p[9]}<br>


        Renk:
        {p[10]}<br>


        Stok:
        {p[4]}

        <br><br>

        <a href="/label/{p[0]}">
        🏷 Etiket
        </a>


        </div>

        """


    return html





# =========================
# BARKOD KAMERA
# =========================


@app.route("/scan")
def scan():

    return """

<html>

<head>

<script src="
https://unpkg.com/html5-qrcode
"></script>

</head>


<body style="
background:#111;
color:white;
text-align:center">


<h2>
📷 Barkod Oku
</h2>


<div id="reader"
style="
width:300px;
margin:auto">
</div>



<form id="form"
method="post"
action="/scan_result">

<input type="hidden"
id="barcode"
name="barcode">

</form>



<script>


function success(code)
{

document.getElementById(
"barcode"
).value=code;


document.getElementById(
"form"
).submit();


}


let scanner =
new Html5QrcodeScanner(
"reader",
{
fps:10,
qrbox:250
}
);


scanner.render(success);


</script>


</body>

</html>


"""




# =========================
# OKUTULAN ÜRÜN
# =========================


@app.route("/scan_result",
methods=["POST"])
def scan_result():


    barcode=request.form["barcode"]


    con=db()


    p=con.execute("""
    SELECT * FROM products
    WHERE barcode=?
    """,
    (barcode,)).fetchone()


    con.close()



    if not p:

        return "Ürün bulunamadı"



    return f"""

<h2>Ürün</h2>


Ürün:
{p[1]}
<br>

Barkod:
{p[2]}

<br>

Ebat:
{p[6]} mm

<br>

HG:
{p[8]}

<br>

MAT:
{p[9]}

<br>

Stok:
{p[4]}


<br><br>


<a href="/cash/{p[0]}">

Sepete Ekle

</a>


"""





# =========================
# SEPET
# =========================

cart=[]



@app.route("/cash/<int:id>")
def cash(id):


    con=db()

    p=con.execute("""
    SELECT * FROM products
    WHERE id=?
    """,
    (id,)).fetchone()


    con.close()



    if p:

        cart.append({

        "id":p[0],
        "name":p[1],
        "price":p[3]

        })


    return redirect("/cart")






@app.route("/cart")
def cart_page():


    total=0

    html="""

<h2>🛒 KASA</h2>

"""


    for x in cart:

        total+=x["price"]


        html+=f"""

{x['name']}
-
{x['price']} TL

<br>

"""


    html+=f"""

<h3>
Toplam:
{total} TL
</h3>



<form method="post"
action="/checkout">


Ödeme:

<select name=payment>

<option>Nakit</option>

<option>Kart</option>


</select>


<br><br>


<button>
Satışı Bitir
</button>


</form>


"""


    return html







# =========================
# SATIŞ TAMAMLA
# =========================


@app.route("/checkout",
methods=["POST"])
def checkout():


    payment=request.form["payment"]


    con=db()


    for item in cart:


        con.execute("""
        UPDATE products

        SET stock=stock-1

        WHERE id=?
        """,
        (item["id"],))



        con.execute("""
        INSERT INTO stock_moves
        (
        product_id,
        depot,
        quantity,
        action,
        username,
        date
        )

        VALUES(?,?,?,?,?,?)
        """,
        (

        item["id"],
        1,
        -1,
        "Satış",
        session["user"],
        datetime.now()

        ))



    total=sum(
    x["price"]
    for x in cart
    )



    con.execute("""
    INSERT INTO sales
    (
    total,
    payment,
    username,
    date
    )

    VALUES(?,?,?,?)
    """,

    (
    total,
    payment,
    session["user"],
    datetime.now()
    ))



    con.commit()

    con.close()



    log(
    "Satış yaptı"
    )


    cart.clear()



    return """

<h2>
✅ Satış Tamamlandı
</h2>

<a href="/panel">
Panel
</a>

"""






# =========================
# LOG
# =========================


@app.route("/logs")
def logs():


    con=db()

    data=con.execute("""
    SELECT * FROM logs
    ORDER BY id DESC
    """).fetchall()


    con.close()


    html="<h2>👤 İşlem Geçmişi</h2>"


    for l in data:

        html+=f"""

<p>

<b>{l[1]}</b>

-
{l[2]}

-
{l[3]}

</p>

"""


    return html







# =========================
# ETİKET
# =========================


@app.route("/label/<int:id>")
def label(id):

    return """

<h2>
🏷 Etiket Sistemi Hazır
</h2>


QR + Barkod PDF modülü aktif edilecek.


"""






# =========================

if __name__=="__main__":

    app.run(
    host="0.0.0.0",
    port=10000
    ) 
