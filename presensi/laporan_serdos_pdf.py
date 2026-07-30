"""Ekspor PDF Laporan Daftar Hadir Dosen Serdos (LLDIKTI) -- replikasi
format resmi (contoh fisik dari bagian kepegawaian): header logo+judul+
yayasan/PTS/bulan, tabel No/Nama-NIDN/Gol-Jabatan/tanggal 1-31/Total
Hadir dengan paraf ditempel, baris "TUGAS BELAJAR / BIAYA PEMERINTAH"
merentang, legenda hari libur, dan blok tanda tangan.

Ukuran arsir kolom non-kerja (Minggu/hari libur) SENGAJA dibuat warna
abu solid, bukan pola arsir diagonal seperti contoh fisik -- reportlab
Table tidak punya hatch-fill bawaan untuk sel, dan menggambar pola
custom per sel butuh flowable canvas sendiri yang jauh lebih rumit
untuk hasil yang secara fungsi sama (menandai hari non-kerja)."""
import io

from django.contrib.staticfiles import finders
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .laporan_serdos import data_laporan_serdos, jenis_tanggal_bulan
from .models import NAMA_BULAN, HariLibur

NAMA_YAYASAN = "IPTEK ICHSAN GORONTALO"
NAMA_PTS = "UNIVERSITAS ICHSAN GORONTALO"
NAMA_LLDIKTI = "LEMBAGA LAYANAN PENDIDIKAN TINGGI WIL. XVI"

WARNA_HEADER = colors.HexColor("#1e3a5f")
WARNA_ARSIR = colors.HexColor("#d9d9d9")

LEBAR_PARAF = 0.9 * cm
TINGGI_PARAF = 0.6 * cm


def _gambar_aman(field_file, lebar, tinggi):
    """RLImage dari FieldFile Django, atau None kalau kosong/rusak/file
    fisiknya hilang -- jangan sampai satu file bermasalah bikin PDF
    seluruh laporan gagal dibuat."""
    if not field_file:
        return None
    try:
        return RLImage(field_file.path, width=lebar, height=tinggi)
    except (FileNotFoundError, OSError, ValueError):
        return None


def render_pdf_laporan_serdos(
    bulan, tahun, kota, tanggal_cetak,
    jabatan_penandatangan="Rektor", nama_penandatangan="", nip_penandatangan="",
    file_ttd_penandatangan=None,
):
    """Return bytes PDF. Data penandatangan (nama/NIP/gambar ttd) sudah
    diresolusi oleh pemanggil (lihat presensi/views.py::
    export_pdf_laporan_serdos) -- fungsi ini murni soal layout."""
    daftar = data_laporan_serdos(bulan, tahun)
    jenis_list = jenis_tanggal_bulan(bulan, tahun)
    jumlah_hari = len(jenis_list)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A3),
        leftMargin=1 * cm, rightMargin=1 * cm, topMargin=1 * cm, bottomMargin=1 * cm,
    )

    styles = getSampleStyleSheet()
    judul_style = ParagraphStyle("judul", parent=styles["Heading1"], fontSize=13, alignment=TA_CENTER, spaceAfter=2)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"], fontSize=10, alignment=TA_CENTER, spaceAfter=1)
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=6.5, alignment=TA_LEFT, leading=8)
    ket_style = ParagraphStyle("ket", parent=styles["Normal"], fontSize=8)
    ttd_style = ParagraphStyle("ttd", parent=styles["Normal"], fontSize=9, alignment=TA_CENTER)

    elements = []

    # ---- Header: logo + judul + yayasan/PTS/bulan ----
    logo_path = finders.find("img/kampus.png")
    logo = RLImage(logo_path, width=1.8 * cm, height=1.8 * cm) if logo_path else ""
    info_header = [
        Paragraph("DAFTAR HADIR DOSEN TETAP YAYASAN PENERIMA SERDOS", judul_style),
        Paragraph(NAMA_LLDIKTI, judul_style),
        Paragraph(f"YAYASAN : {NAMA_YAYASAN}", sub_style),
        Paragraph(f"PTS : {NAMA_PTS}", sub_style),
        Paragraph(f"BULAN : {NAMA_BULAN[bulan - 1].upper()} {tahun}", sub_style),
    ]
    header_table = Table([[logo, info_header]], colWidths=[2.2 * cm, None])
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.4 * cm))

    # ---- Tabel utama ----
    lebar_no, lebar_nama, lebar_gol, lebar_total = 0.8 * cm, 4.2 * cm, 2.2 * cm, 1.3 * cm
    lebar_usable = (42 * cm - 2 * cm) - (lebar_no + lebar_nama + lebar_gol + lebar_total)
    lebar_tanggal = max(lebar_usable / jumlah_hari, 0.6 * cm) if jumlah_hari else 0.6 * cm
    col_widths = [lebar_no, lebar_nama, lebar_gol] + [lebar_tanggal] * jumlah_hari + [lebar_total]

    header_row = (
        ["No", "Nama/NIDN", "Gol/P\nAkademik"]
        + [str(tanggal.day) for tanggal, _jenis in jenis_list]
        + ["Total\nHadir"]
    )
    table_data = [header_row]
    span_commands = []

    for idx, baris in enumerate(daftar, start=1):
        row_num = idx  # baris 0 = header
        nama_nidn = Paragraph(
            f"{baris.user.get_full_name() or baris.user.username}<br/>{baris.user.nidn or ''}", cell_style,
        )

        if baris.tugas_belajar:
            row = (
                [str(idx), nama_nidn, baris.gol_jabatan, "TUGAS BELAJAR / BIAYA PEMERINTAH"]
                + [""] * (jumlah_hari - 1) + [""]
            )
            span_commands.append(("SPAN", (3, row_num), (3 + jumlah_hari - 1, row_num)))
        else:
            sel_tanggal = []
            for hari in baris.hari_grid:
                gambar = None
                if hari.jenis == "kerja" and hari.hadir and baris.paraf:
                    gambar = _gambar_aman(baris.paraf.gambar, LEBAR_PARAF, TINGGI_PARAF)
                sel_tanggal.append(gambar or "")
            row = [str(idx), nama_nidn, baris.gol_jabatan] + sel_tanggal + [str(baris.total_hadir)]

        table_data.append(row)

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
        ("FONTSIZE", (0, 0), (-1, 0), 7),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 1), (-1, -1), 6.5),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        *span_commands,
        *shading_commands,
    ]))
    elements.append(table)

    # ---- Legenda (KET) ----
    elements.append(Spacer(1, 0.3 * cm))
    elements.append(Paragraph("KET:", ket_style))
    elements.append(Paragraph(
        '<font backColor="#d9d9d9">&nbsp;&nbsp;&nbsp;&nbsp;</font>&nbsp;: Hari Minggu', ket_style,
    ))
    hari_libur_bulan = HariLibur.objects.filter(tanggal__year=tahun, tanggal__month=bulan).order_by("tanggal")
    for libur in hari_libur_bulan:
        elements.append(Paragraph(
            f'<font backColor="#d9d9d9">&nbsp;&nbsp;&nbsp;&nbsp;</font>'
            f'&nbsp;: {libur.keterangan} ({libur.tanggal.strftime("%d %B %Y")})',
            ket_style,
        ))

    # ---- Blok tanda tangan ----
    elements.append(Spacer(1, 0.8 * cm))
    blok_kanan = [
        Paragraph(f"{kota}, {tanggal_cetak.strftime('%d %B %Y').upper()}", ttd_style),
        Paragraph(f"{jabatan_penandatangan.upper()},", ttd_style),
    ]
    gambar_ttd = _gambar_aman(file_ttd_penandatangan, 3 * cm, 1.5 * cm) if file_ttd_penandatangan else None
    blok_kanan.append(gambar_ttd if gambar_ttd else Spacer(1, 1.5 * cm))
    blok_kanan.append(Paragraph(f"<u>{nama_penandatangan or '.........................'}</u>", ttd_style))
    blok_kanan.append(Paragraph(f"NIP. {nip_penandatangan}" if nip_penandatangan else "", ttd_style))

    footer_table = Table([["", blok_kanan]], colWidths=[None, 8 * cm])
    elements.append(footer_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
