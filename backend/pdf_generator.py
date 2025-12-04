import asyncio
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from pdfrw import PdfReader, PdfWriter, PageMerge
from datetime import date
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pathlib import Path

pdfmetrics.registerFont(TTFont('Arial', 'Arial.ttf'))

current_dir = Path(__file__).resolve()
root_path = current_dir.parent
temp_path = root_path / "data" / "letter_temp.pdf"

async def gen_sl(cust_details: dict) -> str:
    overlay = "overlay.pdf"
    temp_pdf = PdfReader(temp_path)
    num_pages = len(temp_pdf.pages)
    out_path = f"letter_{cust_details['cust_name']}.pdf"
    date_issue = date.today()
    field_map = {
    0: [
        (f"Customer: {cust_details['cust_name']}", 10, 770),
        (f"Address: {cust_details['cust_add']}", 10, 750),
        (f"Date: {date_issue}", 10, 730),
        (f"Personal Loan", 200, 450),
        (f"{cust_details['coborrower']}", 200, 410),
        (f"\u20B9 {cust_details['amt']} ONLY", 200, 370),
        (f"{cust_details['tenure']} Months", 200, 330),
        (f"{cust_details['roi']} %", 200, 290),
        (f"\u20B9{cust_details['processing_charges']:,.2f}", 200, 250)
    ]}
    def create_overlay():
        c= canvas.Canvas(overlay, pagesize=A4)
        c.setFont("Arial", 11)
        for page_index in range(num_pages):

            if page_index in field_map:
                for text, x, y in field_map[page_index]:
                    c.drawString(x, y, text)

            c.showPage()

        c.save()
    
    await asyncio.to_thread(create_overlay)

    def merge():
        overlay_pdf = PdfReader(overlay)

        for pg in range(num_pages):
            temp_pg = temp_pdf.pages[pg]
            overlay_pg = overlay_pdf.pages[pg]
            merger = PageMerge(temp_pg)
            merger.add(overlay_pg).render()

        PdfWriter().write(out_path, temp_pdf)

    await asyncio.to_thread(merge)

    return out_path

#demo entry
#asyncio.run(gen_sl(cust_details = {'cust_name': 'Mr. Wilman', 'cust_add': 'Street 7, Dummy City, Earth','coborrower':'NIL', 'amt': 4500000, 'tenure': 132, 'roi': 10.05, 'processing_charges':45500}))