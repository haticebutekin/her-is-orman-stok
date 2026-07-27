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
    <h3>{{session['user']}} ({{session['role']}})</h3>

    <a href="/kamera">📷 Barkod Okut</a><br>
    <a href="/log">📋 Hareket</a><br><br>

    {% if session["role"]=="admin" %}
    <h3>ÜRÜN EKLE</h3>
    <form method="post">
    <input name="isim" placeholder="Mal adı"><br>
    <input name="cins" placeholder="Cins"><br>
    <input name="ebat" placeholder="Ebat"><br>
    <input name="kalinlik" placeholder="mm"><br>
    <input name="sinif" placeholder="Sınıf"><br>
    <select name="yuzey">
        <option>HG</option>
        <option>MAT</option>
    </select><br>
    <input name="renk" placeholder="Renk"><br>
    <input name="adet" placeholder="Adet"><br>

    <select name="depo">
    {% for d in depolar %}
        <option>{{d}}</option>
    {% endfor %}
    </select><br>

    <button>EKLE</button>
    </form>
    {% endif %}

    <hr>

    {% for u in urunler %}
    <div style="border:1px solid;padding:6px;margin:6px">
    {{u[2]}} | {{u[3]}} | {{u[4]}} | {{u[5]}}mm | {{u[6]}} | {{u[7]}} | {{u[8]}}<br>
    Depo: {{u[10]}} | Adet: {{u[9]}}<br>

    <a href="/etiket/{{u[1]}}">🏷️ Etiket</a>
    </div>
    {% endfor %}
    """,urunler=urunler,depolar=DEPOLAR)

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
