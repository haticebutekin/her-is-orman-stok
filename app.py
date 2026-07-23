from flask import Flask, render_template_string, request, redirect, session, jsonify
import sqlite3, random, datetime

app = Flask(__name__)
app.secret_key = "123"

# ================= DB =================
def db():
    return sqlite3.connect("db.sqlite3")

with db() as con:
    con.execute("""CREATE TABLE IF NOT EXISTS urun(
        id INTEGER PRIMARY KEY,
        barkod TEXT,
        ad TEXT,
        cins TEXT,
        ebat TEXT,
        yuzey TEXT,
        sinif TEXT,
        renk TEXT
    )""")

    con.execute("""CREATE TABLE IF NOT EXISTS stok(
        id INTEGER PRIMARY KEY,
        barkod TEXT,
        depo TEXT,
        adet INTEGER
    )""")

    con.execute("""CREATE TABLE IF NOT EXISTS log(
        id INTEGER PRIMARY KEY,
        barkod TEXT,
        islem TEXT,
        adet INTEGER,
        personel TEXT,
        tarih TEXT
    )""")

# ================= DEPOLAR =================
DEPOLAR = [
"1.MDF SATIŞ DEPOSU",
"2.LAMİNANT DEPOSU",
"3.KAPI DEPOSU",
"4.HGLOSS DEPOSU",
"5.MORAYIN YANINDAKİ DEPO",
"6.SÜTÇÜNÜN YANINDAKİ DEPO",
"7.RÖTBALANSÇININ ORDAKİ DEPO",
"8.KESİMHANEDEKİ DEPO"
]

# ================= HTML =================
HTML = """
<html>
<head>
<title>Stok Sistemi PRO</title>
<script src="https://unpkg.com/html5-qrcode"></script>
<style>
body{font-family:Arial;background:#111;color:#fff;padding:20px}
.card{background:#1e1e1e;padding:15px;margin:10px;border-radius:10px}
input,select,button{padding:8px;margin:5px;border-radius:5px;border:none}
button{background:#0a84ff;color:white}
</style>
</head>
<body>

<h2>📦 STOK SİSTEMİ PRO</h2>

<div class="card">
<form method="POST" action="/urun">
<h3>Ürün Ekle</h3>
<input name="ad" placeholder="Ürün Adı" required>
<input name="cins" placeholder="Cinsi">
<input name="ebat" placeholder="Ebat (mm)">
<select name="yuzey">
<option>HG</option>
<option>MAT</option>
</select>
<input name="sinif" placeholder="Sınıf">
<input name="renk" placeholder="Renk">
<button>Ekle</button>
</form>
</div>

<div class="card">
<form method="POST" action="/stok">
<h3>Stok İşlem</h3>
<input name="barkod" id="barkod" placeholder="Barkod" required>
<input name="adet" placeholder="Adet" required>
<select name="depo">
{% for d in depolar %}
<option>{{d}}</option>
{% endfor %}
</select>
<select name="islem">
<option>giris</option>
<option>cikis</option>
</select>
<input name="personel" placeholder="Personel" required>
<button>Kaydet</button>
</form>
</div>

<div class="card">
<h3>📷 Barkod Oku</h3>
<div id="reader" style="width:300px"></div>
</div>

<div class="card">
<h3>📊 Stoklar</h3>
{% for s in stok %}
<div>{{s[0]}} | {{s[1]}} | {{s[2]}}</div>
{% endfor %}
</div>

<div class="card">
<h3>📜 Hareketler</h3>
{% for l in log %}
<div>{{l[0]}} | {{l[1]}} | {{l[2]}} | {{l[3]}}</div>
{% endfor %}
</div>

<script>
function onScanSuccess(decodedText){
document.getElementById("barkod").value = decodedText;
}
new Html5QrcodeScanner("reader",{fps:10}).render(onScanSuccess);
</script>

</body>
</html>
"""

# ================= ROUTES =================
@app.route("/")
def index():
    with db() as con:
        stok = con.execute("SELECT barkod,depo,adet FROM stok").fetchall()
        log = con.execute("SELECT barkod,islem,adet,personel FROM log ORDER BY id DESC LIMIT 20").fetchall()
    return render_template_string(HTML, stok=stok, log=log, depolar=DEPOLAR)

@app.route("/urun", methods=["POST"])
def urun():
    barkod = str(random.randint(1000000000,9999999999))
    with db() as con:
        con.execute("INSERT INTO urun(barkod,ad,cins,ebat,yuzey,sinif,renk) VALUES(?,?,?,?,?,?,?)",
        (barkod,
         request.form["ad"],
         request.form["cins"],
         request.form["ebat"],
         request.form["yuzey"],
         request.form["sinif"],
         request.form["renk"]))
    return redirect("/")

@app.route("/stok", methods=["POST"])
def stok():
    barkod = request.form["barkod"]
    adet = int(request.form["adet"])
    depo = request.form["depo"]
    islem = request.form["islem"]
    personel = request.form["personel"]

    with db() as con:
        mevcut = con.execute("SELECT adet FROM stok WHERE barkod=? AND depo=?",(barkod,depo)).fetchone()

        if islem=="giris":
            if mevcut:
                con.execute("UPDATE stok SET adet=adet+? WHERE barkod=? AND depo=?",(adet,barkod,depo))
            else:
                con.execute("INSERT INTO stok(barkod,depo,adet) VALUES(?,?,?)",(barkod,depo,adet))

        if islem=="cikis":
            if not mevcut or mevcut[0] < adet:
                return "YETERSİZ STOK!"
            con.execute("UPDATE stok SET adet=adet-? WHERE barkod=? AND depo=?",(adet,barkod,depo))

        con.execute("INSERT INTO log(barkod,islem,adet,personel,tarih) VALUES(?,?,?,?,?)",
        (barkod,islem,adet,personel,str(datetime.datetime.now())))

    return redirect("/")

# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
