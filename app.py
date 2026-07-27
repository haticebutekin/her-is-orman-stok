from flask import Flask, request, redirect, session, render_template_string, send_file
import sqlite3, datetime, os, io, base64

app = Flask(__name__)
app.secret_key = "123"

DEPOLAR = [
"MDF SATIŞ DEPOSU",
"LAMİNANT DEPOSU",
"KAPI DEPOSU",
"HGLOSS DEPOSU (MORAY YANI)",
"SÜTÇÜ YANI",
"HELVACI YANI",
"RÖTBALANSÇI YANI",
"KESİMHANE"
]

def db():
    return sqlite3.connect("stok.db")

# ---------------- DB ----------------
with db() as con:
    con.execute("""CREATE TABLE IF NOT EXISTS urunler(
    id INTEGER PRIMARY KEY,
    barkod TEXT,
    isim TEXT,
    cins TEXT,
    ebat TEXT,
    kalinlik TEXT,
    sinif TEXT,
    yuzey TEXT,
    renk TEXT,
    adet INT,
    depo TEXT
    )""")

    con.execute("""CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    username TEXT,
    password TEXT,
    role TEXT
    )""")

    con.execute("""CREATE TABLE IF NOT EXISTS log(
    id INTEGER PRIMARY KEY,
    user TEXT,
    islem TEXT,
    barkod TEXT,
    depo TEXT,
    adet INT,
    tarih TEXT
    )""")

    if not con.execute("SELECT * FROM users").fetchall():
        con.execute("INSERT INTO users VALUES(NULL,'admin','123','admin')")
        con.execute("INSERT INTO users VALUES(NULL,'depo','123','depo')")

# ---------------- LOG ----------------
def log(user,islem,kod,depo,adet):
    with db() as con:
        con.execute("INSERT INTO log VALUES(NULL,?,?,?,?,?,?)",
        (user,islem,kod,depo,adet,str(datetime.datetime.now())))

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        k=request.form["k"]
        s=request.form["s"]
        with db() as con:
            u=con.execute("SELECT * FROM users WHERE username=? AND password=?",(k,s)).fetchone()
        if u:
            session["g"]=1
            session["user"]=u[1]
            session["role"]=u[3]
            return redirect("/panel")

    return """
    <h2>Giriş</h2>
    <form method="post">
    <input name="k"><br>
    <input name="s" type="password"><br>
    <button>Giriş</button>
    </form>
    """

# ---------------- PANEL ----------------
@app.route("/panel", methods=["GET","POST"])
def panel():
    if not session.get("g"): return redirect("/")

    if request.method=="POST" and session["role"]=="admin":
        kod="HER-"+str(int(datetime.datetime.now().timestamp()))
        with db() as con:
            con.execute("""INSERT INTO urunler VALUES(NULL,?,?,?,?,?,?,?,?,?,?)""",
            (kod,
             request.form["isim"],
             request.form["cins"],
             request.form["ebat"],
             request.form["kalinlik"],
             request.form["sinif"],
             request.form["yuzey"],
             request.form["renk"],
             int(request.form["adet"]),
             request.form["depo"]
             ))
        log(session["user"],"EKLE",kod,request.form["depo"],request.form["adet"])

    with db() as con:
        urunler=con.execute("SELECT * FROM urunler ORDER BY id DESC").fetchall()

  return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Stok Paneli</title>

<style>
body{
    font-family: Arial;
    background:#0f172a;
    color:white;
    margin:0;
}

.header{
    background:#111827;
    padding:15px;
    display:flex;
    justify-content:space-between;
}

.container{
    padding:20px;
}

.card{
    background:#1e293b;
    padding:15px;
    border-radius:10px;
    margin-bottom:15px;
    box-shadow:0 0 10px rgba(0,0,0,0.4);
}

input,select{
    width:100%;
    padding:10px;
    margin:5px 0;
    border-radius:6px;
    border:none;
}

button{
    background:#22c55e;
    border:none;
    padding:10px;
    width:100%;
    border-radius:6px;
    color:white;
    font-weight:bold;
    cursor:pointer;
}

button:hover{
    background:#16a34a;
}

.badge{
    padding:5px 10px;
    border-radius:6px;
    font-size:12px;
}

.hg{background:#22c55e;}
.mat{background:#3b82f6;}

.top-btn{
    background:#3b82f6;
    padding:8px 12px;
    border-radius:6px;
    text-decoration:none;
    color:white;
    margin-right:5px;
}

.top-btn:hover{
    background:#2563eb;
}
</style>

</head>

<body>

<div class="header">
<div>
<b>{{session['user']}}</b> ({{session['role']}})
</div>

<div>
<a class="top-btn" href="/kamera">📷 Okut</a>
<a class="top-btn" href="/log">📋 Log</a>
</div>
</div>

<div class="container">

{% if session["role"]=="admin" %}
<div class="card">
<h3>➕ Yeni Ürün</h3>

<form method="post">
<input name="isim" placeholder="Mal adı">
<input name="cins" placeholder="Cins">
<input name="ebat" placeholder="Ebat">
<input name="kalinlik" placeholder="Kalınlık mm">
<input name="sinif" placeholder="Sınıf">

<select name="yuzey">
<option>HG</option>
<option>MAT</option>
</select>

<input name="renk" placeholder="Renk">
<input name="adet" placeholder="Adet">

<select name="depo">
{% for d in depolar %}
<option>{{d}}</option>
{% endfor %}
</select>

<button>Kaydet</button>
</form>
</div>
{% endif %}

<h3>📦 Ürünler</h3>

{% for u in urunler %}
<div class="card">

<b>{{u[2]}}</b><br>

{{u[3]}} | {{u[4]}} | {{u[5]}} mm<br>

<span class="badge {% if u[7]=='HG' %}hg{% else %}mat{% endif %}">
{{u[7]}}
</span>

<span class="badge">{{u[8]}}</span>

<br><br>

🏬 {{u[10]}}<br>
📦 Stok: <b>{{u[9]}}</b>

<br><br>

<a class="top-btn" href="/etiket/{{u[1]}}">🏷️ Etiket</a>

</div>
{% endfor %}

</div>

</body>
</html>
""", urunler=urunler, depolar=DEPOLAR)

# ---------------- ETİKET (QR + barkod) ----------------
@app.route("/etiket/<kod>")
def etiket(kod):
    import qrcode
    img = qrcode.make(kod)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    data = base64.b64encode(buf.getvalue()).decode()

    return f"""
    <h3>Barkod: {kod}</h3>
    <img src="data:image/png;base64,{data}">
    <br><button onclick="window.print()">YAZDIR</button>
    """

# ---------------- KAMERA ----------------
@app.route("/kamera")
def kamera():
    if not session.get("g"): return redirect("/")

    return """
    <h2>Barkod Okut</h2>
    <video id="preview" width="300"></video>

    <script src="https://unpkg.com/@ericblade/quagga2/dist/quagga.min.js"></script>

    <script>
    Quagga.init({
        inputStream: {type: "LiveStream", target: document.querySelector('#preview')},
        decoder: {readers: ["code_128_reader"]}
    }, function(err) {
        if (!err) Quagga.start();
    });

    Quagga.onDetected(function(data) {
        let kod = data.codeResult.code;
        window.location = "/cikis/" + kod;
    });
    </script>
    """
    return """
<!DOCTYPE html>
<html>
<head>
<style>
body{
    background:black;
    color:white;
    text-align:center;
    font-family:Arial;
}
video{
    width:90%;
    border-radius:10px;
    margin-top:20px;
}
</style>
</head>

<body>

<h2>📷 Barkod Okut</h2>
<video id="preview"></video>

<script src="https://unpkg.com/@ericblade/quagga2/dist/quagga.min.js"></script>

<script>
Quagga.init({
    inputStream: {
        type: "LiveStream",
        target: document.querySelector('#preview')
    },
    decoder: {
        readers: ["code_128_reader"]
    }
}, function(err) {
    if (!err) Quagga.start();
});

Quagga.onDetected(function(data) {
    let kod = data.codeResult.code;
    window.location = "/cikis/" + kod;
});
</script>

</body>
</html>
"""

# ---------------- ÇIKIŞ ----------------
@app.route("/cikis/<kod>", methods=["GET","POST"])
def cikis(kod):
    if not session.get("g"): return redirect("/")

    with db() as con:
        u=con.execute("SELECT * FROM urunler WHERE barkod=?",(kod,)).fetchone()

    if not u:
        return "❌ Ürün bulunamadı"

    if request.method=="POST":
        adet=int(request.form["adet"])
        if adet > u[9]:
            return "❌ Stok yetersiz"

        with db() as con:
            con.execute("UPDATE urunler SET adet=adet-? WHERE barkod=?",(adet,kod))
        log(session["user"],"CIKIS",kod,u[10],adet)

        return redirect("/panel")

    return f"""
    <h3>{u[2]}</h3>
    Cins: {u[3]}<br>
    Ebat: {u[4]}<br>
    Kalınlık: {u[5]}mm<br>
    {u[7]} / {u[6]}<br>
    Renk: {u[8]}<br>
    Depo: {u[10]}<br>
    Stok: {u[9]}<br><br>

    <form method="post">
    <input name="adet" placeholder="kaç adet">
    <button>ÇIKIŞ YAP</button>
    </form>
    """

# ---------------- LOG ----------------
@app.route("/log")
def logs():
    with db() as con:
        data=con.execute("SELECT * FROM log ORDER BY id DESC").fetchall()

    return render_template_string("""
    <h2>HAREKET</h2>
    {% for l in data %}
    <div>
    {{l[1]}} | {{l[2]}} | {{l[3]}} | {{l[4]}} | {{l[5]}} adet | {{l[6]}}
    </div>
    {% endfor %}
    """,data=data)

# ---------------- RUN ----------------
if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
