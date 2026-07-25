from flask import Flask, request, redirect, url_for, session, render_template_string, send_file
import barcode
from barcode.writer import ImageWriter
import os

app = Flask(__name__)
app.secret_key = "secret123"

USERNAME = "admin"
PASSWORD = "1234"

HTML_LOGIN = """
<h2>Giriş Yap</h2>
<form method="post">
  Kullanıcı: <input name="username"><br>
  Şifre: <input name="password" type="password"><br>
  <button type="submit">Giriş</button>
</form>
"""

HTML_PANEL = """
<h2>Barkod Oluştur</h2>
<form method="post" action="/generate">
  Barkod: <input name="code"><br>
  <button type="submit">Oluştur</button>
</form>
<a href="/logout">Çıkış</a>
"""

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == USERNAME and request.form["password"] == PASSWORD:
            session["user"] = True
            return redirect("/panel")
    return render_template_string(HTML_LOGIN)

@app.route("/panel")
def panel():
    if not session.get("user"):
        return redirect("/")
    return render_template_string(HTML_PANEL)

@app.route("/generate", methods=["POST"])
def generate():
    if not session.get("user"):
        return redirect("/")
    
    code = request.form["code"]
    filename = f"{code}.png"
    
    ean = barcode.get('code128', code, writer=ImageWriter())
    ean.save(code)

    return send_file(filename, as_attachment=True)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
