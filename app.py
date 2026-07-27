from flask import Flask, request, redirect, session, render_template_string
import sqlite3, datetime, os

app = Flask(__name__)
app.secret_key = "123"

def db():
    return sqlite3.connect("stok.db")

# ---------------- DB ----------------
with db() as con:
    con.execute("CREATE TABLE IF NOT EXISTS urunler(id INTEGER PRIMARY KEY,barkod TEXT,isim TEXT,adet INT,depo TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT,password TEXT,role TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS log(id INTEGER PRIMARY KEY,user TEXT,islem TEXT,barkod TEXT,tarih TEXT)")

    if not con.execute("SELECT * FROM users").fetchall():
        con.execute("INSERT INTO users VALUES(NULL,'admin','123','admin')")
        con.execute("INSERT INTO users VALUES(NULL,'depo','123','depo')")
        con.execute("INSERT INTO users VALUES(NULL,'satis','123','satis')")

# ---------------- LOG ----------------
def log(user,islem,kod):
    with db() as con:
        con.execute("INSERT INTO log VALUES(NULL,?,?,?,?)",(user,islem,kod,str(datetime.datetime.now())))

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
    <input name="k" placeholder="kullanıcı"><br>
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
            con.execute("INSERT INTO urunler VALUES(NULL,?,?,?,?)",
                        (kod,request.form["isim"],int(request.form["adet"]),request.form["depo"]))
        log(session["user"],"EKLE",kod)

    with db() as con:
        urunler=con.execute("SELECT * FROM urunler ORDER BY id DESC").fetchall()

    return render_template_string("""
    <h3>{{session['user']}} ({{session['role']}})</h3>

    {% if session["role"]=="admin" %}
    <form method="post">
    <input name="isim" placeholder="ürün">
    <input name="adet" placeholder="adet">
    <input name="depo" placeholder="depo">
    <button>EKLE</button>
    </form>
    {% endif %}

    <hr>

    {% for u in urunler %}
    <div style="border:1px solid;padding:6px;margin:6px">
    {{u[2]}} | {{u[4]}} | Adet: {{u[3]}} <br>

    {% if u[3] <= 5 %}
    <b style="color:red">DÜŞÜK STOK</b><br>
    {% endif %}

    <a href="/sat/{{u[1]}}">SAT</a>
    </div>
    {% endfor %}

    <br><a href="/log">LOG</a>
    """,urunler=urunler)

# ---------------- SAT ----------------
@app.route("/sat/<kod>")
def sat(kod):
    if not session.get("g"): return redirect("/")

    with db() as con:
        s=con.execute("SELECT adet FROM urunler WHERE barkod=?",(kod,)).fetchone()
        if s and s[0]>0:
            con.execute("UPDATE urunler SET adet=adet-1 WHERE barkod=?",(kod,))
            log(session["user"],"SAT",kod)

    return redirect("/panel")

# ---------------- LOG ----------------
@app.route("/log")
def logs():
    with db() as con:
        data=con.execute("SELECT * FROM log ORDER BY id DESC").fetchall()

    return render_template_string("""
    <h2>LOG</h2>
    {% for l in data %}
    <div>{{l[1]}} | {{l[2]}} | {{l[3]}} | {{l[4]}}</div>
    {% endfor %}
    """,data=data)

# ---------------- RUN ----------------
if __name__=="__main__":
    app.run(host="0.0.0.0",port=10000)
