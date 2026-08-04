"""Ekspor PDF Daftar Data Tendik (Kelola Data Tendik) -- daftar
administratif sederhana, BUKAN laporan resmi eksternal seperti Laporan
Serdos, jadi tanpa blok pengesahan/tanda tangan."""
import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

WARNA_HEADER = colors.HexColor("#1e3a5f")


def render_pdf_daftar_tendik(daftar, *, kata_kunci=""):
    """Return bytes PDF. `daftar` queryset/list DataTendik -- fungsi ini
    murni tampilan, tidak melakukan query apa pun."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    judul_style = ParagraphStyle("judul", parent=styles["Heading1"], fontSize=13, alignment=TA_CENTER, spaceAfter=2)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER, spaceAfter=2)

    elements = [
        Paragraph("DAFTAR DATA TENDIK", judul_style),
        Paragraph("Universitas Ichsan Gorontalo", sub_style),
    ]
    if kata_kunci:
        elements.append(Paragraph(f'Kata kunci pencarian: "{kata_kunci}"', sub_style))
    elements.append(Spacer(1, 0.4 * cm))

    headers = ["No", "Nama", "NIP Yayasan", "Jabatan", "Unit Kerja", "Status Kepegawaian", "Status"]
    table_data = [headers]
    for idx, t in enumerate(daftar, start=1):
        table_data.append([
            str(idx), t.nama_lengkap, t.nip_yayasan or "-", t.jabatan or "-",
            t.unit_kerja_nama or "-", t.status_kepegawaian_nama or "-",
            "Aktif" if t.is_active else "Nonaktif",
        ])

    col_widths = [1 * cm, 4 * cm, 2.5 * cm, 2.8 * cm, 2.8 * cm, 3 * cm, 1.5 * cm]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), WARNA_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
