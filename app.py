from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import mm

@app.route("/label/<int:product_id>")
def label(product_id):

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    SELECT name, barcode, cins, ebat, mm, hg, yuzey, sinif, renk
    FROM products WHERE id=?
    """, (product_id,))

    p = c.fetchone()
    conn.close()

    if not p:
        return "ÜRÜN YOK"

    name, code, cins, ebat, mm_val, hg, yuzey, sinif, renk = p

    barcode_path = f"barcodes/{code}.png"

    pdf_file = f"etiket_{product_id}.pdf"

    # ETİKET BOYUTU (100x60 mm)
    c = canvas.Canvas(pdf_file, pagesize=(100*mm, 60*mm))

    # ÜRÜN ADI (BÜYÜK)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(10, 150, name)

    # ALT BİLGİLER
    c.setFont("Helvetica", 8)

    c.drawString(10, 130, f"Cins: {cins}")
    c.drawString(10, 115, f"Ebat: {ebat}")
    c.drawString(10, 100, f"MM: {mm_val}")
    c.drawString(10, 85, f"HG: {hg}")
    c.drawString(10, 70, f"Yüzey: {yuzey}")
    c.drawString(10, 55, f"Sınıf: {sinif}")
    c.drawString(10, 40, f"Renk: {renk}")

    # BARKOD
    if os.path.exists(barcode_path):
        c.drawImage(barcode_path, 200, 30, width=200, height=80)

    # KOD YAZISI
    c.setFont("Helvetica", 8)
    c.drawString(200, 15, code)

    c.save()

    return send_file(pdf_file, as_attachment=True)
