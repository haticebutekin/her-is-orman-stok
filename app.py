from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "<h1>Ana Sayfa</h1><a href='/depocu'>Depocuya git</a>"

@app.route("/depocu")
def depocu():
    return "<h1>Depocu Sayfası 🔥</h1><a href='/'>Geri</a>"

if __name__ == "__main__":
    app.run(debug=True)
