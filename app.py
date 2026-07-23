from flask import Flask,request,redirect,session,render_template_string
import sqlite3
import os
from datetime import datetime

app=Flask(__name__)
app.secret_key="her_is_orman_guvenlik"


DB="stok.db"


USERS={
    "behic":"123",
    "ramazan":"123",
    "orhan":"123"
}


DEPOLAR=[
"MDF SATIŞ DEPOSU",
"LAMİNANT DEPOSU",
"KAPI DEPOSU",
"HGLOSS DEPOSU",
"KESİMHANE"
]


def db():

    con=sqlite3.connect(DB)

    con.execute("""
    CREATE TABLE IF NOT EXISTS urunler(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tarih TEXT,
    barkod TEXT,
    isim TEXT,
    cins TEXT,
    ebat TEXT,
    kalinlik TEXT,
    sinif TEXT,
    yuzey TEXT,
    renk TEXT,
    adet INTEGER,
    depo TEXT
    )
    """)

    con.commit()

    return con



@app.route("/",methods=["GET","POST"])
def login():

    if request.method=="POST":

        u=request.form["user"]
        p=request.form["pass"]

        if u in USERS and USERS[u]==p:

            session["user"]=u

            return redirect("/panel")


    return """
    <html>
    <body style="font-family:Arial;text-align:center">

    <h1>HER İŞ ORMAN ÜRÜNLERİ
    STOK TAKİBİ</h1>

    <form method="post">

    Kullanıcı<br>
    <input name="user"><br><br>

    Şifre<br>
    <input name="pass" type="password"><br><br>

    <button>GİRİŞ</button>

    </form>

    </body>
    </html>
    """





@app.route("/panel",methods=["GET","POST"])
def panel():

    if "user" not in session:
        return redirect("/")


    con=db()


    if request.method=="POST":

        con.execute("""
        INSERT INTO urunler
        VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
        datetime.now().strftime("%d.%m.%Y %H:%M"),
        request.form["barkod"],
        request.form["isim"],
        request.form["cins"],
        request.form["ebat"],
        request.form["kalinlik"],
        request.form["sinif"],
        request.form["yuzey"],
        request.form["renk"],
        request.form["adet"],
        request.form["depo"]
        ))

        con.commit()



    rows=con.execute(
    "SELECT * FROM urunler ORDER BY id DESC"
    ).fetchall()


    con.close()



    return render_template_string("""
    
    <style>

    body{
    font-family:Arial;
    background:#f2f2f2;
    padding:20px;
    }

    .box{
    background:white;
    padding:20px;
    border-radius:15px;
    }

    input,select{
    padding:8px;
    margin:5px;
    }

    button{
    padding:12px;
    background:#0066cc;
    color:white;
    border:0;
    border-radius:8px;
    }

    table{
    width:100%;
    background:white;
    border-collapse:collapse;
    }

    td,th{
    border:1px solid #ddd;
    padding:8px;
    }

    </style>



    <div class="box">

    <h1>
    HER İŞ ORMAN ÜRÜNLERİ STOK TAKİBİ
    </h1>


    Personel: {{user}}


    <form method="post">

    Barkod
    <input name="barkod">

    Ürün Adı
    <input name="isim">

    Mal Cinsi
    <input name="cins">

    Ebat
    <input name="ebat">


    Kalınlık
    <input name="kalinlik">


    Sınıf
    <input name="sinif">


    Yüzey

    <select name="yuzey">
    <option>HG</option>
    <option>MAT</option>
    </select>


    Renk
    <input name="renk">


    Adet
    <input name="adet" type="number">


    Depo

    <select name="depo">

    {% for d in depolar %}
    <option>{{d}}</option>
    {% endfor %}

    </select>


    <br>

    <button>KAYDET</button>

    </form>


    <hr>


    <table>

    <tr>
    <th>Barkod</th>
    <th>Ürün</th>
    <th>Cins</th>
    <th>Ebat</th>
    <th>Adet</th>
    <th>Depo</th>
    </tr>


    {% for r in rows %}

    <tr>

    <td>{{r[2]}}</td>
    <td>{{r[3]}}</td>
    <td>{{r[4]}}</td>
    <td>{{r[5]}}</td>
    <td>{{r[10]}}</td>
    <td>{{r[11]}}</td>

    </tr>

    {% endfor %}


    </table>


    </div>


    """,
    user=session["user"],
    rows=rows,
    depolar=DEPOLAR)





@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")





if __name__=="__main__":

    app.run(
    host="0.0.0.0",
    port=int(os.environ.get("PORT",10000))
    )
