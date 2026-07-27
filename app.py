from flask import Flask, request, redirect, session, send_file
import sqlite3, uuid, os
import qrcode
from reportlab.pdfgen import canvas
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")
    <!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Stok Panel</title>

<style>
body {
    margin: 0;
    font-family: Arial, sans-serif;

    /* 👇 SENİN GÖRSEL */
    background: url("/static/bg.jpg") no-repeat center center fixed;
    background-size: cover;
}

/* üst karartma (okunabilirlik için) */
.overlay {
    background: rgba(0,0,0,0.6);
    min-height: 100vh;
    padding: 30px;
}

h1 {
    text-align: center;
    color: #fff;
}

/* butonlar */
.btn {
    display: block;
    width: 80%;
    margin: 15px auto;
    padding: 20px;
    font-size: 18px;
    border-radius: 10px;
    text-align: center;
    color: white;
    text-decoration: none;
}

/* renkler (senin eski sistem) */
.ekle { background: #007bff; }
.cikis { background: #28a745; }
.okut { background: #ff9800; }
.stok { background: #3f51b5; }
.hareket { background: #f44336; }

</style>
</head>

<body>

<div class="overlay">

<h1>📦 STOK PANEL</h1>

<a href="/urun-ekle" class="btn ekle">➕ ÜRÜN EKLE</a>
<a href="/cikis" class="btn cikis">📤 ÇIKIŞ</a>
<a href="/okut" class="btn okut">📷 OKUT</a>
<a href="/stok" class="btn stok">📋 STOK</a>
<a href="/hareket" class="btn hareket">📊 HAREKET</a>

</div>

</body>
</html>

app = Flask(__name__)
app.secret_key = "12345"

UPLOAD_FOLDER = "static"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
        barkod TEXT,
        foto TEXT
    )""")

    con.commit()
    con.close()

kur()

# ---------------- PDF ----------------
def etiket_pdf(barkod, ad):
    qr = qrcode.make(barkod)
    qr_path = f"{UPLOAD_FOLDER}/{barkod}.png"
    qr.save(qr_path)

    pdf_path = f"{UPLOAD_FOLDER}/{barkod}.pdf"
    pdf = canvas.Canvas(pdf_path)

    x,y = 40,750
    for i in range(20):
        pdf.drawString(x,y,ad)
        pdf.drawImage(qr_path,x,y-80,80,80)
        x+=120
        if x>400:
            x=40
            y-=120

    pdf.save()
    return pdf_path

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        if request.form["kullanici"]=="admin":
            session["user"]="admin"
            return redirect("/panel")
        if request.form["kullanici"]=="depo":
            session["user"]="depo"
            return redirect("/cikis")

    return """
    <h2>Giriş</h2>
    <form method="post">
    <input name="kullanici" placeholder="admin / depo">
    <button>Giriş</button>
    </form>
    """

# ---------------- PANEL ----------------
@app.route("/panel")
def panel():
    con=db()
    c=con.cursor()
    urunler=c.execute("SELECT * FROM urun").fetchall()
    con.close()

    html="<h2>Panel</h2>"
    html+="<a href='/ekle'>+ Ürün</a> | "
    html+="<a href='/rapor'>📊 Rapor</a><br><br>"

    for u in urunler:
        html+=f"""
        <div style='border:1px solid #ccc;padding:10px;margin:10px'>
        <b>{u[1]}</b><br>
        {u[4]} | {u[5]} | {u[6]}<br>
        Stok: {u[7]} | Depo: {u[8]}<br>
        <img src='/static/{u[10]}' width='100'><br>
        <a href='/pdf/{u[9]}'>🧾 PDF indir</a>
        </div>
        """

    return html

# ---------------- ÜRÜN EKLE ----------------
@app.route("/ekle", methods=["GET","POST"])
def ekle():

    if request.method == "POST":

        barkod = str(uuid.uuid4())[:8]

        foto = request.files["foto"]
        foto_ad = barkod + ".jpg"
        foto.save(f"{UPLOAD_FOLDER}/{foto_ad}")

        data = (
            request.form["ad"],
            request.form["cins"],
            request.form["ebat"],
            request.form["kalinlik"],
            request.form["yuzey"],
            request.form["renk"],
            int(request.form["adet"]),
            request.form["depo"],
            barkod,
            foto_ad
        )

        con = db()
        c = con.cursor()
        c.execute("INSERT INTO urun(ad,cins,ebat,kalinlik,yuzey,renk,adet,depo,barkod,foto) VALUES (?,?,?,?,?,?,?,?,?,?)", data)
        con.commit()
        con.close()

        return redirect("/panel")

    return """
    <style>
    body{font-family:sans-serif;padding:20px}
    button{padding:10px;margin:5px;color:white;border:none}
    .k{background:#007aff}
    .y{background:#34c759}
    .r{background:#5856d6}
    input{width:100%;padding:10px;margin:5px}
    </style>

    <h2>Ürün Ekle</h2>

    <form method="post" enctype="multipart/form-data">

    Ad:<input name="ad">
    Cins:<input name="cins">
    Ebat:<input name="ebat">

    <h3>Kalınlık</h3>
    <button type="button" class="k" onclick="secK('4mm')">4</button>
    <button type="button" class="k" onclick="secK('6mm')">6</button>
    <button type="button" class="k" onclick="secK('8mm')">8</button>
    <button type="button" class="k" onclick="secK('10mm')">10</button>
    <button type="button" class="k" onclick="secK('12mm')">12</button>
    <button type="button" class="k" onclick="secK('30mm')">30</button>
    <button type="button" class="k" onclick="secK('35mm')">35</button>
    <input id="kalinlik" name="kalinlik">

    <h3>Yüzey</h3>
    <button type="button" class="y" onclick="secY('HG')">HG</button>
    <button type="button" class="y" onclick="secY('Mat')">Mat</button>
    <input id="yuzey" name="yuzey">

    <h3>Renk</h3>
    <div id="renkler"></div>
    <input id="renk" name="renk">

    Adet:<input name="adet">

    <h3>Depo</h3>
    <button type="button" onclick="secD('Ana')">Ana</button>
    <button type="button" onclick="secD('Şube')">Şube</button>
    <input id="depo" name="depo">

    Foto:<input type="file" name="foto">

    <button style="background:red;width:100%">Kaydet</button>
    </form>

    <script>
    const renkList = {
        HG:["Beyaz","Krem","Antrasit"],
        Mat:["Gri","Siyah"]
    };

    function secK(v){
        document.getElementById("kalinlik").value=v;
    }

    function secY(v){
        document.getElementById("yuzey").value=v;

        let alan=document.getElementById("renkler");
        alan.innerHTML="";

        renkList[v].forEach(r=>{
            alan.innerHTML += `<button type='button' class='r' onclick="secR('${r}')">${r}</button>`;
        });
    }

    function secR(v){
        document.getElementById("renk").value=v;
    }

    function secD(v){
        document.getElementById("depo").value=v;
    }
    </script>
    """

# ---------------- PDF ----------------
@app.route("/pdf/<barkod>")
def pdf(barkod):
    con=db()
    c=con.cursor()
    urun=c.execute("SELECT ad FROM urun WHERE barkod=?",(barkod,)).fetchone()
    con.close()

    path=etiket_pdf(barkod, urun[0])
    return send_file(path, as_attachment=True)

# ---------------- RAPOR ----------------
@app.route("/rapor")
def rapor():
    con=db()
    c=con.cursor()
    data=c.execute("SELECT depo, SUM(adet) FROM urun GROUP BY depo").fetchall()
    con.close()

    return f"""
    <h2>Depo Rapor</h2>
    <canvas id="g"></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    new Chart(document.getElementById("g"), {{
        type: "pie",
        data: {{
            labels: {[x[0] for x in data]},
            datasets: [{{ data: {[x[1] for x in data]} }}]
        }}
    }});
    </script>
    """

# ---------------- DEPO (QR OKUTMA) ----------------
@app.route("/cikis", methods=["GET","POST"])
def cikis():
    if request.method=="POST":
        barkod=request.form["barkod"]
        adet=int(request.form["adet"])

        con=db()
        c=con.cursor()
        urun=c.execute("SELECT * FROM urun WHERE barkod=?",(barkod,)).fetchone()

        if not urun:
            return "❌ Ürün yok"

        yeni=urun[7]-adet
        if yeni<0:
            return "⚠️ Yetersiz stok"

        c.execute("UPDATE urun SET adet=? WHERE barkod=?",(yeni,barkod))
        con.commit()
        con.close()

        return f"✅ {urun[1]} | Kalan: {yeni}"

    return """
    <style>
    body{background:black;color:white;text-align:center}
    video{width:100%;height:60vh}
    input{font-size:25px;width:100%}
    </style>

    <h2>📦 Depo Modu</h2>
    <div id="kamera"></div>
    <input id="adet" value="1">

    <script src="https://unpkg.com/html5-qrcode"></script>
    <script>
    const qr=new Html5Qrcode("kamera");

    Html5Qrcode.getCameras().then(d=>{
    qr.start(d[0].id,{fps:10},code=>{
        fetch("/cikis",{
        method:"POST",
        headers:{"Content-Type":"application/x-www-form-urlencoded"},
        body:"barkod="+code+"&adet="+adet.value
        })
        .then(r=>r.text())
        .then(alert);
    });
    });
    </script>
    """

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
