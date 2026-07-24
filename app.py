from flask import Flask, request, redirect, session
import sqlite3
import random
import json
import qrcode
import barcode
from barcode.writer import ImageWriter
from reportlab.pdfgen import canvas
from flask import send_file
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "HER_IS_STOK_PRO_2026"


# =====================
# DATABASE
# =====================

def db():
    return sqlite3.connect("stok.db")


def init():

    con = db()
    c = con.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        quantity INTEGER,
        status TEXT
)
""")
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS requests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        quantity INTEGER,
        status TEXT
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
        username TEXT,
        action TEXT,
        date TEXT
    )
    """)


    # kullanıcılar

    if c.execute("SELECT * FROM users").fetchone() is None:

        c.execute("""
        INSERT INTO users(username,password,role)
        VALUES('admin','1234','admin')
        """)


        c.execute("""
        INSERT INTO users(username,password,role)
        VALUES('depocu','1234','depo')
        """)



    # 8 depo

    depolar=[
        "MDF SATIS DEPOSU",
        "LAMINANT DEPOSU",
        "KAPI DEPOSU",
        "HGLOSS DEPOSU",
        "SUTCUNUN YANI",
        "HELVACI YANI",
        "ROTBALANSCI YANI",
        "KESIMHANE"
    ]


    if c.execute("SELECT * FROM depots").fetchone() is None:

        for depo in depolar:

            c.execute("""
            INSERT INTO depots(name)
            VALUES(?)
            """,(depo,))


    con.commit()
    con.close()



init()



# =====================
# YARDIMCI
# =====================


def yeni_barkod():

    return str(
        random.randint(
            100000000000,
            999999999999
        )
    )



def logla(islem):

    con=db()

    con.execute("""
    INSERT INTO logs(username,action,date)
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


        kullanici=request.form["username"]
        sifre=request.form["password"]


        con=db()


        user=con.execute("""
        SELECT * FROM users
        WHERE username=? AND password=?
        """,
        (
        kullanici,
        sifre
        )).fetchone()


        con.close()



        if user:

            session["user"]=user[1]
            session["role"]=user[3]

            return redirect("/panel")



    return """
    <h1>HER IS STOK PRO</h1>

    <form method="post">

    Kullanici:
    <input name="username"><br><br>

    Sifre:
    <input name="password"
    type="password"><br><br>

    <button>
    GIRIS
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
    <h1>HER IS STOK PRO</h1>

    <a href="/urun">Yeni Urun</a><br><br>

    <a href="/liste">Urunler</a><br><br>
    <a href="/etiket/{u[0]}">
    🏷️ ETİKET BAS
    </a>
    <a href="/cikis">Depo Cikis</a><br><br>

    <a href="/log">Kim Ne Yapti</a>

    """



# =====================
# URUN EKLE
# =====================


@app.route("/urun",methods=["GET","POST"])
def urun():


    con=db()


    depolar=con.execute("""
    SELECT * FROM depots
    """).fetchall()



    if request.method=="POST":


        barkod=yeni_barkod()


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
        barkod,
        request.form["stock"],
        request.form["depot"]
        ))


        con.commit()

        con.close()


        logla(
        "Yeni urun eklendi "+barkod
        )


        return "Kaydedildi Barkod:"+barkod



    secenek=""


    for d in depolar:

        secenek+=f"""
        <option value="{d[0]}">
        {d[1]}
        </option>
        """



    con.close()


    return f"""

<h2>URUN KARTI</h2>


<form method="post">


Mal Adi:
<input name="name"><br>


Mal Cinsi:
<input name="type"><br>


Ebat mm:
<input name="size"><br>


Sinifi:
<input name="class_name"><br>


HG / MAT:

<select name="surface">

<option>HG</option>

<option>MAT</option>

</select>


<br>


Renk:

<input name="color">

<br>


Adet:

<input name="stock">


<br>


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
# URUN LISTE
# =====================

@app.route("/liste")
def liste():

    con=db()

    urunler=con.execute("""
    SELECT * FROM products
    """).fetchall()

    con.close()


    sayfa="""

<h2>URUN LISTESI</h2>

"""


    for u in urunler:

        sayfa+=f"""

<hr>

<b>Mal:</b> {u[1]}<br>

Cins:
{u[2]}<br>

Ebat:
{u[3]} mm<br>

Sinif:
{u[4]}<br>

Yuzey:
{u[5]}<br>

Renk:
{u[6]}<br>

Barkod:
{u[7]}<br>

Stok:
{u[8]}

<br>

<a href="/etiket/{u[0]}">
Etiket
</a>

"""


    return sayfa




# =====================
# DEPO CIKIS
# =====================


@app.route("/cikis",methods=["GET","POST"])
def cikis():

    if request.method=="POST":

        barkod=request.form["barcode"]
        adet=int(request.form["adet"])
        talep=int(request.form["talep"])


        con=db()


        urun=con.execute("""
        SELECT * FROM products
        WHERE barcode=?
        """,
        (barkod,)).fetchone()



        talep_urun=con.execute("""
        SELECT * FROM requests
        WHERE id=?
        """,
        (talep,)).fetchone()



        if urun is None:

            con.close()

            return "❌ Barkod bulunamadı"



        if talep_urun is None:

            con.close()

            return "❌ Geçersiz çıkış talebi"



        # YANLIŞ MAL KONTROLÜ

        if urun[0] != talep_urun[1]:

            con.close()

            return """
            <h2 style='color:red'>
            ❌ YANLIŞ MALZEME!
            </h2>

            Çıkış engellendi.
            """



        if urun[8] < adet:

            con.close()

            return "❌ Yetersiz stok"



        con.execute("""
        UPDATE products

        SET stock=stock-?

        WHERE id=?
        """,
        (
        adet,
        urun[0]
        ))



        con.execute("""
        UPDATE requests
        SET status='Tamamlandı'
        WHERE id=?
        """,
        (talep,))


        con.commit()
        con.close()



        logla(
        f"{urun[1]} {adet} adet çıkış yaptı"
        )


        return """
        <h2>
        ✅ Doğru ürün çıktı
        </h2>
        """



    return """

<h2>
DEPO ÇIKIŞ
</h2>


<form method="post">


Talep No:

<input name="talep">


<br><br>


Barkod:

<input name="barcode"
autofocus>


<br><br>


Adet:

<input name="adet">


<br><br>


<button>
OKUT VE ÇIK
</button>


</form>

"""

@app.route("/cikis",methods=["POST"])
def cikis_yap():


    barkod=request.form["barcode"]

    adet=int(
    request.form["adet"]
    )


    con=db()


    urun=con.execute("""
    SELECT * FROM products
    WHERE barcode=?
    """,
    (barkod,)
    ).fetchone()



    if urun is None:

        con.close()

        return "Urun bulunamadi"



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



    logla(
    f"{urun[1]} {adet} adet cikis"
    )



    return """

<h2>
CIKIS TAMAMLANDI
</h2>

<a href="/kamera">
📷 Kamera Barkod
</a>
    
<a href="/panel">
Panel
</a>

"""



# =====================
# LOG
# =====================

@app.route("/talep/<int:id>/<int:adet>")
def talep(id,adet):

    con=db()

    con.execute("""
    INSERT INTO requests
    (product_id,quantity,status)

    VALUES(?,?,?)
    """,
    (
    id,
    adet,
    "Bekliyor"
    ))

    con.commit()


    no=con.execute("""
    SELECT last_insert_rowid()
    """).fetchone()[0]


    con.close()


    return f"""

<h2>
Çıkış Talebi Oluşturuldu
</h2>

Talep No:

<b>{no}</b>

"""

@app.route("/log")
def log_ekran():

    con=db()

    kayit=con.execute("""
    SELECT * FROM logs
    ORDER BY id DESC
    """).fetchall()


    con.close()


    html="""

<h2>KIM NE YAPTI</h2>

"""


    for k in kayit:

        html+=f"""

<p>

Kullanici:
{k[1]}

<br>

Islem:
{k[2]}

<br>

Tarih:
{k[3]}

</p>

<hr>

"""


    return html




# =====================
# ETIKET
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

        return "Urun yok"



    return f"""

<h2>ETIKET BILGISI</h2>


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

<h3>
{urun[7]}
</h3>


"""





# =====================
# CALISTIRMA
# =====================

# =====================
# KAMERA BARKOD OKUMA
# =====================

@app.route("/kamera")
def kamera():

    return """

<!DOCTYPE html>
<html>

<head>

<script src="https://unpkg.com/html5-qrcode"></script>

</head>


<body>

<h2>
Kamera Barkod Okuma
</h2>


<div id="reader"
style="width:300px">
</div>


<script>


function barkod_okundu(code)
{

window.location.href =
"/barkod_bul/" + code;

}



let scanner =
new Html5QrcodeScanner(
"reader",
{
fps:10,
qrbox:250
}
);



scanner.render(
barkod_okundu
);


</script>


</body>

</html>

"""





@app.route("/barkod_bul/<kod>")
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
        URUN BULUNAMADI
        </h2>

        """



    return f"""

<h2>
URUN BULUNDU
</h2>


Mal:

{urun[1]}

<br><br>


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


<hr>


<a href="/cikis">

CIKIS EKRANI

</a>

"""


# =====================
# BARKOD QR ETIKET
# =====================

@app.route("/etiket/<int:id>")
def etiket(id):

    con=db()

    urun=con.execute("""
    SELECT * FROM products
    WHERE id=?
    """,(id,)).fetchone()

    con.close()


    if urun is None:
        return "Urun bulunamadi"


    barkod=urun[7]


    # QR OLUSTUR

    qr=qrcode.make(barkod)

    qr_dosya=f"qr_{barkod}.png"

    qr.save(qr_dosya)



    # BARKOD OLUSTUR

    barkod_img=barcode.get(
        "code128",
        barkod,
        writer=ImageWriter()
    )


    barkod_dosya=barkod_img.save(
        f"barcode_{barkod}"
    )



    # PDF

    pdf_adi=f"etiket_{barkod}.pdf"


    p=canvas.Canvas(pdf_adi)


    p.setFont(
        "Helvetica",
        12
    )


    p.drawString(
        40,750,
        "HER IS STOK PRO"
    )


    p.drawString(
        40,720,
        "Mal: "+urun[1]
    )


    p.drawString(
        40,700,
        "Cins: "+urun[2]
    )


    p.drawString(
        40,680,
        "Ebat: "+urun[3]+" mm"
    )


    p.drawString(
        40,660,
        "HG/MAT: "+urun[5]
    )


    p.drawString(
        40,640,
        "Renk: "+urun[6]
    )


    p.drawString(
        40,620,
        "Barkod: "+barkod
    )


    p.drawImage(
        qr_dosya,
        40,
        450,
        120,
        120
    )


    p.drawImage(
        barkod_dosya+".png",
        200,
        480,
        250,
        80
    )


    p.save()



    return f"""

<h2>
Etiket Hazir
</h2>

<a href="/indir/{pdf_adi}">
PDF indir
</a>

"""





@app.route("/indir/<dosya>")
def indir(dosya):

    return send_file(
        dosya,
        as_attachment=True
    )
    
    if __name__=="__main__":
    
    app.run(
    host="0.0.0.0",
    port=10000
    )
