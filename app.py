from flask import Flask, request, redirect, session
import sqlite3, uuid, datetime

app = Flask(__name__)
app.secret_key = "123"

def db():
    return sqlite3.connect("db.sqlite3")

def kur():
    conn=db(); c=conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    username TEXT,
    password TEXT,
    role TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY,
    name TEXT,
    type TEXT,
    ebat TEXT,
    kalinlik TEXT,
    yuzey TEXT,
    color TEXT,
    adet INTEGER,
    depo TEXT,
    barcode TEXT)""")

    c.execute("""CREATE TABLE IF NOT EXISTS hareket(
    id INTEGER PRIMARY KEY,
    user TEXT,
    islem TEXT,
    urun TEXT,
    adet INTEGER,
    depo TEXT,
    saat TEXT)""")

    c.execute("DELETE FROM users")
    c.execute("INSERT INTO users VALUES(NULL,'admin','123','yonetici')")
    c.execute("INSERT INTO users VALUES(NULL,'depocu','123','depocu')")

    conn.commit(); conn.close()

kur()

DEPOLAR = [
"MDF SATIŞ DEPOSU","LAMİNANT DEPOSU","KAPI DEPOSU",
"HGLOSS DEPOSU (MORAY YANI)","SÜTÇÜ YANI","HELVACI YANI",
"RÖTBALANSÇI YANI","KESİMHANE"
]

# LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u=request.form["u"]; p=request.form["p"]
        conn=db(); c=conn.cursor()
        user=c.execute("SELECT * FROM users WHERE username=? AND password=?",(u,p)).fetchone()
        conn.close()
        if user:
            session["user"]=u
            session["role"]=user[3]
            return redirect("/panel")
        return "Hatalı giriş"

    return """
    <h2>Giriş</h2>
    <form method=post>
    Kullanıcı<input name=u><br>
    Şifre<input type=password name=p><br>
    <button>GİR</button>
    </form>
    """

# PANEL
@app.route("/panel")
def panel():
    if "user" not in session: return redirect("/")
    return """
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <body style="font-family:Arial;text-align:center;background:#111;color:white">
    <h2>📦 STOK PANEL</h2>

    <a href='/ekle' style='display:block;margin:15px;padding:20px;background:#0a84ff;color:white;border-radius:10px'>➕ ÜRÜN EKLE</a>
    <a href='/okut' style='display:block;margin:15px;padding:20px;background:#34c759;color:white;border-radius:10px'>📤 ÇIKIŞ</a>
    <a href='/kamera' style='display:block;margin:15px;padding:20px;background:#ff9f0a;color:white;border-radius:10px'>📷 OKUT</a>
    <a href='/liste' style='display:block;margin:15px;padding:20px;background:#5856d6;color:white;border-radius:10px'>📋 STOK</a>
    <a href='/hareket' style='display:block;margin:15px;padding:20px;background:#ff375f;color:white;border-radius:10px'>📊 HAREKET</a>
    </body>
    """

# ÜRÜN EKLE
@app.route("/ekle", methods=["GET","POST"])
def ekle():
    if session.get("role")!="yonetici": return "Yetki yok"

    if request.method=="POST":
        if not request.form.get("kalinlik") or not request.form.get("yuzey"):
            return "❌ Kalınlık ve Yüzey seç!"

        data = (
            request.form["name"],
            request.form["type"],
            request.form["ebat"],
            request.form["kalinlik"],
            request.form["yuzey"],
            request.form["color"],
            int(request.form["adet"]),
            request.form["depo"],
            str(uuid.uuid4())[:12]
        )

        conn=db(); c=conn.cursor()
        c.execute("INSERT INTO products VALUES(NULL,?,?,?,?,?,?,?,?,?)",data)
        conn.commit(); conn.close()

        return "✅ EKLENDİ <br><a href='/panel'>Geri</a>"

    depo_options = "".join([f"<option>{d}</option>" for d in DEPOLAR])

    return f"""
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <body style="font-family:Arial;text-align:center">

    <h2>ÜRÜN EKLE</h2>

    <form method=post>

    <input name=name placeholder="Mal adı"><br>
    <input name=type placeholder="Cinsi"><br>
    <input name=ebat placeholder="Ebat (2100x2800)"><br>

    <h3>Kalınlık</h3>
    <button type=button onclick="secK('8')" style='padding:15px'>8 mm</button>
    <button type=button onclick="secK('18')" style='padding:15px'>18 mm</button>
    <button type=button onclick="secK('25')" style='padding:15px'>25 mm</button>

    <input type=hidden name=kalinlik id=kalinlik>

    <h3>Yüzey</h3>
    <button type=button onclick="secY('HG')" style='padding:15px;background:#0a84ff;color:white'>HG</button>
    <button type=button onclick="secY('MAT')" style='padding:15px;background:#555;color:white'>MAT</button>

    <input type=hidden name=yuzey id=yuzey>

    <br><br>
    <input name=color placeholder="Renk"><br>
    <input name=adet placeholder="Adet"><br>

    <select name=depo>{depo_options}</select><br><br>

    <button style="padding:20px;font-size:20px">EKLE</button>

    </form>

    <script>
    function secK(x) {{
        document.getElementById("kalinlik").value = x;
        alert("Kalınlık: " + x);
    }}

    function secY(x) {{
        document.getElementById("yuzey").value = x;
        alert("Yüzey: " + x);
    }}
    </script>

    </body>
    """

# STOK
@app.route("/liste")
def liste():
    conn=db(); c=conn.cursor()
    data=c.execute("SELECT * FROM products").fetchall()
    conn.close()

    html="<h2>STOK</h2>"
    for i in data:
        html+=f"""
        <div style='border:1px solid #ccc;padding:10px;margin:10px'>
        <b>{i[1]}</b><br>
        {i[2]}<br>
        Ebat: {i[3]}<br>
        Kalınlık: {i[4]} mm<br>
        Yüzey: {i[5]}<br>
        Renk: {i[6]}<br>
        Stok: {i[7]}<br>
        Depo: {i[8]}<br>
        Barkod: {i[9]}
        </div>
        """
    return html

<h3>Kalınlık Seç (mm)</h3>

<div id="kalinlikGrup" style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center">

<button type="button" onclick="secK(this,'4')">4</button>
<button type="button" onclick="secK(this,'6')">6</button>
<button type="button" onclick="secK(this,'8')">8</button>
<button type="button" onclick="secK(this,'10')">10</button>
<button type="button" onclick="secK(this,'12')">12</button>
<button type="button" onclick="secK(this,'18')">18</button>
<button type="button" onclick="secK(this,'30')">30</button>
<button type="button" onclick="secK(this,'35')">35</button>

</div>
"""
<input type="hidden" name="kalinlik" id="kalinlik" required>
# OKUT
@app.route("/okut", methods=["GET","POST"])
def okut():
    if session.get("role")!="depocu": return "Yetki yok"

    barkod=request.args.get("barkod")

    if request.method=="POST" or barkod:
        if not barkod:
            barkod=request.form["barkod"]

        adet=int(request.form.get("adet",1))

        conn=db(); c=conn.cursor()
        u=c.execute("SELECT * FROM products WHERE barcode=?",(barkod,)).fetchone()

        if not u: return "Ürün yok"
        if u[7]<adet: return "Stok yetersiz"

        yeni=u[7]-adet
        c.execute("UPDATE products SET adet=? WHERE barcode=?",(yeni,barkod))

        c.execute("INSERT INTO hareket VALUES(NULL,?,?,?,?,?,?)",
        (session["user"],"ÇIKIŞ",u[1],adet,u[8],datetime.datetime.now().strftime("%H:%M:%S")))

        conn.commit(); conn.close()

        return f"OK | {u[1]} | Kalan:{yeni}"

    return """
    <h2>BARKOD</h2>
    <form method=post>
    <input name=barkod>
    <input name=adet value=1>
    <button>ÇIKIŞ</button>
    </form>
    """
<script>
function kontrolEt(){
    let k = document.getElementById("kalinlik").value;

    if(!k){
        alert("Kalınlık seç!");
        return false;
    }
    return true;
}
</script>
# KAMERA
@app.route("/kamera")
def kamera():
    return """
    <script src="https://unpkg.com/html5-qrcode"></script>
    <div id="reader"></div>
    <script>
    function onScanSuccess(decodedText) {
        window.location="/okut?barkod="+decodedText;
    }
    new Html5QrcodeScanner("reader").render(onScanSuccess);
    </script>
    """

# HAREKET
@app.route("/hareket")
def hareket():
    conn=db(); c=conn.cursor()
    data=c.execute("SELECT * FROM hareket ORDER BY id DESC").fetchall()
    conn.close()

    html="<h2>HAREKET</h2>"
    for i in data:
        html+=f"{i[1]} | {i[2]} | {i[3]} | {i[4]} | {i[5]} | {i[6]}<br>"
    return html

if __name__ == "__main__":
    app.run(debug=True)
