from flask import Flask, request, render_template_string
import sqlite3

app = Flask(__name__)

def get_db():
    return sqlite3.connect("stok.db")

# VERİTABANI OLUŞTUR
def init_db():
    con = get_db()
    con.execute("""
    CREATE TABLE IF NOT EXISTS urun (
        barkod TEXT PRIMARY KEY,
        ad TEXT,
        adet INTEGER
    )
    """)

    con.execute("""
    CREATE TABLE IF NOT EXISTS hareket (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        barkod TEXT,
        ad TEXT,
        tip TEXT,
        adet INTEGER,
        kullanici TEXT,
        tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    con.commit()
    con.close()

init_db()

# ANA SAYFA
@app.route("/")
def index():
    return render_template_string("""
    <h2>Stok Yönetimi</h2>

    <form method="post" action="/islem">
        <input type="text" name="barkod" placeholder="Barkod" required><br><br>
        <input type="text" name="ad" placeholder="Ürün Adı"><br><br>
        <input type="number" name="adet" placeholder="Adet" required><br><br>

        <!-- SENİN EKLEMEK İSTEDİĞİN -->
        <input type="text" name="kullanici" placeholder="İşlemi yapan kişi" required><br><br>

        <select name="tip">
            <option value="GIRIS">Giriş</option>
            <option value="CIKIS">Çıkış</option>
        </select><br><br>

        <button type="submit">Kaydet</button>
    </form>
    """)

# İŞLEM
@app.route("/islem", methods=["POST"])
def islem():
    barkod = request.form["barkod"]
    ad = request.form.get("ad", "")
    adet = int(request.form["adet"])
    tip = request.form["tip"]

    # SENİN EKLEMEK İSTEDİĞİN
    kullanici = request.form.get("kullanici", "Bilinmiyor")

    con = get_db()

    # Ürün var mı kontrol
    urun = con.execute("SELECT * FROM urun WHERE barkod=?", (barkod,)).fetchone()

    if tip == "GIRIS":
        if urun:
            con.execute("UPDATE urun SET adet = adet + ? WHERE barkod=?", (adet, barkod))
        else:
            con.execute("INSERT INTO urun (barkod, ad, adet) VALUES (?, ?, ?)", (barkod, ad, adet))

        # HAREKET KAYDI (SENİN SORUN)
        con.execute("""
        INSERT INTO hareket (barkod, ad, tip, adet, kullanici)
        VALUES (?, ?, ?, ?, ?)
        """, (barkod, ad, "GIRIS", adet, kullanici))

    elif tip == "CIKIS":

        # 🔴 STOK KONTROL (SENİN SORUN)
        stok = con.execute("SELECT adet FROM urun WHERE barkod=?", (barkod,)).fetchone()

        if not stok:
            return "❌ Ürün bulunamadı!"

        if stok[0] < adet:
            return f"❌ Yetersiz stok! Mevcut: {stok[0]}"

        # 🔴 GÜVENLİ ÇIKIŞ (SENİN SORUN)
        con.execute("""
        UPDATE urun SET adet = adet - ?
        WHERE barkod=? AND adet >= ?
        """, (adet, barkod, adet))

        if con.total_changes == 0:
            return "❌ İşlem başarısız! Stok yetersiz olabilir."

        # HAREKET KAYDI
        con.execute("""
        INSERT INTO hareket (barkod, ad, tip, adet, kullanici)
        VALUES (?, ?, ?, ?, ?)
        """, (barkod, ad, "CIKIS", adet, kullanici))

    con.commit()
    con.close()

    return "✅ İşlem başarılı!"
    

if __name__ == "__main__":
    app.run(debug=True)
