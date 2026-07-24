from flask import Flask, render_template_string, request, send_file
import io
from reportlab.pdfgen import canvas
import barcode
from barcode.writer import ImageWriter

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>MDF Kesim + Barkod</title>
</head>
<body style="font-family: Arial; padding:20px;">

<h2>MDF Kesim Sistemi</h2>

<form method="POST">
    <label>Ürün Adı:</label><br>
    <input type="text" name="urun" required><br><br>

    <label>En (mm):</label><br>
    <input type="number" name="en" required><br><br>

    <label>Boy (mm):</label><br>
    <input type="number" name="boy" required><br><br>

    <label>Adet:</label><br>
    <input type="number" name="adet" required><br><br>

    <label>MDF Kalınlık (mm):</label><br>
    <input type="number" name="kalinlik" required><br><br>

    <button type="submit">Oluştur</button>
</form>

{% if barkod %}
    <h3>Sonuç:</h3>
    <p><b>Ürün:</b> {{urun}}</p>
    <p><b>Ölçü:</b> {{en}} x {{boy}} mm</p>
    <p><b>Adet:</b> {{adet}}</p>
    <p><b>Kalınlık:</b> {{kalinlik}} mm</p>

    <img src="/barkod" alt="barkod"><br><br>

    <a href="/pdf">PDF İndir</a>
{% endif %}

</body>
</html>
"""

data_store = {}

@app.route("/", methods=["GET", "POST"])
def index():
    global data_store

    if request.method == "POST":
        urun = request.form["urun"]
        en = request.form["en"]
        boy = request.form["boy"]
        adet = request.form["adet"]
        kalinlik = request.form["kalinlik"]

        barkod_data = f"{urun}-{en}x{boy}-{kalinlik}mm"

        data_store = {
            "urun": urun,
            "en": en,
            "boy": boy,
            "adet": adet,
            "kalinlik": kalinlik,
            "barkod": barkod_data
        }

        return render_template_string(HTML, barkod=True, **data_store)

    return render_template_string(HTML, barkod=False)


@app.route("/barkod")
def barkod():
    global data_store

    CODE128 = barcode.get_barcode_class('code128')
    rv = io.BytesIO()
    code = CODE128(data_store["barkod"], writer=ImageWriter())
    code.write(rv)
    rv.seek(0)

    return send_file(rv, mimetype='image/png')


@app.route("/pdf")
def pdf():
    global data_store

    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)

    p.drawString(100, 800, f"Ürün: {data_store['urun']}")
    p.drawString(100, 780, f"Ölçü: {data_store['en']} x {data_store['boy']} mm")
    p.drawString(100, 760, f"Adet: {data_store['adet']}")
    p.drawString(100, 740, f"Kalınlık: {data_store['kalinlik']} mm")

    p.drawString(100, 700, f"Barkod: {data_store['barkod']}")

    p.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="kesim.pdf", mimetype='application/pdf')


if __name__ == "__main__":
    app.run(debug=True)
