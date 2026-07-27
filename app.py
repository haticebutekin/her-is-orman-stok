from flask import Flask, request, redirect, session
import sqlite3
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "12345"

# ---------------- DB ----------------
def db():
    return sqlite3.connect("db.sqlite3")

def kur():
    con = db()
    c = con.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS urun(
        id INTEGER PRIMARY KEY,
        ad TEXT,
        cins TEXT,
        ebat TEXT,
        kalinlik TEXT,
        yuzey TEXT,
        renk TEXT,
        adet INTEGER,
        depo TEXT,
        barkod TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS hareket(
        id INTEGER PRIMARY KEY,
        urun TEXT,
        adet INTEGER,
        depo TEXT,
        kim TEXT,
        saat TEXT
    )""")

    con.commit()
    con.close()

kur()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["kullanici"]
        p = request.form["sifre"]

        if u == "admin" and p == "123":
            session["user"]="admin"
            return redirect("/panel")

        if u == "depo" and p == "123":
            session["user"]="depo"
            return redirect("/cikis")

        return "Hatalı giriş"

    return """
    <h2>Giriş</h2>
    <form method="post">
    Kullanıcı: <input name="kullanici"><br><br>
    Şifre: <input type="password" name="sifre"><br><br>
    <button>Giriş</button>
    </form>
    """

# ---------------- PANEL ----------------
@app.route("/panel")
def panel():
    if session.get("user")!="admin":
        return redirect("/")

    con=db()
    c=con.cursor()
    urunler=c.execute("SELECT * FROM urun").fetchall()
    con.close()

    html="<h2>Panel</h2><a href='/ekle'>+ Ürün Ekle</a><br><br>"

    for u in urunler:
        html+=f"{u[1]} | {u[3]} | {u[4]}mm | {u[6]} | Stok:{u[7]} | Barkod:{u[9]}<br>"

    return html

# ---------------- ÜRÜN EKLE ----------------
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method=="POST":
        data = (
            request.form["ad"],
            request.form["cins"],
            request.form["ebat"],
            request.form["kalinlik"],
            request.form["yuzey"],
            request.form["renk"],
            int(request.form["adet"]),
            request.form["depo"],
            str(uuid.uuid4())[:8]
        )

        con=db()
        c=con.cursor()
        c.execute("INSERT INTO urun(ad,cins,ebat,kalinlik,yuzey,renk,adet,depo,barkod) VALUES (?,?,?,?,?,?,?,?,?)",data)
        con.commit()
        con.close()

        return redirect("/panel")

    return """
    <h2>Ürün Ekle</h2>

    <form method="post">

    Mal adı:<br><input name="ad"><br><br>
    Cinsi:<br><input name="cins"><br><br>

    Ebat (2100x2800):<br>
    <input name="ebat"><br><br>

    <h3>Kalınlık</h3>
    <div id="kalinlikGrup">
    <button type="button" onclick="secK(this,'4')">4</button>
    <button type="button" onclick="secK(this,'6')">6</button>
    <button type="button" onclick="secK(this,'8')">8</button>
    <button type="button" onclick="secK(this,'10')">10</button>
    <button type="button" onclick="secK(this,'12')">12</button>
    <button type="button" onclick="secK(this,'18')">18</button>
    <button type="button" onclick="secK(this,'30')">30</button>
    <button type="button" onclick="secK(this,'35')">35</button>
    </div>

    <input type="hidden" name="kalinlik" id="kalinlik"><br>

    <h3>HG / MAT</h3>
    <button type="button" onclick="secY(this,'HG')">HG</button>
    <button type="button" onclick="secY(this,'MAT')">MAT</button>
    <input type="hidden" name="yuzey" id="yuzey"><br><br>

    Renk:<br><input name="renk"><br><br>

    Adet:<br><input name="adet" type="number"><br><br>

    Depo:<br>
    <select name="depo">
    <option>MDF SATIŞ DEPOSU</option>
    <option>LAMİNANT DEPOSU</option>
    <option>KAPI DEPOSU</option>
    <option>HGLOSS DEPOSU</option>
    <option>SÜTÇÜ YANI</option>
    <option>HELVACI YANI</option>
    <option>RÖTBALANSÇI YANI</option>
    </select><br><br>

    <button>Kaydet</button>

    </form>

    <script>
    function secK(btn,val){
        document.getElementById("kalinlik").value=val;
        document.querySelectorAll("#kalinlikGrup button").forEach(b=>b.style.background="");
        btn.style.background="blue";
    }

    function secY(btn,val){
        document.getElementById("yuzey").value=val;
        document.querySelectorAll("button").forEach(b=>b.style.border="");
        btn.style.border="3px solid red";
    }
    </script>
    """

# ---------------- DEPO ÇIKIŞ ----------------
@app.route("/cikis", methods=["GET","POST"])
def cikis():
    if request.method=="POST":
        barkod=request.form["barkod"]
        adet=int(request.form["adet"])

        con=db()
        c=con.cursor()

        urun=c.execute("SELECT * FROM urun WHERE barkod=?",(barkod,)).fetchone()

        if not urun:
            return "Ürün yok"

        yeni=urun[7]-adet

        if yeni<0:
            return "Yetersiz stok"

        c.execute("UPDATE urun SET adet=? WHERE barkod=?",(yeni,barkod))

        c.execute("INSERT INTO hareket(urun,adet,depo,kim,saat) VALUES (?,?,?,?,?)",
        (urun[1],adet,urun[8],"depo",datetime.now().strftime("%H:%M")))

        con.commit()
        con.close()

        return "Çıkış yapıldı"

    return """
    <h2>Depodan Çıkış</h2>
    <form method="post">
    Barkod:<br><input name="barkod"><br><br>
    Adet:<br><input name="adet"><br><br>
    <button>Çıkış</button>
    </form>
    """

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()
