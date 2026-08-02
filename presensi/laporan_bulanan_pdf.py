"""Ekspor PDF Laporan Bulanan Jam Kerja -- BARU (sebelumnya cuma ada
Excel). A4 portrait cukup karena cuma 8 kolom ringkas (beda dari Laporan
Presensi Internal yang butuh grid lebar ±31 kolom tanggal)."""
import io

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .laporan_internal_pdf import _label_filter
from .models import NAMA_BULAN

WARNA_HEADER = colors.HexColor("#1e3a5f")


def render_pdf_laporan_bulanan(
    daftar, bulan, tahun, *, kategori="", fakultas="", prodi="",
    kota="Gorontalo", tanggal_cetak=None, jabatan_penandatangan="", nama_penandatangan="", id_penandatangan="",
):
    """Return bytes PDF. `daftar` sudah hasil
    rekap.laporan_bulanan_jam_kerja() -- fungsi ini murni tampilan."""
    tanggal_cetak = tanggal_cetak or timezone.localdate()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    judul_style = ParagraphStyle("judul", parent=styles["Heading1"], fontSize=13, alignment=TA_CENTER, spaceAfter=2)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER, spaceAfter=2)
    ttd_style = ParagraphStyle("ttd", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER)

    elements = [
        Paragraph("LAPORAN BULANAN JAM KERJA", judul_style),
        Paragraph("Universitas Ichsan Gorontalo", sub_style),
        Paragraph(f"{NAMA_BULAN[bulan - 1]} {tahun}", sub_style),
    ]
    label_filter = _label_filter(kategori, fakultas, prodi)
    if label_filter:
        elements.append(Paragraph(label_filter, sub_style))
    elements.append(Spacer(1, 0.4 * cm))

    headers = ["No", "Nama", "Role", "Kelompok", "Hari Hadir", "Total Jam", "Target", "Selisih"]
    table_data = [headers]
    for idx, item in enumerate(daftar, start=1):
        target = item["target"]
        table_data.append([
            str(idx), item["user"].nama_resmi, item["user"].get_role_display_id(),
            item["kelompok"].nama if item["kelompok"] else "-",
            str(item["hari_hadir"]), item["total_jam_kerja"],
            f"{target.target_jam_kerja} jam" if target else "-",
            item["selisih_jam_kerja"] or "-",
        ])

    col_widths = [1 * cm, 4.5 * cm, 2.3 * cm, 2.3 * cm, 2 * cm, 2.3 * cm, 2 * cm, 2 * cm]
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

    if jabatan_penandatangan or nama_penandatangan or id_penandatangan:
        blok_kanan = [Paragraph(f"{kota}, {tanggal_cetak.strftime('%d %B %Y').upper()}", ttd_style)]
        if jabatan_penandatangan:
            blok_kanan.append(Paragraph(f"{jabatan_penandatangan.upper()},", ttd_style))
        blok_kanan.append(Spacer(1, 1.5 * cm))
        blok_kanan.append(Paragraph(f"<u>{nama_penandatangan or '.........................'}</u>", ttd_style))
        if id_penandatangan:
            blok_kanan.append(Paragraph(id_penandatangan, ttd_style))
        elements.append(Spacer(1, 0.8 * cm))
        elements.append(Table([["", blok_kanan]], colWidths=[None, 7 * cm]))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
