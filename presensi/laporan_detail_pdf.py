"""Ekspor PDF Detail Presensi Bulanan -- tabel sederhana (bukan grid
lebar seperti laporan lain), A4 portrait cukup karena cuma 1 orang."""
import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .laporan_detail import detail_presensi_bulanan
from .models import NAMA_BULAN

WARNA_HEADER = colors.HexColor("#1e3a5f")
WARNA_ARSIR = colors.HexColor("#d9d9d9")


def render_pdf_detail_presensi(
    user, bulan, tahun, *, kota="Gorontalo", tanggal_cetak=None,
    jabatan_penandatangan="", nama_penandatangan="", id_penandatangan="",
):
    """Return bytes PDF. Blok tanda tangan bersifat OPSIONAL & manual --
    beda dari Laporan Serdos yang otomatis dari Pejabat Struktural SIMDA
    (get_pejabat_aktif), karena penandatangan Detail Presensi bisa siapa
    saja (atasan langsung, HR, dst), bukan cuma Rektor. id_penandatangan
    diisi bebas apa adanya (mis. "NIP. 199001012020121001" atau
    "NIDN. 0910097601") -- BUKAN dipisah field NIP/NIDN dengan prefiks
    otomatis seperti Serdos, karena jenis id-nya bisa beda tiap orang."""
    tanggal_cetak = tanggal_cetak or timezone.localdate()
    data = detail_presensi_bulanan(user, bulan, tahun)
    rekap = data["rekap"]

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=1.5 * cm, rightMargin=1.5 * cm, topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    judul_style = ParagraphStyle("judul", parent=styles["Heading1"], fontSize=13, alignment=TA_CENTER, spaceAfter=4)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER, spaceAfter=2)
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, alignment=TA_LEFT, leading=10)
    ringkasan_style = ParagraphStyle("ringkasan", parent=styles["Normal"], fontSize=10, spaceAfter=3)
    ttd_style = ParagraphStyle("ttd", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER)

    elements = [
        Paragraph("DETAIL PRESENSI BULANAN", judul_style),
        Paragraph(
            f"{user.get_full_name() or user.username}" + (f" ({user.nidn})" if user.nidn else ""), sub_style,
        ),
        Paragraph(f"{NAMA_BULAN[bulan - 1]} {tahun}", sub_style),
        Spacer(1, 0.4 * cm),
    ]

    headers = ["Tanggal", "Hari", "Status", "Masuk", "Pulang", "Keterangan", "Durasi"]
    table_data = [headers]
    shading_rows = []
    for idx, baris in enumerate(data["baris"], start=1):
        table_data.append([
            baris.tanggal.strftime("%d-%m-%Y"), baris.nama_hari, baris.status,
            baris.waktu_masuk, baris.waktu_pulang, Paragraph(baris.keterangan, cell_style), baris.durasi_kerja,
        ])
        if baris.jenis != "kerja":
            shading_rows.append(idx)

    col_widths = [2.3 * cm, 1.8 * cm, 2 * cm, 1.6 * cm, 1.6 * cm, 6 * cm, 1.7 * cm]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), WARNA_HEADER),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (4, -1), "CENTER"),
        ("ALIGN", (6, 0), (6, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for row_idx in shading_rows:
        style_cmds.append(("BACKGROUND", (0, row_idx), (-1, row_idx), WARNA_ARSIR))
    table.setStyle(TableStyle(style_cmds))
    elements.append(table)

    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(f"<b>Hari Hadir:</b> {rekap['hari_hadir']} hari", ringkasan_style))
    elements.append(Paragraph(f"<b>Total Jam Kerja:</b> {rekap['total_jam_kerja']}", ringkasan_style))
    if rekap["target"]:
        elements.append(Paragraph(
            f"<b>Target ({rekap['kelompok'].nama}):</b> {rekap['target'].target_jam_kerja} jam "
            f"/ {rekap['target'].target_hari_kerja} hari", ringkasan_style,
        ))
        elements.append(Paragraph(f"<b>Selisih:</b> {rekap['selisih_jam_kerja']}", ringkasan_style))

    if jabatan_penandatangan or nama_penandatangan or id_penandatangan:
        blok_kanan = [
            Paragraph(f"{kota}, {tanggal_cetak.strftime('%d %B %Y').upper()}", ttd_style),
        ]
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
