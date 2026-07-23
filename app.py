from flask import Flask, render_template_string, request, redirect, session, send_file
from reportlab.pdfgen import canvas
from io import BytesIO
import datetime
import os
import csv

app = Flask(__name__)
app.secret_key = "heris_stok_guvenli_key"


USERS = {
    "behic": "123",
    "ramazan": "123",
    "orhan": "123"
}


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


@app.route("/", methods=["GET","POST"])
def login():

    if request.method=="POST":

        user=request.form.get("user")
        password=request.form.get("pass")

        if user in USERS and USERS[user]==password:
    session["user"]=user
    return redirect("/panel")
else:
    return """
    <h3 style='color:red'>
    Kullanıcı adı veya şifre yanlış
    </h3>
    <a href='/'>Geri dön</a>
    """


    return """
    <html>
    <body>

    <h1>HER İŞ STOK PRO</h1>

    <h3>Personel Giriş</h3>

    <form method="post">

    Kullanıcı:
    <input name="user">

    <br><br>

    Şifre:
    <input name="pass" type="password">

    <br><br>

    <button>GİRİŞ</button>

    </form>

    </body>
    </html>
    """



@app.route("/panel", methods=["GET","POST"])
def panel():

    if "user" not in session:
        return redirect("/")


    if request.method=="POST":

        DATA.append({

        "tarih":
        datetime.datetime.now().strftime("%d.%m.%Y %H:%M"),

        "personel":
        session["user"],

        "barkod":
        request.form.get("barkod",""),

        "urun":
        request.form.get("urun",""),

        "cins":
        request.form.get("cins",""),

        "ebat":
        request.form.get("ebat",""),

        "yuzey":
        request.form.get("yuzey",""),

        "renk":
        request.form.get("renk",""),

        "depo":
        request.form.get("depo","")

        })


    return render_template_string("""

<h1>HER İŞ STOK PRO</h1>

<h3>Personel: {{user}}</h3>


<form method="post">

Barkod:
<input name="barkod">

<br>

Ürün:
<input name="urun">

<br>

Mal Cinsi:
<input name="cins">

<br>

Ebat:
<input name="ebat">

<br>

Yüzey:

<select name="yuzey">
<option>HG</option>
<option>MAT</option>
</select>

<br>

Renk:
<input name="renk">

<br>

Depo:

<select name="depo">

{% for d in depos %}
<option>{{d}}</option>
{% endfor %}

</select>


<br><br>

<button>KAYDET</button>

</form>


<br>

<a href="/pdf">PDF</a>

|

<a href="/csv">CSV</a>

|

<a href="/logout">ÇIKIŞ</a>



<h2>Kayıtlar</h2>


<table border="1">

<tr>
<th>Tarih</th>
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

""",
user=session["user"],
data=DATA,
depos=DEPOS)



@app.route("/pdf")
def pdf():

    file=BytesIO()

    c=canvas.Canvas(file)

    y=800


    for x in DATA:

        c.drawString(
        30,
        y,
        f"{x['urun']} {x['barkod']} {x['depo']}"
        )

        y-=20

        if y<50:
            c.showPage()
            y=800


    c.save()

    file.seek(0)


    return send_file(
        file,
        as_attachment=True,
        download_name="stok.pdf"
    )



@app.route("/csv")
def csv():

    file=BytesIO()

    text="Tarih,Barkod,Urun,Cins,Ebat,Yuzey,Renk,Depo\n"

    for x in DATA:

        text+=f"{x['tarih']},{x['barkod']},{x['urun']},{x['cins']},{x['ebat']},{x['yuzey']},{x['renk']},{x['depo']}\n"


    file.write(text.encode("utf-8-sig"))

    file.seek(0)


    return send_file(
        file,
        as_attachment=True,
        download_name="stok.csv"
    )



@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")



if __name__=="__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT",10000))
    )
