"""Ekspor PDF Daftar Data Tendik (Kelola Data Tendik) -- daftar
administratif sederhana, BUKAN laporan resmi eksternal seperti Laporan
Serdos, jadi tanpa blok pengesahan/tanda tangan."""
import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

WARNA_HEADER = colors.HexColor("#1e3a5f")


def render_pdf_daftar_tendik(daftar, *, kata_kunci=""):
    """Return bytes PDF. `daftar` queryset/list DataTendik -- fungsi ini
    murni tampilan, tidak melakukan query apa pun.

    Landscape (bukan portrait) + sel dibungkus Paragraph (bukan string
    polos) -- teks panjang (nama, unit kerja, dst) otomatis pindah baris
    mengikuti lebar kolom alih-alih menimpa/tumpang tindih dengan sel
    sebelah, yang terjadi kalau reportlab Table diberi string polos
    (tidak wrap sama sekali, cuma dipotong scara visual)."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    judul_style = ParagraphStyle("judul", parent=styles["Heading1"], fontSize=13, alignment=TA_CENTER, spaceAfter=2)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER, spaceAfter=2)
    sel_style = ParagraphStyle("sel", parent=styles["Normal"], fontSize=8, leading=10, alignment=TA_LEFT)
    sel_tengah_style = ParagraphStyle("sel_tengah", parent=sel_style, alignment=TA_CENTER)

    elements = [
        Paragraph("DAFTAR DATA TENDIK", judul_style),
        Paragraph("Universitas Ichsan Gorontalo", sub_style),
    ]
    if kata_kunci:
        elements.append(Paragraph(f'Kata kunci pencarian: "{kata_kunci}"', sub_style))
    elements.append(Spacer(1, 0.4 * cm))

    headers = ["No", "Nama", "NITK", "NIP Yayasan", "Unit Kerja", "Status Kepegawaian", "Pendidikan Terakhir", "Status"]
    table_data = [headers]
    for idx, t in enumerate(daftar, start=1):
        table_data.append([
            Paragraph(str(idx), sel_tengah_style),
            Paragraph(t.nama_lengkap, sel_style),
            Paragraph(t.nip or "-", sel_tengah_style),
            Paragraph(t.nip_yayasan or "-", sel_tengah_style),
            Paragraph(t.unit_kerja_nama or "-", sel_style),
            Paragraph(t.status_kepegawaian_nama or "-", sel_tengah_style),
            Paragraph(t.get_pendidikan_terakhir_display() if t.pendidikan_terakhir else "-", sel_tengah_style),
            Paragraph("Aktif" if t.is_active else "Nonaktif", sel_tengah_style),
        ])

    col_widths = [1 * cm, 4.5 * cm, 2.8 * cm, 2.8 * cm, 4.5 * cm, 3.5 * cm, 3.5 * cm, 2 * cm]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), WARNA_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
