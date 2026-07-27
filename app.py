from flask import Flask, request, redirect, session, render_template_string, send_file
import sqlite3, os, datetime
from barcode import Code128
from barcode.writer import ImageWriter
from openpyxl import Workbook

app = Flask(__name__)
app.secret_key = "12345"

DB = "stok.db"

def db():
    return sqlite3.connect(DB)

def init_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS urunler(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barkod TEXT,
            isim TEXT,
            cins TEXT,
            ebat TEXT,
            kalinlik TEXT,
            sinif TEXT,
            yuzey TEXT,
            renk TEXT,
            adet INTEGER,
            depo TEXT,
            tarih TEXT
        )
        """)
init_db()

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        if request.form["k"] == "admin" and request.form["s"] == "1234":
            session["ok"] = True
            return redirect("/panel")

    return """
    <style>
    body {background:#0f172a;color:white;font-family:sans-serif;text-align:center;}
    .box {margin-top:100px;}
    input {padding:10px;margin:5px;border-radius:8px;border:none;}
    button {padding:10px 20px;background:#22c55e;color:white;border:none;border-radius:8px;}
    </style>

    <div class="box">
    <h1>🌲 HER İŞ ORMAN STOK PRO</h1>
    <form method="post">
    <input name="k" placeholder="Kullanıcı"><br>
    <input name="s" type="password" placeholder="Şifre"><br>
    <button>Giriş</button>
    </form>
    </div>
    """

# ---------------- PANEL ----------------
@app.route("/panel", methods=["GET","POST"])
def panel():
    if not session.get("ok"):
        return redirect("/")

    if request.method == "POST":
        barkod = "HER-" + str(int(datetime.datetime.now().timestamp()))

        Code128(barkod, writer=ImageWriter()).save("static/" + barkod)

        with db() as con:
            con.execute("""
            INSERT INTO urunler(barkod,isim,cins,ebat,kalinlik,sinif,yuzey,renk,adet,depo,tarih)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,(
                barkod,
                request.form["isim"],
                request.form["cins"],
                request.form["ebat"],
                request.form["kalinlik"],
                request.form["sinif"],
                request.form["yuzey"],
                request.form["renk"],
                int(request.form["adet"]),
                request.form["depo"],
                str(datetime.datetime.now())
            ))

        return redirect("/panel")

    urunler = db().execute("SELECT * FROM urunler ORDER BY id DESC").fetchall()

    return render_template_string("""
    <style>
    body {background:#0f172a;color:white;font-family:sans-serif;}
    h1 {color:#22c55e;}
    form input, select {
        padding:8px;
        margin:4px;
        border-radius:6px;
        border:none;
    }
    button {
        background:#22c55e;
        color:white;
        border:none;
        padding:10px;
        border-radius:6px;
        cursor:pointer;
    }
    table {
        width:100%;
        margin-top:20px;
        border-collapse:collapse;
    }
    th {background:#22c55e;color:black;}
    td, th {padding:8px;text-align:center;}
    tr:nth-child(even){background:#1e293b;}
    tr:nth-child(odd){background:#334155;}
    a {color:#38bdf8;text-decoration:none;}
    </style>

    <h1>🌲 HER İŞ ORMAN STOK TAKİBİ</h1>

    <form method="post">
    <input name="isim" placeholder="İsim">
    <input name="cins" placeholder="Cins">
    <input name="ebat" placeholder="Ebat mm">
    <input name="kalinlik" placeholder="Kalınlık">
    <input name="sinif" placeholder="Sınıf">
    
    <select name="yuzey">
        <option>HG</option>
        <option>MAT</option>
        <option>PARLAK</option>
    </select>

    <input name="renk" placeholder="Renk">
    <input name="adet" type="number" placeholder="Adet">

    <select name="depo">
        <option>MDF SATIŞ DEPOSU</option>
        <option>LAMİNANT DEPOSU</option>
        <option>KAPI DEPOSU</option>
        <option>HGLOSS DEPOSU</option>
        <option>SÜTÇÜ YANI</option>
        <option>HELVACI YANI</option>
        <option>RÖTBALANSÇI YANI</option>
        <option>KESİMHANE</option>
    </select>

    <button>➕ EKLE</button>
    </form>

    <br>
    <a href="/kamera">📷 Barkod Oku</a> |
    <a href="/excel">📊 Excel</a>

    <table>
    <tr>
    <th>Barkod</th>
    <th>İsim</th>
    <th>Adet</th>
    <th>Depo</th>
    <th>İşlem</th>
    </tr>

    {% for u in urunler %}
    <tr>
    <td>{{u[1]}}</td>
    <td>{{u[2]}}</td>
    <td>{{u[9]}}</td>
    <td>{{u[10]}}</td>
    <td>
    <a href="/dus/{{u[1]}}">➖</a>
    <a href="/etiket/{{u[1]}}">🧾</a>
    </td>
    </tr>
    {% endfor %}
    </table>
    """, urunler=urunler)

# ---------------- STOK DÜŞ ----------------
@app.route("/dus/<kod>")
def dus(kod):
    with db() as con:
        con.execute("UPDATE urunler SET adet = adet - 1 WHERE barkod=?",(kod,))
    return redirect("/panel")

# ---------------- KAMERA ----------------
@app.route("/kamera")
def kamera():
    return """
    <script src="https://unpkg.com/@zxing/library@latest"></script>
    <video id="v" width="300"></video>
    <script>
    let codeReader = new ZXing.BrowserBarcodeReader()
    codeReader.decodeFromVideoDevice(null, 'v', (result, err) => {
        if(result){
            window.location="/dus/"+result.text
        }
    })
    </script>
    """

# ---------------- ETİKET ----------------
@app.route("/etiket/<kod>")
def etiket(kod):
    return f"""
    <h2>{kod}</h2>
    <img src="/static/{kod}.png">
    <br><button onclick="window.print()">Yazdır</button>
    """

# ---------------- EXCEL ----------------
@app.route("/excel")
def excel():
    wb = Workbook()
    ws = wb.active
    ws.append(["Barkod","İsim","Adet","Depo"])

    data = db().execute("SELECT barkod,isim,adet,depo FROM urunler").fetchall()
    for d in data:
        ws.append(d)

    file = "rapor.xlsx"
    wb.save(file)
    return send_file(file, as_attachment=True)

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
