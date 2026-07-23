from flask import Flask, request, render_template_string, send_file
import barcode
from barcode.writer import ImageWriter
import os

app = Flask(__name__)

# Depolar
depots = [
    "1. MDF SATIŞ DEPOSU",
    "2. LAMİNANT DEPOSU",
    "3. KAPI DEPOSU",
    "4. HGLOSS DEPOSU (MORAYIN YANI)",
    "5. SÜTÇÜNÜN YANI",
    "6. HELVACININ ORASI",
    "7. RÖTBALANSÇI YANI",
    "8. KESİMHANE DEPOSU"
]

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Stok Yönetim</title>

<script src="https://unpkg.com/html5-qrcode"></script>

<style>
body {
    font-family: Arial;
    background: #0f172a;
    color: white;
    text-align: center;
}
.card {
    background: #1e293b;
    padding: 20px;
    margin: 20px auto;
    width: 400px;
    border-radius: 15px;
}
input, select {
    width: 90%;
    padding: 10px;
    margin: 5px;
    border-radius: 10px;
    border: none;
}
button {
    background: #22c55e;
    border: none;
    padding: 10px;
    width: 95%;
    border-radius: 10px;
    color: white;
    font-size: 16px;
}
#reader {
    width: 300px;
    margin: auto;
}
</style>

</head>
<body>

<h1>📦 Stok Yönetim Paneli</h1>

<div class="card">
<form method="POST" action="/generate">

<input type="text" name="product" placeholder="Ürün Adı" required>

<select name="type">
<option value="HG">HG</option>
<option value="MAT">MAT</option>
</select>

<select name="depot">
{% for d in depots %}
<option value="{{d}}">{{d}}</option>
{% endfor %}
</select>

<input type="number" name="quantity" placeholder="Miktar" required>

<input type="text" id="barcode" name="barcode" placeholder="Barkod">

<button type="submit">BARKOD OLUŞTUR</button>

</form>
</div>

<div class="card">
<h3>📷 Barkod Oku</h3>
<div id="reader"></div>
</div>

<script>
const html5QrCode = new Html5Qrcode("reader");

html5QrCode.start(
    { facingMode: "environment" },
    { fps: 10 },
    (decodedText) => {
        document.getElementById("barcode").value = decodedText;
    }
);
</script>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML, depots=depots)

@app.route("/generate", methods=["POST"])
def generate():
    product = request.form["product"]
    type_ = request.form["type"]
    depot = request.form["depot"]
    quantity = request.form["quantity"]
    code = request.form["barcode"]

    if not code:
        code = product[:3].upper() + type_ + "001"

    filename = "barcode.png"

    CODE128 = barcode.get_barcode_class('code128')
    my_code = CODE128(code, writer=ImageWriter())
    my_code.save("static/barcode")

    return f"""
    <h2>Barkod Oluşturuldu</h2>
    <p>{product} - {type_}</p>
    <p>Depo: {depot}</p>
    <p>Miktar: {quantity}</p>
    <img src="/static/barcode.png"><br><br>

    <button onclick="window.print()">🖨️ Yazdır</button>
    <br><br>
    <a href="/">Geri</a>
    """

if __name__ == "__main__":
    os.makedirs("static", exist_ok=True)
    app.run(debug=True)
