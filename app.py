from flask import Flask, request, redirect, session
import sqlite3
import uuid
import os
import barcode
from barcode.writer import ImageWriter
import qrcode

app = Flask(__name__)
app.secret_key = "1234"

os.makedirs("static/barcodes", exist_ok=True)
os.makedirs("static/qrcodes", exist_ok=True)

# ---------------- DB ----------------
def db():
    return sqlite3.connect("db.db")

def init():
    con = db()

    con.execute('''CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY,
    username TEXT,
    password TEXT,
    role TEXT)''')

    con.execute('''CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY,
    barkod TEXT,
    ad TEXT,
    cins TEXT,
    ebat TEXT,
    sinif TEXT,
    renk TEXT,
    adet INTEGER,
    depo TEXT)''')

    con.execute('''CREATE TABLE IF NOT EXISTS hareket(
    id INTEGER PRIMARY KEY,
    barkod TEXT,
    islem TEXT,
    adet INTEGER,
    user TEXT,
    tarih DATETIME DEFAULT CURRENT_TIMESTAMP)''')

    # default kullanıcılar
    con.execute("INSERT OR IGNORE INTO users VALUES (1,'admin','123','admin')")
    con.execute("INSERT OR IGNORE INTO users VALUES (2,'depocu','123','depocu')")

    con.commit()

init()

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form['u']
        p = request.form['p']

        con = db()
        user = con.execute("SELECT * FROM users WHERE username=? AND password=?", (u,p)).fetchone()

        if user:
            session['user'] = user[1]
            session['role'] = user[3]
            return redirect('/panel')

    return '''
    <h2>Giriş</h2>
    <form method="POST">
    Kullanıcı: <input name="u"><br>
    Şifre: <input name="p"><br>
    <button>Giriş</button>
    </form>
    '''

# ---------------- PANEL ----------------
@app.route('/panel')
def panel():
    if 'user' not in session:
        return redirect('/')

    con = db()
    urunler = con.execute("SELECT * FROM products").fetchall()

    html = f"<h2>Hoşgeldin {session['user']} ({session['role']})</h2>"
    html += '<a href="/ekle">Ürün Ekle</a> | <a href="/okut">Barkod Okut</a> | <a href="/hareket">Hareket</a><hr>'

    for u in urunler:
        html += f"""
        <b>{u[2]}</b> | {u[7]} adet | {u[8]}<br>
        Barkod: {u[1]}<br>
        <img src="/static/barcodes/{u[1]}.png" width="150"><hr>
        """

    return html

# ---------------- BARKOD ----------------
def barkod():
    return str(uuid.uuid4())[:10]

# ---------------- ÜRÜN EKLE ----------------
@app.route('/ekle', methods=['GET','POST'])
def ekle():
    if session.get('role') != 'admin':
        return "Yetki yok!"

    if request.method == 'POST':
        data = request.form
        kod = barkod()

        # barcode
        code = barcode.get('code128', kod, writer=ImageWriter())
        code.save(f"static/barcodes/{kod}")

        # qr
        img = qrcode.make(kod)
        img.save(f"static/qrcodes/{kod}.png")

        con = db()
        con.execute('''INSERT INTO products
        (barkod, ad, cins, ebat, sinif, renk, adet, depo)
        VALUES (?,?,?,?,?,?,?,?)''',
        (kod, data['ad'], data['cins'], data['ebat'],
         data['sinif'], data['renk'], data['adet'], data['depo']))

        con.commit()
        return redirect('/panel')

    return '''
    <h2>Ürün Ekle</h2>
    <form method="POST">
    Ad: <input name="ad"><br>
    Cins: <input name="cins"><br>
    Ebat: <input name="ebat"><br>
    Sınıf: <input name="sinif"><br>
    Renk: <input name="renk"><br>
    Adet: <input name="adet"><br>

    Depo:
    <select name="depo">
    <option>MDF SATIŞ DEPOSU</option>
    <option>LAMİNANT DEPOSU</option>
    <option>KAPI DEPOSU</option>
    <option>HGLOSS DEPOSU</option>
    <option>SÜTÇÜ YANI</option>
    <option>HELVACI YANI</option>
    <option>RÖTBALANSÇI YANI</option>
    <option>KESİMHANE</option>
    </select><br><br>

    <button>Kaydet</button>
    </form>
    '''

# ---------------- OKUT ----------------
@app.route('/okut')
def okut():
    return '''
    <h2>Barkod Okut</h2>

    <script src="https://unpkg.com/html5-qrcode"></script>
    <div id="reader"></div>

    <form method="POST" action="/cikis">
    Barkod: <input id="barkod" name="barkod"><br>
    Adet: <input name="adet"><br>
    <button>Çıkış Yap</button>
    </form>

    <script>
    function onScanSuccess(text){
        document.getElementById("barkod").value = text;
    }
    new Html5QrcodeScanner("reader").render(onScanSuccess);
    </script>
    '''

# ---------------- ÇIKIŞ ----------------
@app.route('/cikis', methods=['POST'])
def cikis():
    kod = request.form['barkod']
    adet = int(request.form['adet'])

    con = db()
    urun = con.execute("SELECT adet FROM products WHERE barkod=?", (kod,)).fetchone()

    if not urun:
        return "Ürün yok!"

    if urun[0] < adet:
        return "Stok yetersiz!"

    con.execute("UPDATE products SET adet=adet-? WHERE barkod=?", (adet, kod))
    con.execute("INSERT INTO hareket (barkod,islem,adet,user) VALUES (?,?,?,?)",
                (kod,'CIKIS',adet,session['user']))

    con.commit()
    return redirect('/panel')

# ---------------- HAREKET ----------------
@app.route('/hareket')
def hareket():
    con = db()
    h = con.execute("SELECT * FROM hareket ORDER BY id DESC").fetchall()

    html = "<h2>Hareketler</h2><hr>"
    for i in h:
        html += f"{i[1]} | {i[2]} | {i[3]} adet | {i[4]} | {i[5]}<br>"

    return html

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)
