from flask import Flask, render_template_string, request, redirect, session, send_file
import pandas as pd
from reportlab.pdfgen import canvas
from io import BytesIO
import datetime
import os

app = Flask(__name__)
app.secret_key = "secret123"

# PERSONELLER
USERS = {
    "behic": "123",
    "ramazan": "123",
    "orhan": "123"
}

# DEPOLAR
DEPOS = [
    "MDF SATIŞ DEPOSU",
    "LAMİNANT DEPOSU",
    "KAPI DEPOSU",
    "HGLOSS DEPOSU (MORAY YANI)",
    "SÜTÇÜ YANI",
    "HELVACI YANI",
    "RÖTBALANSÇI YANI",
    "KESİMHANE"
]

DATA = []

# LOGIN
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["user"]
        p = request.form["pass"]
        if u in USERS and USERS[u] == p:
            session["user"] = u
            return redirect("/panel")
    return render_template_string("""
    <h2>Personel Giriş</h2>
    <form method="post">
        Kullanıcı: <input name="user"><br>
        Şifre: <input name="pass" type="password"><br>
        <button>Giriş</button>
    </form>
    """)

# PANEL
@app.route("/panel", methods=["GET", "POST"])
def panel():
    if "user" not in session:
        return redirect("/")

    if request.method == "POST":
        barkod = request.form["barkod"]
        urun = request.form["urun"]
        cins = request.form["cins"]
        ebat = request.form["ebat"]
        yuzey = request.form["yuzey"]
        renk = request.form["renk"]
        depo = request.form["depo"]

        DATA.append({
            "tarih": datetime.datetime.now(),
            "personel": session["user"],
            "barkod": barkod,
            "urun": urun,
            "cins": cins,
            "ebat": ebat,
            "yuzey": yuzey,
            "renk": renk,
            "depo": depo
        })

    return render_template_string("""
    <h2>Hoşgeldin {{user}}</h2>

    <video id="cam" width="300" autoplay></video>
    <button onclick="startCam()">Kamera Aç</button>

    <form method="post">
        Barkod: <input name="barkod" id="barkod"><br>
        Ürün Adı: <input name="urun"><br>
        Mal Cinsi: <input name="cins"><br>
        Ebat: <input name="ebat"><br>

        Yüzey:
        <select name="yuzey">
            <option>HG</option>
            <option>MAT</option>
        </select><br>

        Renk: <input name="renk"><br>

        Depo:
        <select name="depo">
            {% for d in depos %}
            <option>{{d}}</option>
            {% endfor %}
        </select><br>

        <button>Kaydet</button>
    </form>

    <br>
    <a href="/pdf">PDF Yazdır</a> |
    <a href="/excel">Excel Al</a>

    <h3>Kayıtlar</h3>
    <table border=1>
        <tr>
            <th>Tarih</th><th>Personel</th><th>Barkod</th>
            <th>Ürün</th><th>Cins</th><th>Ebat</th>
            <th>Yüzey</th><th>Renk</th><th>Depo</th>
        </tr>
        {% for d in data %}
        <tr>
            <td>{{d.tarih}}</td>
            <td>{{d.personel}}</td>
            <td>{{d.barkod}}</td>
            <td>{{d.urun}}</td>
            <td>{{d.cins}}</td>
            <td>{{d.ebat}}</td>
            <td>{{d.yuzey}}</td>
            <td>{{d.renk}}</td>
            <td>{{d.depo}}</td>
        </tr>
        {% endfor %}
    </table>

    <script>
    function startCam(){
        navigator.mediaDevices.getUserMedia({video:true})
        .then(stream => {
            document.getElementById('cam').srcObject = stream;
        });
    }
    </script>
    """, user=session["user"], data=DATA, depos=DEPOS)

# PDF
@app.route("/pdf")
def pdf():
    buffer = BytesIO()
    c = canvas.Canvas(buffer)

    y = 800
    for d in DATA:
        c.drawString(30, y, f"{d['urun']} - {d['barkod']} - {d['depo']}")
        y -= 20

    c.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="etiket.pdf")

# EXCEL
@app.route("/excel")
def excel():
    df = pd.DataFrame(DATA)
    file = BytesIO()
    df.to_excel(file, index=False)
    file.seek(0)
    return send_file(file, as_attachment=True, download_name="rapor.xlsx")

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# RENDER FIX
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
