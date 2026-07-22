from flask import Flask, render_template_string, request, redirect, session
import sqlite3, random, datetime

app = Flask(__name__)
app.secret_key="123"

db=sqlite3.connect("db.db",check_same_thread=False)
c=db.cursor()

# TABLOLAR
c.execute("""CREATE TABLE IF NOT EXISTS urun(
id INTEGER PRIMARY KEY,
barkod TEXT,
ad TEXT,
marka TEXT,
cins TEXT,
ebat TEXT,
renk TEXT,
yuzey TEXT,
adet INTEGER,
fiyat REAL)""")

c.execute("""CREATE TABLE IF NOT EXISTS satis(
id INTEGER PRIMARY KEY,
urun TEXT,
fiyat REAL,
tarih TEXT)""")

db.commit()

def barkod():
    return str(random.randint(100000000000,999999999999))

# LOGIN
@app.route("/",methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form["k"]=="admin" and request.form["s"]=="1234":
            session["ok"]=1
            session["sepet"]=[]
            return redirect("/pos")
    return """<h2>Giriş</h2>
    <form method=post>
    <input name=k><input name=s type=password>
    <button>GİR</button></form>"""

# KASA
@app.route("/pos",methods=["GET","POST"])
def pos():
    if "ok" not in session:
        return redirect("/")

    if request.method=="POST":
        barkod=request.form["barkod"]
        c.execute("SELECT * FROM urun WHERE barkod=?",(barkod,))
        u=c.fetchone()

        if u:
            if u[8]>0:
                session["sepet"].append(u)
                c.execute("UPDATE urun SET adet=adet-1 WHERE barkod=?",(barkod,))
                c.execute("INSERT INTO satis (urun,fiyat,tarih) VALUES (?,?,?)",
                          (u[2],u[9],str(datetime.date.today())))
                db.commit()

    toplam=sum([x[9] for x in session["sepet"]])

    return render_template_string("""
<html>
<head>
<meta name=viewport content="width=device-width, initial-scale=1">
<script src="https#unpkg.com/html5-qrcode"></script>
<style>
body{background:#020617;color:white;font-family:Arial;text-align:center}
.box{background:#111;padding:15px;margin:10px;border-radius:15px}
input,button{padding:12px;font-size:18px;margin:5px;border-radius:10px;border:none}
button{background:#22c55e;color:white}
</style>
</head>
<body>

<h2>🔥 PRO KASA</h2>

<form method=post>
<input id=barkod name=barkod autofocus placeholder="BARKOD">
<button>EKLE</button>
</form>

<button onclick="cam()">📷 KAMERA</button>
<div id=reader></div>

<script>
function cam(){
 let r=new Html5Qrcode("reader");
 r.start({facingMode:"environment"},{fps:10,qrbox:250},
 (t)=>{document.getElementById("barkod").value=t; r.stop(); document.forms[0].submit();}
 );
}
</script>

<div class=box>
<h3>🛒 SEPET</h3>
{% for i in sepet %}
<p>{{i[2]}} - {{i[9]}} ₺</p>
{% endfor %}
<h2>TOPLAM: {{toplam}} ₺</h2>

<button onclick="window.print()">🧾 FİŞ</button>
</div>

<a href="/ekle"><button>ÜRÜN EKLE</button></a>
<a href="/rapor"><button>RAPOR</button></a>

</body>
</html>
""",sepet=session["sepet"],toplam=toplam)

# ÜRÜN EKLE
@app.route("/ekle",methods=["GET","POST"])
def ekle():
    if request.method=="POST":
        c.execute("""INSERT INTO urun VALUES (NULL,?,?,?,?,?,?,?,?,?)""",
        (barkod(),
         request.form["ad"],
         request.form["marka"],
         request.form["cins"],
         request.form["ebat"],
         request.form["renk"],
         request.form["yuzey"],
         int(request.form["adet"]),
         float(request.form["fiyat"])
        ))
        db.commit()
        return "OK"
    return """
    <h2>Ürün</h2>
    <form method=post>
    Ad<input name=ad>
    Marka<input name=marka>
    Cins<input name=cins>
    Ebat<input name=ebat>
    Renk<input name=renk>
    Yüzey<select name=yuzey><option>HG</option><option>MAT</option></select>
    Adet<input name=adet>
    Fiyat<input name=fiyat>
    <button>KAYDET</button>
    </form>
    """

# RAPOR
@app.route("/rapor")
def rapor():
    c.execute("SELECT urun, SUM(fiyat) FROM satis GROUP BY urun")
    data=c.fetchall()

    html="<h2>Satış Raporu</h2>"
    for d in data:
        html+=f"<p>{d[0]} : {d[1]} ₺</p>"
    return html

app.run()

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
