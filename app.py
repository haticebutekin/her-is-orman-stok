from flask import Flask, render_template_string, request, redirect, session
import sqlite3, os, uuid
import barcode
import os
print("APP STARTED")
from barcode.writer import ImageWriter

app = Flask(__name__)
app.secret_key = "secret123"

STATIC = "static"
if not os.path.exists(STATIC):
    os.makedirs(STATIC)

# DEPOLAR DEPOLAR = [ "MDF SATIŞ DEPOSU", "LAMİNANT DEPOSU", "KAPI DEPOSU", "HGLOSS DEPOSU (MORAY YANI)", "SÜTÇÜ YANI", "HELVACI YANI", "RÖTBALANSÇI YANI", "KESİMHANE" ]

# DB
db = sqlite3.connect("stok.db", check_same_thread=False)
cur = db.cursor()

# TABLOLAR
cur.execute("""
CREATE TABLE IF NOT EXISTS urun (
id INTEGER PRIMARY KEY,
barkod TEXT,
isim TEXT,
cins TEXT,
ebat TEXT,
kalinlik TEXT,
sinif TEXT,
renk TEXT,
yuzey TEXT,
adet INTEGER,
kritik INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS log (
id INTEGER PRIMARY KEY,
kullanici TEXT,
barkod TEXT,
islem TEXT,
tarih TEXT
)
""")

db.commit()

# KULLANICILAR
users = {
    "admin": {"pass":"1234","role":"admin"},
    "depo": {"pass":"1234","role":"depo"}
}

# ANA SAYFA @app.route("/") def index(): return """ <h2>Depo Sistem</h2> <a href='/ekle'>Ürün Ekle</a><br><br> <a href='/kamera/giris'>Giriş (Stok Artır)</a><br><br> <a href='/kamera/cikis'>Çıkış (Stok Düş)</a> """

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        u = request.form["u"]
        p = request.form["p"]

        if u in users and users[u]["pass"] == p:
            session["user"] = u
            session["role"] = users[u]["role"]
            return redirect("/panel")

    return """
    <h2>Giriş</h2>
    <form method=post>
    Kullanıcı: <input name=u><br>
    Şifre: <input name=p type=password><br>
    <button>Giriş</button>
    </form>
    """
@app.route("/kamera/<tip>")
def kamera(tip):
    return render_template_string("""
    <style>
    body { font-family:Arial; text-align:center; }
    #isim { font-size:30px; font-weight:bold; margin:10px; }
    #stok { font-size:22px; color:green; }
    </style>

    <h2>📦 Barkod Okut</h2>

    <video id="video" width="300" autoplay></video>

    <div id="isim">Hazır...</div>
    <div id="stok"></div>

    <script src="https://unpkg.com/@zxing/library@latest"></script>

    <script>
    const codeReader = new ZXing.BrowserBarcodeReader()

    let lastScan = ""
    let lock = false

    codeReader.decodeFromVideoDevice(null, 'video', async (result, err) => {
        if (result && !lock) {

            let barkod = result.text

            if (barkod === lastScan) return;

            lock = true
            lastScan = barkod

            let res = await fetch("/hizli_islem", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    barkod: barkod,
                    tip: "{{tip}}"
                })
            })

            let data = await res.json()

            if (data.ok) {

                document.body.style.background = "white"

                document.getElementById("isim").innerText = data.isim
                document.getElementById("stok").innerText = "Kalan: " + data.adet

                navigator.vibrate(100)

            } else {

                document.body.style.background = "red"
                document.getElementById("isim").innerText = "❌ HATALI ÜRÜN"
                document.getElementById("stok").innerText = ""

            }

            setTimeout(()=>{
                lock = false
            }, 400)
        }
    })
    </script>
    """, tip=tip)


# BARKOD 
def yeni_barkod():
      con = db() 
      cur = con.cursor() 
      

@app.route("/sayac")
def sayac():
    cur.execute("SELECT COUNT(*) FROM urun")
    sayi = cur.fetchone()[0] + 1
    return str(sayi)

def barkod_olustur(kod): 
      path = f"{STATIC}/{kod}.png" 
      Code128(kod, writer=ImageWriter()).write(open(path, "wb")) 
      return path 

# LOGIN 
@app.route("/", methods=["GET","POST"]) 
def login(): 
      if request.method == "POST":
           if request.form["user"] == "admin" and request.form["pass"] == "123":           
                session["login"] = True
                return redirect("/panel") 
       return """

 <h2>HER İŞ ORMAN STOK PRO</h2> 
<form method=post> 
Kullanıcı: <input name=user><br>
 Şifre: <input name=pass type=password><br> 
<button>Giriş</button> 
</form> 
""" 

# PANEL 
@app.route("/panel", methods=["GET","POST"]) 
def panel(): 
       if not session.get("login"): 
            return redirect("/") 

      if request.method == "POST":
           barkod = yeni_barkod() 
           barkod_olustur(barkod) 

           data = ( barkod, 
                         request.form["isim"],  
                         request.form["cins"], 
                         request.form["ebat"],
                         request.form["kalinlik"], 
                         request.form["sinif"],
                         request.form["yuzey"], 
                         request.form["renk"], 
                         request.form["adet"], 
                         request.form["depo"], 
                         str(datetime.datetime.now())
 ) 

        con = db() 
        cur = con.cursor() 
        cur.execute("INSERT INTO urunler VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?)", data)    
        con.commit() 
        con.close() 

con = db() 
cur = con.cursor() 
urunler = cur.execute("SELECT * FROM urunler").fetchall() 
con.close() 

return render_template_string("""
 <h2>STOK PANEL</h2> 

<form method=post> 
İsim <input name=isim><br> 
Cins <input name=cins><br> 
Ebat <input name=ebat><br> 
Kalınlık <input name=kalinlik><br> 
Sınıf <input name=sinif><br> 

Yüzey: 
<select name=yuzey> 
       <option>HG</option> 
       <option>MAT</option> 
</select><br> 

Renk <input name=renk><br>
Adet <input name=adet type=number><br> 

Depo:
 <select name=depo> 
{% for d in depolar %}
        <option>{{d}}</option> 
{% endfor %}
 </select><br>

 <button>EKLE</button> 
</form>

 <hr> 

<a href="/kamera">📷 Kamera</a> | 
<a href="/excel">📊 Excel</a>


 <table border=1> 
<tr><th>Barkod</th><th>İsim</th><th>Adet</th><th>Depo</th></tr> 
{% for u in urunler %}
 <tr>
        <td>{{u[1]}}</td>
        <td>{{u[2]}}</td>
        <td>{{u[9]}}</td> 
        <td>{{u[10]}}</td> 
</tr> 
{% endfor %} 
</table>
 """, urunler=urunler, depolar=DEPOLAR)

@app.route("/hizli_islem", methods=["POST"])
def hizli_islem():

    if "user" not in session:
        return {"ok": False}

    barkod = request.json.get("barkod")
    tip = request.json.get("tip")

    if session.get("role") == "depo" and tip != "cikis":
        return {"ok": False, "msg": "yetki"}

    cur.execute("SELECT isim, adet FROM urun WHERE barkod=?", (barkod,))
    veri = cur.fetchone()

    if not veri:
        return {"ok": False, "msg": "yok"}

    isim, adet = veri

    if tip == "cikis":
        if adet <= 0:
            return {"ok": False, "msg": "stok"}
        adet -= 1
    else:
        adet += 1

    cur.execute("UPDATE urun SET adet=? WHERE barkod=?", (adet, barkod))

    cur.execute("""
    INSERT INTO log (kullanici,barkod,islem,tarih)
    VALUES (?,?,?,datetime('now'))
    """, (session["user"], barkod, tip))

    db.commit()

    return {
        "ok": True,
        "isim": isim,
        "adet": adet
    }

# STOK DÜŞ
 @app.route("/stok/<kod>") 
def stok(kod): 
       con = db() 
       cur = con.cursor() 

       cur.execute("SELECT adet FROM urunler WHERE barkod=?", (kod,)) 
       veri = cur.fetchone()

       if veri: 
            yeni = veri[0] - 1
            if yeni < 0: yeni = 0

            cur.execute("UPDATE urunler SET adet=? WHERE barkod=?", (yeni, kod))      
            
            cur.execute("INSERT INTO hareketler VALUES(NULL,?,?,?,?)", 
                               (kod, "ÇIKIŞ", 1, str(datetime.datetime.now())))
           
             con.commit()


 con.close() 
return redirect("/panel")

# ETİKET
@app.route("/etiket/<barkod>")
def etiket(barkod):
    return f"""
    <h3>{barkod}</h3>
    <img src="/static/{barkod}.png" width=200>
    <script>window.print()</script>
    """
# İŞLEM
@app.route("/islem/<barkod>/<tip>")
def islem(barkod, tip):

    if session.get("role") == "depo" and tip != "cikis":
        return "❌ Yetkin yok"

    cur.execute("SELECT adet FROM urun WHERE barkod=?", (barkod,))
    veri = cur.fetchone()

    if not veri:
        return "Ürün yok"

    adet = veri[0]

    if tip == "cikis":
        if adet <= 0:
            return "❌ Stok yok"
        cur.execute("UPDATE urun SET adet = adet - 1 WHERE barkod=?", (barkod,))
    else:
        cur.execute("UPDATE urun SET adet = adet + 1 WHERE barkod=?", (barkod,))

    navigator.vibrate(200);
    new Audio("https://actions.google.com/sounds/v1/cartoon/wood_plank_flicks.ogg").play();

    cur.execute("""
    INSERT INTO log (kullanici,barkod,islem,tarih)
    VALUES (?,?,?,datetime('now'))
    """, (session["user"], barkod, tip))

    db.commit()

    return redirect("/panel")

# LOG
@app.route("/log")
def log():
    cur.execute("SELECT * FROM log ORDER BY id DESC")
    data = cur.fetchall()

    return render_template_string("""
    <h2>Log</h2>
    {% for l in data %}
    <p>{{l[1]}} → {{l[3]}} → {{l[2]}} ({{l[4]}})</p>
    {% endfor %}
    """, data=data)

# ÜRÜN EKLE
 @app.route("/ekle", methods=["GET","POST"]) 
def ekle(): 
       if request.method == "POST": 
            isim = request.form["isim"] 
            barkod = request.form["barkod"] 
            adet = int(request.form["adet"])

            try: 
                 
                    cur.execute("INSERT INTO urun (isim,barkod,adet) VALUES (?,?,?)",                                                                                                                
                                       (isim,barkod,adet))
                  
                    db.commit() 
except:
                    return "Barkod zaten var!" 

return redirect("/")

 return """
 <h2>Ürün Ekle</h2> 
<form method="post">
 İsim: <input name="isim"><br>
 Barkod: <input name="barkod"><br> 
Adet: <input name="adet" type="number"><br><br> 
<button>Ekle</button> </form> 

"""


# ÇALIŞTIR
 if __name__ == "__main__":
 app.run(debug=True)
