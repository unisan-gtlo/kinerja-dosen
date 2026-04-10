from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from accounts.models import User
from master.models import Fakultas, Prodi, TahunAkademik, Pengaturan
from profil.models import ProfilDosen
from kinerja.models import Penelitian, Publikasi, PKM, HKI, BKD
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import io


@login_required
def index(request):
    tahun_list = TahunAkademik.objects.filter(status='aktif').order_by('-urutan')
    fakultas_list = Fakultas.objects.filter(status='aktif').order_by('kode_fakultas')
    prodi_list = Prodi.objects.filter(status='aktif').order_by('kode_prodi')
    try:
        pengaturan = Pengaturan.objects.first()
    except:
        pengaturan = None
    context = {
        'tahun_list': tahun_list,
        'fakultas_list': fakultas_list,
        'prodi_list': prodi_list,
        'pengaturan': pengaturan,
    }
    return render(request, 'laporan/index.html', context)


def get_dosen_queryset(user, filter_prodi='', filter_fakultas='', filter_status=''):
    if user.role in ['admin', 'rektorat', 'biro']:
        qs = User.objects.filter(role='dosen')
    elif user.role in ['dekan', 'wadek']:
        qs = User.objects.filter(role='dosen', kode_fakultas=user.kode_fakultas)
    elif user.role in ['kaprodi', 'sekprodi', 'operator']:
        qs = User.objects.filter(role='dosen', kode_prodi=user.kode_prodi)
    else:
        qs = User.objects.none()

    if filter_prodi:
        qs = qs.filter(kode_prodi=filter_prodi)
    if filter_fakultas:
        qs = qs.filter(kode_fakultas=filter_fakultas)
    if filter_status:
        qs = qs.filter(status_kepegawaian=filter_status)

    return qs.order_by('kode_fakultas', 'kode_prodi', 'first_name')


# ============================================================
# EXPORT EXCEL
# ============================================================
@login_required
def export_excel_rekap(request):
    filter_tahun = request.GET.get('tahun', '')
    filter_semester = request.GET.get('semester', '')
    filter_prodi = request.GET.get('prodi', '')
    filter_fakultas = request.GET.get('fakultas', '')
    filter_status = request.GET.get('status_kepegawaian', '')

    dosen_qs = get_dosen_queryset(request.user, filter_prodi, filter_fakultas, filter_status)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Rekap Kinerja Dosen"

    # Style
    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='1e3a5f', end_color='1e3a5f', fill_type='solid')
    center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left = Alignment(horizontal='left', vertical='center', wrap_text=True)
    thin = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    # Judul
    ws.merge_cells('A1:N1')
    ws['A1'] = 'REKAP DATA KINERJA DOSEN'
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = center

    ws.merge_cells('A2:N2')
    ws['A2'] = 'Universitas Ichsan Gorontalo'
    ws['A2'].font = Font(bold=True, size=12)
    ws['A2'].alignment = center

    filter_info = []
    if filter_tahun:
        filter_info.append(f'Tahun: {filter_tahun}')
    if filter_semester:
        filter_info.append(f'Semester: {filter_semester}')
    if filter_prodi:
        filter_info.append(f'Prodi: {filter_prodi}')
    if filter_info:
        ws.merge_cells('A3:N3')
        ws['A3'] = ' | '.join(filter_info)
        ws['A3'].alignment = center

    # Header tabel
    headers = [
        'No', 'Nama Dosen', 'NIDN', 'Fakultas', 'Prodi',
        'Jabfung', 'Pend.', 'Status Kpg.',
        'BKD', 'Penelitian', 'Publikasi', 'PKM', 'HKI', 'Profil %'
    ]
    row_header = 5
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=row_header, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = thin

    ws.row_dimensions[row_header].height = 30

    # Data
    for idx, dosen in enumerate(dosen_qs, 1):
        penelitian_qs = dosen.penelitian_set.all()
        publikasi_qs = dosen.publikasi_set.all()
        pkm_qs = dosen.pkm_set.all()
        hki_qs = dosen.hki_set.all()
        bkd_qs = dosen.bkd_set.all()

        if filter_tahun:
            penelitian_qs = penelitian_qs.filter(tahun_akademik=filter_tahun)
            publikasi_qs = publikasi_qs.filter(tahun_akademik=filter_tahun)
            pkm_qs = pkm_qs.filter(tahun_akademik=filter_tahun)
            hki_qs = hki_qs.filter(tahun_akademik=filter_tahun)
            bkd_qs = bkd_qs.filter(tahun_akademik=filter_tahun)

        if filter_semester:
            penelitian_qs = penelitian_qs.filter(semester=filter_semester)
            publikasi_qs = publikasi_qs.filter(semester=filter_semester)
            pkm_qs = pkm_qs.filter(semester=filter_semester)
            hki_qs = hki_qs.filter(semester=filter_semester)
            bkd_qs = bkd_qs.filter(semester=filter_semester)

        try:
            profil = dosen.profil
            kelengkapan = profil.persentase_kelengkapan
            jabfung = profil.jabfung_aktif or '-'
            pendidikan = profil.pendidikan_terakhir or '-'
        except:
            kelengkapan = 0
            jabfung = '-'
            pendidikan = '-'

        row_data = [
            idx,
            dosen.get_full_name() or dosen.username,
            dosen.nidn or '-',
            dosen.kode_fakultas or '-',
            dosen.kode_prodi or '-',
            jabfung,
            pendidikan,
            dosen.status_kepegawaian or 'Aktif',
            bkd_qs.count(),
            penelitian_qs.count(),
            publikasi_qs.count(),
            pkm_qs.count(),
            hki_qs.count(),
            f'{kelengkapan}%',
        ]

        row_num = row_header + idx
        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col, value=value)
            cell.border = thin
            cell.alignment = center if col != 2 else left
            if col == 9 and isinstance(value, int) and value == 0:
                cell.fill = PatternFill(start_color='FFE0E0', end_color='FFE0E0', fill_type='solid')
            elif col in [9, 10, 11, 12, 13] and isinstance(value, int) and value > 0:
                cell.fill = PatternFill(start_color='E0F0E0', end_color='E0F0E0', fill_type='solid')

    # Lebar kolom
    col_widths = [5, 30, 15, 10, 8, 20, 8, 15, 8, 12, 12, 8, 8, 10]
    for col, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width

    # Response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'Rekap_Kinerja_Dosen_{filter_tahun or "Semua"}_{filter_semester or "Semua"}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


@login_required
def export_excel_penelitian(request):
    filter_tahun = request.GET.get('tahun', '')
    filter_semester = request.GET.get('semester', '')
    filter_prodi = request.GET.get('prodi', '')
    filter_fakultas = request.GET.get('fakultas', '')

    dosen_qs = get_dosen_queryset(request.user, filter_prodi, filter_fakultas)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data Penelitian"

    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='1e3a5f', end_color='1e3a5f', fill_type='solid')
    center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left = Alignment(horizontal='left', vertical='center', wrap_text=True)
    thin = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    ws.merge_cells('A1:K1')
    ws['A1'] = 'DATA PENELITIAN DOSEN'
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = center
    ws.merge_cells('A2:K2')
    ws['A2'] = 'Universitas Ichsan Gorontalo'
    ws['A2'].font = Font(bold=True, size=12)
    ws['A2'].alignment = center

    headers = ['No', 'Nama Dosen', 'NIDN', 'Prodi', 'Judul', 'Semester',
               'Tahun Akademik', 'L/N/I', 'Sumber Dana', 'Pendanaan (Juta)', 'Jml Mahasiswa']
    row_h = 4
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=row_h, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = thin

    row_num = row_h + 1
    no = 1
    for dosen in dosen_qs:
        penelitian_qs = dosen.penelitian_set.all()
        if filter_tahun:
            penelitian_qs = penelitian_qs.filter(tahun_akademik=filter_tahun)
        if filter_semester:
            penelitian_qs = penelitian_qs.filter(semester=filter_semester)

        for p in penelitian_qs:
            row_data = [
                no, dosen.get_full_name() or dosen.username,
                dosen.nidn or '-', dosen.kode_prodi or '-',
                p.judul, p.semester or '-', p.tahun_akademik,
                p.get_ln_i_display() if p.ln_i else '-',
                p.sumber or '-', float(p.pendanaan), p.jml_mahasiswa
            ]
            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_num, column=col, value=value)
                cell.border = thin
                cell.alignment = left if col in [5] else center
            row_num += 1
            no += 1

    col_widths = [5, 25, 15, 8, 50, 10, 15, 8, 20, 15, 12]
    for col, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'Data_Penelitian_{filter_tahun or "Semua"}_{filter_semester or "Semua"}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


@login_required
def export_excel_publikasi(request):
    filter_tahun = request.GET.get('tahun', '')
    filter_semester = request.GET.get('semester', '')
    filter_prodi = request.GET.get('prodi', '')
    filter_fakultas = request.GET.get('fakultas', '')

    dosen_qs = get_dosen_queryset(request.user, filter_prodi, filter_fakultas)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data Publikasi"

    header_font = Font(bold=True, color='FFFFFF', size=11)
    header_fill = PatternFill(start_color='1e3a5f', end_color='1e3a5f', fill_type='solid')
    center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    left = Alignment(horizontal='left', vertical='center', wrap_text=True)
    thin = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    ws.merge_cells('A1:K1')
    ws['A1'] = 'DATA PUBLIKASI DOSEN'
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = center
    ws.merge_cells('A2:K2')
    ws['A2'] = 'Universitas Ichsan Gorontalo'
    ws['A2'].font = Font(bold=True, size=12)
    ws['A2'].alignment = center

    headers = ['No', 'Nama Dosen', 'NIDN', 'Prodi', 'Judul',
               'Jenis', 'Nama Jurnal', 'Volume', 'Nomor',
               'Tahun Terbit', 'Semester', 'Tahun Akademik']
    row_h = 4
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=row_h, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = thin

    row_num = row_h + 1
    no = 1
    for dosen in dosen_qs:
        publikasi_qs = dosen.publikasi_set.all()
        if filter_tahun:
            publikasi_qs = publikasi_qs.filter(tahun_akademik=filter_tahun)
        if filter_semester:
            publikasi_qs = publikasi_qs.filter(semester=filter_semester)

        for p in publikasi_qs:
            row_data = [
                no, dosen.get_full_name() or dosen.username,
                dosen.nidn or '-', dosen.kode_prodi or '-',
                p.judul, p.jenis_publikasi,
                p.nama_jurnal or '-', p.volume or '-',
                p.nomor or '-', p.tahun_terbit or '-',
                p.semester or '-', p.tahun_akademik
            ]
            for col, value in enumerate(row_data, 1):
                cell = ws.cell(row=row_num, column=col, value=value)
                cell.border = thin
                cell.alignment = left if col == 5 else center
            row_num += 1
            no += 1

    col_widths = [5, 25, 15, 8, 50, 8, 30, 8, 8, 12, 10, 15]
    for col, width in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(col)].width = width

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f'Data_Publikasi_{filter_tahun or "Semua"}_{filter_semester or "Semua"}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


# ============================================================
# EXPORT PDF
# ============================================================
@login_required
def export_pdf_rekap(request):
    filter_tahun = request.GET.get('tahun', '')
    filter_semester = request.GET.get('semester', '')
    filter_prodi = request.GET.get('prodi', '')
    filter_fakultas = request.GET.get('fakultas', '')
    filter_status = request.GET.get('status_kepegawaian', '')

    dosen_qs = get_dosen_queryset(request.user, filter_prodi, filter_fakultas, filter_status)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=1*cm, leftMargin=1*cm,
        topMargin=1.5*cm, bottomMargin=1*cm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('title', parent=styles['Heading1'],
                                  fontSize=14, alignment=TA_CENTER, spaceAfter=4)
    sub_style = ParagraphStyle('sub', parent=styles['Normal'],
                                fontSize=10, alignment=TA_CENTER, spaceAfter=2)
    small_style = ParagraphStyle('small', parent=styles['Normal'],
                                  fontSize=8, alignment=TA_LEFT)

    elements = []
    elements.append(Paragraph('REKAP DATA KINERJA DOSEN', title_style))
    elements.append(Paragraph('Universitas Ichsan Gorontalo', sub_style))

    filter_info = []
    if filter_tahun:
        filter_info.append(f'Tahun: {filter_tahun}')
    if filter_semester:
        filter_info.append(f'Semester: {filter_semester}')
    if filter_prodi:
        filter_info.append(f'Prodi: {filter_prodi}')
    if filter_info:
        elements.append(Paragraph(' | '.join(filter_info), sub_style))

    elements.append(Spacer(1, 0.3*cm))

    header_color = colors.HexColor('#1e3a5f')
    alt_color = colors.HexColor('#f0f4f8')

    table_data = [['No', 'Nama Dosen', 'NIDN', 'Prodi', 'Jabfung',
                   'Pend.', 'Status', 'BKD', 'Penelitian', 'Publikasi', 'PKM', 'HKI', 'Profil%']]

    for idx, dosen in enumerate(dosen_qs, 1):
        penelitian_qs = dosen.penelitian_set.all()
        publikasi_qs = dosen.publikasi_set.all()
        pkm_qs = dosen.pkm_set.all()
        hki_qs = dosen.hki_set.all()
        bkd_qs = dosen.bkd_set.all()

        if filter_tahun:
            penelitian_qs = penelitian_qs.filter(tahun_akademik=filter_tahun)
            publikasi_qs = publikasi_qs.filter(tahun_akademik=filter_tahun)
            pkm_qs = pkm_qs.filter(tahun_akademik=filter_tahun)
            hki_qs = hki_qs.filter(tahun_akademik=filter_tahun)
            bkd_qs = bkd_qs.filter(tahun_akademik=filter_tahun)

        if filter_semester:
            penelitian_qs = penelitian_qs.filter(semester=filter_semester)
            publikasi_qs = publikasi_qs.filter(semester=filter_semester)
            pkm_qs = pkm_qs.filter(semester=filter_semester)
            hki_qs = hki_qs.filter(semester=filter_semester)
            bkd_qs = bkd_qs.filter(semester=filter_semester)

        try:
            profil = dosen.profil
            kelengkapan = profil.persentase_kelengkapan
            jabfung = profil.jabfung_aktif or '-'
            pendidikan = profil.pendidikan_terakhir or '-'
        except:
            kelengkapan = 0
            jabfung = '-'
            pendidikan = '-'

        table_data.append([
            str(idx),
            Paragraph(dosen.get_full_name() or dosen.username, small_style),
            dosen.nidn or '-',
            dosen.kode_prodi or '-',
            jabfung,
            pendidikan,
            dosen.status_kepegawaian or 'Aktif',
            str(bkd_qs.count()),
            str(penelitian_qs.count()),
            str(publikasi_qs.count()),
            str(pkm_qs.count()),
            str(hki_qs.count()),
            f'{kelengkapan}%',
        ])

    col_widths_pdf = [1*cm, 5*cm, 2.5*cm, 1.8*cm, 3*cm,
                      1.5*cm, 2.5*cm, 1.2*cm, 1.8*cm, 1.8*cm, 1.2*cm, 1.2*cm, 1.5*cm]

    table = Table(table_data, colWidths=col_widths_pdf, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_color),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, alt_color]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    filename = f'Rekap_Kinerja_Dosen_{filter_tahun or "Semua"}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response