import sqlite3
import random
from flask import Flask, request, redirect, session, render_template_string

app = Flask(__name__)
app.secret_key = "HERISSTOKPRO2026"

DB="stok.db"


# ---------------- DATABASE ----------------

def db():
    return sqlite3.connect(DB)


con=db()
cur=con.cursor()


cur.execute("""
CREATE TABLE IF NOT EXISTS urun(
id INTEGER PRIMARY KEY AUTOINCREMENT,
barkod TEXT,
ad TEXT,
cins TEXT,
marka TEXT,
ebat TEXT,
hgm TEXT,
sinif TEXT,
renk TEXT,
yuzey TEXT,
adet INTEGER,
alis REAL,
satis REAL
)
""")


cur.execute("""
CREATE TABLE IF NOT EXISTS satis(
id INTEGER PRIMARY KEY AUTOINCREMENT,
urun TEXT,
fiyat REAL
)
""")


con.commit()



# ---------------- BARKOD ----------------

def barkod():
    return str(random.randint(1000000000000,9999999999999))



# ---------------- TASARIM ----------------


style="""

<style>

body{
background:#07111f;
color:white;
font-family:Arial;
padding:20px;
}

input,select{
padding:10px;
margin:5px;
width:220px;
}

button{
background:#16a34a;
color:white;
padding:12px;
border:0;
border-radius:8px;
cursor:pointer;
}

.card{
background:#111827;
padding:20px;
border-radius:15px;
margin:10px;
}

h1{
color:#22c55e;
}

</style>

"""



# ---------------- LOGIN ----------------


@app.route("/admin",methods=["GET","POST"])
def admin():

    if request.method=="POST":

        if request.form["sifre"]=="1234":
            session["admin"]=True
            return redirect("/panel")


    return style+"""

<h1>HER-İŞ STOK PRO</h1>

<h3>Admin Giriş</h3>

<form method="post">

<input type="password" name="sifre" placeholder="Şifre">

<button>Giriş</button>

</form>

"""





# ---------------- PANEL ----------------


@app.route("/panel",methods=["GET","POST"])
def panel():

    if not session.get("admin"):
        return redirect("/admin")


    if request.method=="POST":

        con=db()
        cur=con.cursor()


        cur.execute("""
        INSERT INTO urun VALUES
        (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (

        barkod(),
        request.form["ad"],
        request.form["cins"],
        request.form["marka"],
        request.form["ebat"],
        request.form["hgm"],
        request.form["sinif"],
        request.form["renk"],
        request.form["yuzey"],
        request.form["adet"],
        request.form["alis"],
        request.form["satis"]

        ))


        con.commit()


    urunler=con.execute(
    "SELECT * FROM urun"
    ).fetchall()


    html=style+"""

<h1>ÜRÜN EKLE</h1>


<form method="post">


<input name="ad" placeholder="Ürün adı">

<input name="cins" placeholder="Cins">


<input name="marka" placeholder="Marka">


<input name="ebat" placeholder="Ebat mm">


<select name="hgm">

<option>HG</option>
<option>MAT</option>

</select>


<input name="sinif" placeholder="Sınıf">


<input name="renk" placeholder="Renk">


<input name="yuzey" placeholder="Yüzey">


<input name="adet" placeholder="Adet">


<input name="alis" placeholder="Alış fiyat">


<input name="satis" placeholder="Satış fiyat">


<button>ÜRÜN EKLE</button>


</form>


<h2>Stok</h2>

"""


    for u in urunler:

        html+=f"""

<div class='card'>

<b>{u[2]}</b><br>

Cins: {u[3]}<br>

Ebat: {u[5]}<br>

{u[6]} / Sınıf:{u[7]}<br>

Renk:{u[8]} Yüzey:{u[9]}<br>

Stok:{u[10]}<br>

Barkod:{u[1]}

</div>

"""


    return html





# ---------------- KASA ----------------


sepet=[]


@app.route("/",methods=["GET","POST"])
def kasa():

    global sepet


    if request.method=="POST":

        b=request.form["barkod"]


        con=db()

        urun=con.execute(
        "SELECT * FROM urun WHERE barkod=?",
        (b,)
        ).fetchone()



        if urun:

            sepet.append(
            (
            urun[2],
            urun[12]
            )
            )


            con.execute(
            "INSERT INTO satis VALUES(NULL,?,?)",
            (
            urun[2],
            urun[12]
            )
            )

            con.commit()



    html=style+"""

<h1>🌲 ORMAN KASA PRO</h1>


<button onclick="kamera()">📷 Kamera Barkod</button>


<div id="reader"></div>


<form method="post">


<input id="barkod" name="barkod"
placeholder="Barkod okut">


<button>EKLE</button>


</form>


<h2>Sepet</h2>

"""


    toplam=0

    for s in sepet:

        html+=f"""

<div class='card'>

{s[0]} - {s[1]} TL

</div>

"""

        toplam+=s[1]


    html+=f"""

<h1>TOPLAM {toplam} TL</h1>


<script src="https://unpkg.com/html5-qrcode"></script>


<script>

function kamera(){


let scanner=new Html5QrcodeScanner(
"reader",
{
fps:10,
qrbox:250
});


scanner.render(
function(text){

document.getElementById("barkod").value=text;

scanner.clear();

}

);


}


</script>


"""


    return html





# ---------------- RUN ----------------


app.run(
host="0.0.0.0",
port=5000
)
