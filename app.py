from flask import Flask, render_template_string, request, redirect, session, jsonify
import sqlite3, random, datetime

app = Flask(__name__)
app.secret_key = "1234"

# DB
def db():
    return sqlite3.connect("db.sqlite")

with db() as con:
    con.execute("CREATE TABLE IF NOT EXISTS urun (id INTEGER PRIMARY KEY, ad TEXT, marka TEXT, fiyat REAL, barkod TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS satis (id INTEGER PRIMARY KEY, tarih TEXT, toplam REAL)")

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["user"]=="admin" and request.form["pass"]=="1234":
            session["login"]=True
            return redirect("/kasa")
    return '''
    <h2>Admin Giriş</h2>
    <form method="post">
    Kullanıcı: <input name="user"><br>
    Şifre: <input name="pass" type="password"><br>
    <button>Giriş</button>
    </form>
    '''

# KASA
@app.route("/kasa")
def kasa():
    if "login" not in session:
        return redirect("/")
    return render_template_string("""
<h2>🛒 PRO KASA</h2>

<input id="barkod" placeholder="Barkod okut">
<button onclick="ekle()">Ekle</button>

<ul id="liste"></ul>
<h3 id="toplam">Toplam: 0 TL</h3>

<button onclick="satis()">Satışı Bitir</button>

<script>
let sepet=[];

function ekle(){
 let kod=document.getElementById("barkod").value;
 fetch("/urun/"+kod)
 .then(r=>r.json())
 .then(d=>{
    if(d.ad){
        sepet.push(d);
        goster();
    } else alert("Ürün yok");
 });
}

function goster(){
 let html="";
 let toplam=0;
 sepet.forEach(x=>{
   html+=x.ad+" ("+x.marka+") - "+x.fiyat+" TL<br>";
   toplam+=x.fiyat;
 });
 document.getElementById("liste").innerHTML=html;
 document.getElementById("toplam").innerHTML="Toplam: "+toplam+" TL";
}

function satis(){
 fetch("/satis",{
   method:"POST",
   headers:{'Content-Type':'application/json'},
   body:JSON.stringify(sepet)
 }).then(()=>location.reload());
}
</script>
""")

# ÜRÜN EKLE
@app.route("/urun-ekle", methods=["GET","POST"])
def urun_ekle():
    if request.method=="POST":
        barkod=str(random.randint(1000000000000,9999999999999))
        with db() as con:
            con.execute("INSERT INTO urun (ad,marka,fiyat,barkod) VALUES (?,?,?,?)",
                        (request.form["ad"],request.form["marka"],request.form["fiyat"],barkod))
        return "Kaydedildi Barkod:"+barkod

    return '''
    <h2>Ürün Ekle</h2>
    <form method="post">
    Ad: <input name="ad"><br>
    Marka: <input name="marka"><br>
    Fiyat: <input name="fiyat"><br>
    <button>Kaydet</button>
    </form>
    '''

# ÜRÜN GETİR
@app.route("/urun/<kod>")
def urun(kod):
    with db() as con:
        cur=con.execute("SELECT ad,marka,fiyat FROM urun WHERE barkod=?",(kod,))
        r=cur.fetchone()
        if r:
            return jsonify({"ad":r[0],"marka":r[1],"fiyat":r[2]})
    return jsonify({})

# SATIŞ
@app.route("/satis", methods=["POST"])
def satis():
    data=request.json
    toplam=sum([x["fiyat"] for x in data])
    with db() as con:
        con.execute("INSERT INTO satis (tarih,toplam) VALUES (?,?)",
                    (str(datetime.datetime.now()),toplam))
    print("FIŞ -> TOPLAM:",toplam,"TL")  # yazıcı yerine
    return "ok"

# RAPOR
@app.route("/rapor")
def rapor():
    with db() as con:
        cur=con.execute("SELECT tarih,toplam FROM satis")
        data=cur.fetchall()

    labels=[x[0][:10] for x in data]
    values=[x[1] for x in data]

    return render_template_string("""
<h2>📊 Satış Rapor</h2>
<canvas id="c"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
new Chart(document.getElementById("c"),{
 type:"line",
 data:{
  labels:{{labels|safe}},
  datasets:[{label:"Satış",data:{{values|safe}}}]
 }
});
</script>
""",labels=labels,values=values)

app.run(debug=True)
