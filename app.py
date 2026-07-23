from flask import Flask, request, jsonify, render_template_string, send_file
import sqlite3, os
from datetime import datetime
import barcode
from barcode.writer import ImageWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

app = Flask(__name__)
DB="stok.db"

# ---------------- DB ----------------
def init_db():
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT, barcode TEXT,
    cins TEXT, ebat TEXT, mm TEXT,
    hg TEXT, yuzey TEXT, sinif TEXT, renk TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS stock(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER, depo INTEGER, adet INTEGER
    )''')
    conn.commit()
    conn.close()
init_db()

# ---------------- BARKOD ----------------
def generate_barcode(code):
    if not os.path.exists("barcodes"):
        os.makedirs("barcodes")
    EAN=barcode.get_barcode_class('code128')
    EAN(code, writer=ImageWriter()).save(f"barcodes/{code}")

# ---------------- PANEL ----------------
HTML="""
<h2>ÜRÜN EKLE</h2>
<form id=form>
Adı:<input name=name><br>
Cins:<input name=cins><br>
Ebat:<input name=ebat><br>
MM:<input name=mm><br>
HG:<input name=hg><br>
Yüzey:<input name=yuzey><br>
Sınıf:<input name=sinif><br>
Renk:<input name=renk><br>
<button>EKLE</button>
</form>

<h2>STOK</h2>
<form id=stok>
ÜrünID:<input name=product_id><br>
Depo(1-8):<input name=depo><br>
Adet:<input name=adet><br>
<button>EKLE</button>
</form>

<h2>KAMERA</h2>
<div id=reader style="width:300px"></div>
Depo:<input id=d><br>
Adet:<input id=a value=1><br>
<button onclick=baslat()>OKUT</button>

<h2>ETİKET</h2>
ÜrünID:<input id=pid>
<button onclick=tek()>TEK</button>
<button onclick=cok()>TOPLU</button>

<pre id=log></pre>

<script src="https://unpkg.com/html5-qrcode"></script>
<script>

form.onsubmit=async e=>{
e.preventDefault()
let d=Object.fromEntries(new FormData(form))
let r=await fetch("/add_product",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)})
let j=await r.json()
alert("BARKOD:"+j.barcode)
}

stok.onsubmit=async e=>{
e.preventDefault()
let d=Object.fromEntries(new FormData(stok))
await fetch("/add_stock",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(d)})
alert("stok eklendi")
}

function baslat(){
let qr=new Html5Qrcode("reader")
qr.start({facingMode:"environment"},{fps:10,qrbox:250},
async txt=>{
await fetch("/scan",{method:"POST",headers:{"Content-Type":"application/json"},
body:JSON.stringify({barcode:txt,depo:Number(d.value),adet:Number(a.value)})})
alert("okundu:"+txt)
qr.stop()
})
}

function tek(){
window.open("/label/"+pid.value)
}

function cok(){
let adet=prompt("kaç adet?")
window.open("/labels_bulk/"+pid.value+"/"+adet)
}
</script>
"""

@app.route("/")
def panel():
    return render_template_string(HTML)

# ---------------- ÜRÜN ----------------
@app.route("/add_product",methods=["POST"])
def add_product():
    d=request.json
    code=str(int(datetime.now().timestamp()))
    generate_barcode(code)

    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("""INSERT INTO products
    (name,barcode,cins,ebat,mm,hg,yuzey,sinif,renk)
    VALUES(?,?,?,?,?,?,?,?,?)""",
    (d["name"],code,d["cins"],d["ebat"],d["mm"],d["hg"],d["yuzey"],d["sinif"],d["renk"]))
    conn.commit(); conn.close()
    return jsonify({"barcode":code})

# ---------------- STOK ----------------
@app.route("/add_stock",methods=["POST"])
def add_stock():
    d=request.json
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("INSERT INTO stock(product_id,depo,adet) VALUES(?,?,?)",
              (d["product_id"],d["depo"],d["adet"]))
    conn.commit(); conn.close()
    return jsonify({"ok":True})

# ---------------- SCAN ----------------
@app.route("/scan",methods=["POST"])
def scan():
    d=request.json
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT id,name FROM products WHERE barcode=?",(d["barcode"],))
    p=c.fetchone()
    if not p: return jsonify({"error":"ürün yok"})
    pid,name=p
    c.execute("UPDATE stock SET adet=adet-? WHERE product_id=? AND depo=?",
              (d["adet"],pid,d["depo"]))
    conn.commit(); conn.close()
    return jsonify({"urun":name})

# ---------------- TEK ETİKET ----------------
@app.route("/label/<int:id>")
def label(id):
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT * FROM products WHERE id=?",(id,))
    p=c.fetchone(); conn.close()
    if not p: return "yok"

    _,name,code,cins,ebat,mmv,hg,yuzey,sinif,renk=p
    pdf=f"etiket_{id}.pdf"
    c=canvas.Canvas(pdf,pagesize=(100*mm,60*mm))

    c.setFont("Helvetica-Bold",12)
    c.drawString(10,150,name)
    c.setFont("Helvetica",8)
    c.drawString(10,130,f"{cins}-{ebat}-{mmv}")
    c.drawString(10,110,f"{hg}-{yuzey}-{sinif}-{renk}")

    c.drawImage(f"barcodes/{code}.png",150,40,200,80)
    c.drawString(150,20,code)
    c.save()
    return send_file(pdf,as_attachment=True)

# ---------------- TOPLU ----------------
@app.route("/labels_bulk/<int:id>/<int:adet>")
def bulk(id,adet):
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT * FROM products WHERE id=?",(id,))
    p=c.fetchone(); conn.close()
    if not p: return "yok"

    _,name,code,cins,ebat,mmv,hg,yuzey,sinif,renk=p
    pdf=f"cok_{id}.pdf"
    c=canvas.Canvas(pdf,pagesize=A4)

    x,y=20,800
    for i in range(adet):
        c.setFont("Helvetica",8)
        c.drawString(x,y,name)
        c.drawString(x,y-15,f"{cins}-{ebat}-{mmv}")
        c.drawImage(f"barcodes/{code}.png",x,y-80,120,40)

        x+=140
        if x>450: x=20; y-=120
        if y<100: c.showPage(); x=20; y=800

    c.save()
    return send_file(pdf,as_attachment=True)

# ---------------- RUN ----------------
if __name__=="__main__":
    port=int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0",port=port)
