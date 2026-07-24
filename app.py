from flask import Flask, render_template_string, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime
import uuid, os

# Barkod + Kamera
import cv2
from pyzbar.pyzbar import decode

# Barkod üretme
import barcode
from barcode.writer import ImageWriter

# PDF
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
db = SQLAlchemy(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"

# 🔐 KULLANICILAR
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    role = db.Column(db.String(20))

# 📦 ÜRÜN
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    cins = db.Column(db.String(50))
    ebat = db.Column(db.String(50))
    mm = db.Column(db.String(10))
    sinif = db.Column(db.String(20))
    yuzey = db.Column(db.String(20))
    renk = db.Column(db.String(50))
    barcode = db.Column(db.String(100), unique=True)

# 📊 STOK
class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer)
    depo = db.Column(db.String(100))
    miktar = db.Column(db.Integer)

# 🧾 LOG
class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(50))
    action = db.Column(db.String(200))
    date = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 📍 DEPOLAR
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

# 👤 İLK KULLANICILAR
@app.before_request
def create_users():
    if not User.query.first():
        users = [
            ("ramazan","depo"),
            ("orhan","depo"),
            ("behiç","depo"),
            ("hatice","yonetici"),
            ("ahmet","yonetici"),
            ("berke","muhasebe"),
            ("irem","muhasebe")
        ]
        for u,r in users:
            db.session.add(User(username=u, role=r))
        db.session.commit()

# 🔐 LOGIN
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u = User.query.filter_by(username=request.form["username"]).first()
        if u:
            login_user(u)
            return redirect("/panel")
    return render_template_string("""
    <h2>Giriş</h2>
    <form method="post">
    Kullanıcı: <input name="username">
    <button>Giriş</button>
    </form>
    """)

# 🏠 PANEL
@app.route("/panel")
@login_required
def panel():
    products = Product.query.all()
    stocks = Stock.query.all()
    logs = Log.query.order_by(Log.date.desc()).limit(10)

    return render_template_string("""
    <h2>Hoşgeldin {{user.username}} ({{user.role}})</h2>

    <a href="/urun">Ürün Ekle</a> |
    <a href="/barkod_oku">Barkod Oku</a> |
    <a href="/logout">Çıkış</a>

    <h3>Ürünler</h3>
    {% for p in products %}
        {{p.name}} - {{p.barcode}} 
        <a href="/etiket/{{p.id}}">Etiket</a><br>
    {% endfor %}

    <h3>Stok</h3>
    {% for s in stocks %}
        Ürün {{s.product_id}} | {{s.depo}} | {{s.miktar}}
        <a href="/dus/{{s.id}}">Düş</a><br>
    {% endfor %}

    <h3>Log</h3>
    {% for l in logs %}
        {{l.user}} - {{l.action}}<br>
    {% endfor %}
    """, user=current_user, products=products, stocks=stocks, logs=logs)

# 📦 ÜRÜN EKLE
@app.route("/urun", methods=["GET","POST"])
@login_required
def urun():
    if current_user.role=="depo":
        return "Yetki yok"

    if request.method=="POST":
        code = str(uuid.uuid4())[:12]

        p = Product(
            name=request.form["name"],
            cins=request.form["cins"],
            ebat=request.form["ebat"],
            mm=request.form["mm"],
            sinif=request.form["sinif"],
            yuzey=request.form["yuzey"],
            renk=request.form["renk"],
            barcode=code
        )
        db.session.add(p)
        db.session.commit()

        # barkod resmi
        EAN = barcode.get_barcode_class('code128')
        ean = EAN(code, writer=ImageWriter())
        ean.save(f"static/{code}")

        db.session.add(Log(user=current_user.username, action=f"Ürün eklendi {code}"))
        db.session.commit()

        return redirect("/panel")

    return render_template_string("""
    <h2>Ürün Ekle</h2>
    <form method="post">
    Ad: <input name="name"><br>
    Cins: <input name="cins"><br>
    Ebat: <input name="ebat"><br>
    mm: <input name="mm"><br>
    Sınıf: <input name="sinif"><br>
    Yüzey: <input name="yuzey"><br>
    Renk: <input name="renk"><br>
    <button>Kaydet</button>
    </form>
    """)

# 📉 STOK DÜŞ
@app.route("/dus/<int:id>")
@login_required
def dus(id):
    s = Stock.query.get(id)
    if s.miktar>0:
        s.miktar -=1

    db.session.add(Log(user=current_user.username, action="stok düşüldü"))
    db.session.commit()
    return redirect("/panel")

# 📷 BARKOD OKUMA
@app.route("/barkod_oku")
@login_required
def barkod_oku():
    return "Sunucuda kamera çalışmaz (telefon versiyonunu)"
    while True:
        _, frame = cap.read()
        for b in decode(frame):
            code = b.data.decode("utf-8")

            product = Product.query.filter_by(barcode=code).first()
            if product:
                db.session.add(Log(user=current_user.username, action=f"Barkod okutuldu {code}"))
                db.session.commit()

                cap.release()
                cv2.destroyAllWindows()
                return f"Bulundu: {product.name}"

        cv2.imshow("OKU", frame)
        if cv2.waitKey(1)==27:
            break

    cap.release()
    return "iptal"

# 🧾 ETİKET PDF
@app.route("/etiket/<int:id>")
@login_required
def etiket(id):
    p = Product.query.get(id)
    file = f"{p.barcode}.pdf"

    c = canvas.Canvas(file)
    c.drawString(100,750,p.name)
    c.drawString(100,730,p.barcode)
    c.drawImage(f"static/{p.barcode}.png",100,600,200,100)
    c.save()

    return send_file(file)

# 🚪 ÇIKIŞ
@app.route("/logout")
def logout():
    logout_user()
    return redirect("/")

# 🚀 ÇALIŞTIR
if __name__ == "__main__":
    if not os.path.exists("static"):
        os.mkdir("static")
    db.create_all()
    app.run(debug=True)
