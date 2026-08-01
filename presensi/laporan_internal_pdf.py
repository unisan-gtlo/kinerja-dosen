"""Ekspor PDF Laporan Presensi Internal -- kertas F4 landscape (beda dari
laporan_serdos_pdf.py yang pakai A3, karena di sini cuma 1 kolom per
tanggal berisi jam Masuk/Pulang bertumpuk, bukan gambar paraf -- jauh
lebih hemat lebar)."""
import io

from django.contrib.staticfiles import finders
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .laporan_internal import data_laporan_internal
from .laporan_serdos import jenis_tanggal_bulan
from .models import NAMA_BULAN

F4 = (21.5 * cm, 33 * cm)
WARNA_HEADER = colors.HexColor("#1e3a5f")
WARNA_ARSIR = colors.HexColor("#d9d9d9")


def _label_filter(kategori, fakultas, prodi):
    label_kategori = {"dosen": "Dosen (termasuk Pejabat Struktural)", "tendik": "Tendik"}.get(kategori, "")
    bagian = []
    if label_kategori:
        bagian.append(f"Kategori: {label_kategori}")
    if fakultas:
        bagian.append(f"Fakultas: {fakultas}")
    if prodi:
        bagian.append(f"Prodi: {prodi}")
    return " · ".join(bagian)


def render_pdf_laporan_internal(user_qs, bulan, tahun, kategori="", fakultas="", prodi=""):
    """Return bytes PDF."""
    daftar = data_laporan_internal(user_qs, bulan, tahun)
    jenis_list = jenis_tanggal_bulan(bulan, tahun)
    jumlah_hari = len(jenis_list)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(F4),
        leftMargin=1 * cm, rightMargin=1 * cm, topMargin=1 * cm, bottomMargin=1 * cm,
    )

    styles = getSampleStyleSheet()
    judul_style = ParagraphStyle("judul", parent=styles["Heading1"], fontSize=12, alignment=TA_CENTER, spaceAfter=2)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER, spaceAfter=1)
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=6, alignment=TA_LEFT, leading=7)
    jam_style = ParagraphStyle("jam", parent=styles["Normal"], fontSize=6, alignment=TA_CENTER, leading=7)
    ket_style = ParagraphStyle("ket", parent=styles["Normal"], fontSize=7)

    elements = []
    logo_path = finders.find("img/kampus.png")
    logo = RLImage(logo_path, width=1.4 * cm, height=1.4 * cm) if logo_path else ""
    info_header = [
        Paragraph("LAPORAN PRESENSI BULANAN", judul_style),
        Paragraph("Universitas Ichsan Gorontalo", sub_style),
        Paragraph(f"{NAMA_BULAN[bulan - 1]} {tahun}", sub_style),
    ]
    label_filter = _label_filter(kategori, fakultas, prodi)
    if label_filter:
        info_header.append(Paragraph(label_filter, sub_style))
    header_table = Table([[logo, info_header]], colWidths=[1.8 * cm, None])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.3 * cm))

    lebar_no, lebar_nama, lebar_prodi = 0.7 * cm, 3.6 * cm, 2.3 * cm
    lebar_usable = (33 * cm - 2 * cm) - (lebar_no + lebar_nama + lebar_prodi)
    lebar_tanggal = max(lebar_usable / jumlah_hari, 0.5 * cm) if jumlah_hari else 0.5 * cm
    col_widths = [lebar_no, lebar_nama, lebar_prodi] + [lebar_tanggal] * jumlah_hari

    header_row = ["No", "Nama", "Program\nStudi"] + [str(tanggal.day) for tanggal, _jenis in jenis_list]
    table_data = [header_row]

    for idx, baris in enumerate(daftar, start=1):
        nama = Paragraph(baris["user"].nama_resmi, cell_style)
        sel_tanggal = [
            Paragraph(f"{hari.jam_masuk}<br/>{hari.jam_pulang}", jam_style) if (hari.jam_masuk or hari.jam_pulang) else ""
            for hari in baris["hari_grid"]
        ]
        table_data.append([str(idx), nama, baris["nama_prodi"]] + sel_tanggal)

    shading_commands = []
    for i, (_tanggal, jenis) in enumerate(jenis_list):
        if jenis != "kerja" and daftar:
            col_idx = 3 + i
            shading_commands.append(("BACKGROUND", (col_idx, 1), (col_idx, len(daftar)), WARNA_ARSIR))

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), WARNA_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 6.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 1), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
        *shading_commands,
    ]))
    elements.append(table)

    elements.append(Spacer(1, 0.25 * cm))
    elements.append(Paragraph(
        '<font backColor="#d9d9d9">&nbsp;&nbsp;&nbsp;&nbsp;</font>&nbsp;: Hari Minggu/Libur -- jam kosong berarti tidak ada presensi tercatat.',
        ket_style,
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
