from flask import Flask, request, redirect
import sqlite3, os

app = Flask(__name__)

conn = sqlite3.connect("db.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS urun(
id INTEGER PRIMARY KEY,
barkod TEXT,
ad TEXT,
cins TEXT,
ebat TEXT,
sinif TEXT,
renk TEXT,
adet INTEGER,
fiyat REAL)""")
conn.commit()

sepet=[]


@app.route("/", methods=["GET","POST"])
def login():

    if request.method=="POST":
        if request.form["k"]=="admin" and request.form["s"]=="1234":
            return redirect("/pos")

    return """
    <style>
    body{background:#0f172a;color:white;font-family:Arial;text-align:center}
    input,button{padding:15px;font-size:20px;margin:10px;width:90%}
    </style>

    <h2>🌲 ORMAN STOK PRO</h2>

    <form method="post">
    <input name="k" placeholder="Kullanıcı">
    <input name="s" type="password" placeholder="Şifre">
    <button>Giriş</button>
    </form>
    """


@app.route("/pos", methods=["GET","POST"])
def pos():

    global sepet

    if request.method=="POST":

        barkod=request.form["barkod"]

        u=c.execute(
        "SELECT * FROM urun WHERE barkod=?",
        (barkod,)
        ).fetchone()


        if u:

            sepet.append({
            "ad":u[2],
            "fiyat":u[8]
            })

            c.execute(
            "UPDATE urun SET adet=adet-1 WHERE id=?",
            (u[0],)
            )

            conn.commit()


    toplam=0
    rows=""

    for u in sepet:

        toplam+=u["fiyat"]

        rows+=f"""
        <tr>
        <td>{u['ad']}</td>
        <td>{u['fiyat']} ₺</td>
        </tr>
        """


    return f"""

<style>

body{{
background:#0f172a;
color:white;
font-family:Arial;
padding:15px
}}

input,button{{
width:100%;
padding:18px;
font-size:20px;
margin:5px;
border-radius:10px
}}

button{{
background:#22c55e;
border:none
}}

.toplam{{
font-size:35px;
color:#22c55e
}}

</style>


<h2>🌲 ORMAN KASA PRO</h2>


<form method="post">

<input id="barkod"
<button type="button" onclick="kameraAc()" style="
width:100%;
padding:20px;
font-size:22px;
background:#f59e0b;
color:white;
border-radius:10px;
border:0;
margin-top:10px;">
📷 KAMERA İLE BARKOD OKU
</button>

<div id="kamera" style="margin-top:20px;"></div>

<script src="https://unpkg.com/html5-qrcode"></script>

<script>
function kameraAc(){

    let kamera = document.getElementById("kamera");

    kamera.innerHTML="Kamera açılıyor...";

    let scanner = new Html5QrcodeScanner(
        "kamera",
        {
            fps:10,
            qrbox:250
        }
    );

    scanner.render(
        function(barkod){

            document.getElementById("barkod").value=barkod;

            scanner.clear();

            document.forms[0].submit();

        },
        function(hata){
        }
    );
}
</script>
name="barkod"
placeholder="Barkod okut">

</form>


<button onclick="kameraAc()">
📷 KAMERA İLE BARKOD OKU
</button>


<div id="kamera"></div>



<div>

<a href="/odeme">
<button>💰 ÖDE</button>
</a>

<a href="/ekle">
<button>➕ ÜRÜN EKLE</button>
</a>

<a href="/rapor">
<button>📊 STOK</button>
</a>

</div>



<table border="1" width="100%">
{rows}
</table>


<p class="toplam">
TOPLAM: {toplam} ₺
</p>




<script src="https://unpkg.com/html5-qrcode"></script>


<script>

function kameraAc(){


let scanner =
new Html5QrcodeScanner(
"kamera",
{
fps:10,
qrbox:250
}
);


scanner.render(
function(text){


document.getElementById(
"barkod"
).value=text;


scanner.clear();


document.forms[0].submit();


});

}


</script>


"""


@app.route("/ekle",methods=["GET","POST"])
def ekle():

    if request.method=="POST":

        c.execute(
        "INSERT INTO urun VALUES(NULL,?,?,?,?,?,?,?,?)",
        (
        request.form["b"],
        request.form["a"],
        request.form["c"],
        request.form["e"],
        request.form["s"],
        request.form["r"],
        request.form["adet"],
        request.form["f"]
        ))

        conn.commit()

        return redirect("/pos")


    return """

<h2>Ürün Ekle</h2>

<form method="post">

<input name="b" placeholder="Barkod"><br>
<input name="a" placeholder="Ad"><br>
<input name="c" placeholder="Cins"><br>
<input name="e" placeholder="Ebat mm"><br>
<input name="s" placeholder="Sınıf"><br>
<input name="r" placeholder="Renk"><br>
<input name="adet" placeholder="Adet"><br>
<input name="f" placeholder="Fiyat"><br>

<button>Kaydet</button>

</form>

"""


@app.route("/rapor")
def rapor():

    data=c.execute(
    "SELECT * FROM urun"
    ).fetchall()


    html=""

    for u in data:

        html+=f"""

<tr>
<td>{u[2]}</td>
<td>{u[7]}</td>
<td>{u[8]} ₺</td>
</tr>

"""


    return f"""

<h2>Stok</h2>

<table border=1 width=100%>

{html}

</table>

<a href="/pos">
Geri
</a>

"""


@app.route("/odeme")
def odeme():

    global sepet

    txt="ORMAN STOK PRO\n\n"

    toplam=0

    for u in sepet:

        txt+=f"{u['ad']} {u['fiyat']} TL\n"

        toplam+=u["fiyat"]


    txt+=f"\nTOPLAM:{toplam}"

    open(
    "fis.txt",
    "w",
    encoding="utf8"
    ).write(txt)


    sepet.clear()


    return """
<h3>Satış tamamlandı</h3>
<a href="/pos">Geri</a>
"""


app.run(
host="0.0.0.0",
port=5000
)
