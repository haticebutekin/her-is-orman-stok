from flask import Flask, request, redirect, session, send_file
import sqlite3, uuid, os
import qrcode
from reportlab.pdfgen import canvas
from datetime import datetime

app = Flask(__name__)
app.secret_key = "12345"

UPLOAD_FOLDER = "static"   # ✅ sadece bu var, sorun yok

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

    x,y = 50,750
    for i in range(20):
        pdf.drawString(x,y,ad)
        pdf.drawImage(qr_path,x,y-80,80,80)
        x+=120
        if x>400:
            x=50
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
    <input name="kullanici" placeholder="admin / depo"><br><br>
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
        Stok: {u[7]} | Depo: {u[8]}<br>
        <img src='/static/{u[10]}' width='100'><br>
        <a href='/pdf/{u[9]}'>🧾 PDF</a>
        </div>
        """

    return html

# ---------------- ÜRÜN EKLE ----------------
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if request.method=="POST":

        barkod=str(uuid.uuid4())[:8]

        foto=request.files["foto"]
        foto_ad=barkod+".jpg"
        foto.save(f"{UPLOAD_FOLDER}/{foto_ad}")

        data=(
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

        con=db()
        c=con.cursor()
        c.execute("INSERT INTO urun(ad,cins,ebat,kalinlik,yuzey,renk,adet,depo,barkod,foto) VALUES (?,?,?,?,?,?,?,?,?,?)",data)
        con.commit()
        con.close()

        return redirect("/panel")

    return """
    <h2>Ürün Ekle</h2>
    <form method="post" enctype="multipart/form-data">
    Ad:<br><input name="ad"><br>
    Cins:<br><input name="cins"><br>
    Ebat:<br><input name="ebat"><br>
    Kalınlık:<br><input name="kalinlik"><br>
    Yüzey:<br><input name="yuzey"><br>
    Renk:<br><input name="renk"><br>
    Adet:<br><input name="adet"><br>
    Depo:<br><input name="depo"><br><br>
    Foto:<br><input type="file" name="foto"><br><br>
    <button>Kaydet</button>
    </form>
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

    labels=[x[0] for x in data]
    values=[x[1] for x in data]

    return f"""
    <h2>Depo Rapor</h2>
    <canvas id="g"></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    new Chart(document.getElementById("g"), {{
        type: "pie",
        data: {{
            labels: {labels},
            datasets: [{{ data: {values} }}]
        }}
    }});
    </script>
    """

# ---------------- QR ÇIKIŞ ----------------
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
    body{background:black;color:white;text-align:center;}
    video{width:100%;height:60vh;}
    input{font-size:25px;width:100%;}
    </style>

    <h2>📦 Depo</h2>
    <video id="kamera" autoplay></video>

    <input id="adet" value="1">

    <script src="https://unpkg.com/html5-qrcode"></script>

    <script>
    const qr=new Html5Qrcode("kamera");
    let kilit=false;

    Html5Qrcode.getCameras().then(d=>{
    qr.start(d[0].id,{fps:10},code=>{
    if(kilit) return;
    kilit=true;

    fetch("/cikis",{
    method:"POST",
    headers:{"Content-Type":"application/x-www-form-urlencoded"},
    body:"barkod="+code+"&adet="+adet.value
    })
    .then(r=>r.text())
    .then(alert);

    setTimeout(()=>kilit=false,1500);
    });
    });
    </script>
    """

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()
