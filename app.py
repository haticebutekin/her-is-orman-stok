from flask import Flask, request, jsonify, render_template_string
import time

app = Flask(__name__)

urunler = []
hareket = []

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>DEPO PRO</title>

<script src="https://cdn.jsdelivr.net/npm/qrcode/build/qrcode.min.js"></script>

<style>
body { font-family: Arial; padding:20px; }
input, select { margin:5px; padding:6px; }
button { padding:6px 12px; }
.kart { border:1px solid #ccc; padding:10px; margin-top:10px; }
</style>
</head>

<body>

<h2>🔐 Giriş</h2>
<select id="rol">
<option>Yönetici</option>
<option>Depocu</option>
</select>
<input id="kullanici" placeholder="İsim">
<button onclick="giris()">GİRİŞ</button>

<hr>

<div id="panel" style="display:none;">

<h2>📦 Ürün Ekle</h2>

<input id="ad" placeholder="Mal adı">
<input id="ebat" placeholder="Ebat mm">
<input id="adet" type="number" placeholder="Adet">

<select id="depo">
<option>MDF SATIŞ DEPOSU</option>
<option>LAMİNANT DEPOSU</option>
<option>KAPI DEPOSU</option>
<option>HGLOSS DEPOSU</option>
<option>SÜTÇÜ YANI</option>
<option>HELVACI YANI</option>
<option>RÖTBALANSÇI YANI</option>
<option>KESİMHANE</option>
</select>

<button onclick="urunEkle()">EKLE</button>

<hr>

<h2>🚚 Çıkış</h2>
<input id="barkod" placeholder="Barkod">
<input id="cikisAdet" type="number" placeholder="Adet">
<button onclick="cikis()">ÇIKIŞ</button>

<hr>

<h2>📋 Ürünler</h2>
<div id="liste"></div>

<hr>

<h2>📊 Hareket</h2>
<div id="log"></div>

</div>

<script>

let rol = ""
let kullanici = ""

function giris(){
rol = document.getElementById("rol").value
kullanici = document.getElementById("kullanici").value

if(!kullanici) return alert("isim gir")

document.getElementById("panel").style.display="block"
listele()
}

function urunEkle(){

if(rol !== "Yönetici") return alert("yetki yok")

fetch("/ekle", {
method:"POST",
headers:{"Content-Type":"application/json"},
body: JSON.stringify({
ad: ad.value,
ebat: ebat.value,
adet: adet.value,
depo: depo.value,
kullanici: kullanici
})
}).then(r=>r.json()).then(()=>{
listele()
})
}

function listele(){
fetch("/urunler")
.then(r=>r.json())
.then(data=>{
let alan = document.getElementById("liste")
alan.innerHTML=""

data.forEach(u=>{
let div = document.createElement("div")
div.className="kart"

div.innerHTML = `
<b>${u.ad}</b><br>
Ebat: ${u.ebat} mm<br>
Adet: ${u.adet}<br>
Depo: ${u.depo}<br>
Barkod: ${u.barkod}<br>
<canvas id="qr-${u.barkod}"></canvas>
`

alan.appendChild(div)

QRCode.toCanvas(document.getElementById("qr-"+u.barkod), u.barkod)

})
})

fetch("/hareket")
.then(r=>r.json())
.then(data=>{
let log = document.getElementById("log")
log.innerHTML=""

data.slice().reverse().forEach(h=>{
log.innerHTML += `${h.saat} | ${h.kisi} | ${h.islem} | ${h.urun} (${h.adet})<br>`
})
})
}

function cikis(){

if(rol !== "Depocu") return alert("yetki yok")

fetch("/cikis", {
method:"POST",
headers:{"Content-Type":"application/json"},
body: JSON.stringify({
barkod: barkod.value,
adet: parseInt(cikisAdet.value),
kullanici: kullanici
})
}).then(r=>r.json()).then(res=>{
alert(res.mesaj || res.hata)
listele()
})
}

</script>

</body>
</html>
"""

def barkod():
    return "B" + str(int(time.time()*1000))


@app.route("/")
def home():
    return render_template_string(HTML)


@app.route("/ekle", methods=["POST"])
def ekle():
    data = request.json

    u = {
        "ad": data["ad"],
        "ebat": data["ebat"],
        "adet": int(data["adet"]),
        "depo": data["depo"],
        "barkod": barkod()
    }

    urunler.append(u)

    hareket.append({
        "kisi": data["kullanici"],
        "islem": "Ürün eklendi",
        "urun": u["ad"],
        "adet": u["adet"],
        "saat": time.strftime("%H:%M:%S")
    })

    return jsonify({"ok":True})


@app.route("/urunler")
def urunler_get():
    return jsonify(urunler)


@app.route("/cikis", methods=["POST"])
def cikis():
    data = request.json

    for u in urunler:
        if u["barkod"] == data["barkod"]:

            if u["adet"] < data["adet"]:
                return {"hata":"stok yok"}

            u["adet"] -= data["adet"]

            hareket.append({
                "kisi": data["kullanici"],
                "islem": "Çıkış",
                "urun": u["ad"],
                "adet": data["adet"],
                "saat": time.strftime("%H:%M:%S")
            })

            return {"mesaj":"çıkış yapıldı"}

    return {"hata":"ürün yok"}


@app.route("/hareket")
def hareket_get():
    return jsonify(hareket)


if __name__ == "__main__":
    app.run(debug=True)
