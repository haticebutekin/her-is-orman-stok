from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Kamera QR Okuyucu</title>
        <script src="https://unpkg.com/html5-qrcode"></script>
    </head>
    <body style="text-align:center; font-family:Arial;">

        <h2>QR Kod Okuyucu</h2>

        <div id="reader" style="width:300px; margin:auto;"></div>

        <h3 id="result">Sonuç: Yok</h3>

        <script>
            function onScanSuccess(decodedText) {
                document.getElementById("result").innerText = "Sonuç: " + decodedText;
            }

            function onScanError(error) {
                console.warn(error);
            }

            let html5QrcodeScanner = new Html5QrcodeScanner(
                "reader",
                { fps: 10, qrbox: 250 }
            );

            html5QrcodeScanner.render(onScanSuccess, onScanError);
        </script>

    </body>
    </html>
    """

# ❗ app.run YOK ❗
