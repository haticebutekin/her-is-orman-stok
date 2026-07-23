from flask import Flask, render_template_string, request, redirect, session, send_file
import pandas as pd
from reportlab.pdfgen import canvas
from io import BytesIO
import datetime
import os

app = Flask(__name__)
app.secret_key = "heris_stok_guvenli_key"


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
    "HGLOSS DEPOSU",
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

        username = request.form.get("user")
        password = request.form.get("pass")

        if username in USERS and USERS[username] == password:
            session["user"] = username
            return redirect("/panel")

    return render_template_string("""
    
    <html>
    <head>
    <title>Her İş Stok Pro</title>
    </head>

    <body>

    <h1>HER İŞ STOK PRO</h1>

    <h2>Personel Giriş</h2>

    <form method="post">

    Kullanıcı:
    <input name="user"><br><br>

    Şifre:
    <input name="pass" type="password"><br><br>

    <button type="submit">
    GİRİŞ
    </button>

    </form>

    </body>
    </html>

    """)



# PANEL
@app.route("/panel", methods=["GET","POST"])
def panel():

    if "user" not in session:
        return redirect("/")


    if request.method == "POST":

        DATA.append({

            "tarih":
            datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),

            "personel":
            session["user"],

            "barkod":
            request.form.get("barkod"),

            "urun":
            request.form.get("urun"),

            "cins":
            request.form.get("cins"),

            "ebat":
            request.form.get("ebat"),

            "yuzey":
            request.form.get("yuzey"),

            "renk":
            request.form.get("renk"),

            "depo":
            request.form.get("depo")

        })



    return render_template_string("""

<html>

<head>

<title>Her İş Stok Pro</title>

<style>

body{
font-family:Arial;
margin:30px;
}

input,select{
padding:8px;
margin:5px;
}

button{
padding:10px;
background:#0066cc;
color:white;
border:0;
}

table{
border-collapse:collapse;
width:100%;
}

td,th{
border:1px solid black;
padding:8px;
}

</style>

</head>


<body>


<h1>HER İŞ STOK PRO</h1>

<h3>
Personel: {{user}}
</h3>



<form method="post">


Barkod:
<input name="barkod">


Ürün:
<input name="urun">


Mal Cinsi:
<input name="cins">


Ebat:
<input name="ebat">


Yüzey:

<select name="yuzey">

<option>HG</option>
<option>MAT</option>

</select>


Renk:

<input name="renk">


Depo:

<select name="depo">

{% for d in depos %}

<option>{{d}}</option>

{% endfor %}

</select>



<br><br>

<button>
KAYDET
</button>


</form>


<br>


<a href="/pdf">
PDF
</a>

|

<a href="/excel">
EXCEL
</a>

|

<a href="/logout">
ÇIKIŞ
</a>



<h2>Stok Kayıtları</h2>


<table>


<tr>

<th>Tarih</th>
<th>Personel</th>
<th>Barkod</th>
<th>Ürün</th>
<th>Cins</th>
<th>Ebat</th>
<th>Yüzey</th>
<th>Renk</th>
<th>Depo</th>


</tr>


{% for x in data %}


<tr>

<td>{{x.tarih}}</td>
<td>{{x.personel}}</td>
<td>{{x.barkod}}</td>
<td>{{x.urun}}</td>
<td>{{x.cins}}</td>
<td>{{x.ebat}}</td>
<td>{{x.yuzey}}</td>
<td>{{x.renk}}</td>
<td>{{x.depo}}</td>


</tr>


{% endfor %}


</table>



</body>

</html>


""",
user=session["user"],
data=DATA,
depos=DEPOS)




# PDF
@app.route("/pdf")
def pdf():

    buffer = BytesIO()

    c = canvas.Canvas(buffer)

    y = 800


    for x in DATA:

        c.drawString(
            30,
            y,
            f"{x['urun']} {x['barkod']} {x['depo']}"
        )

        y -= 20

        if y < 50:
            c.showPage()
            y = 800


    c.save()

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="stok_rapor.pdf"
    )




# EXCEL
@app.route("/excel")
def excel():

    if len(DATA)==0:
        return "Kayıt yok"


    df=pd.DataFrame(DATA)


    file=BytesIO()

    df.to_excel(
        file,
        index=False,
        engine="openpyxl"
    )


    file.seek(0)


    return send_file(
        file,
        as_attachment=True,
        download_name="stok.xlsx"
    )





# LOGOUT
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")





# RENDER
if __name__=="__main__":

    port=int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
    )
