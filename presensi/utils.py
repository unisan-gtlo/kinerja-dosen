from simda_dosen.models import DataDosen


def get_dosen_by_nidn(nidn):
    """Ambil data dosen dari SIMDA lewat NIDN.

    Presensi tidak bisa memakai ForeignKey lintas app ke simda_dosen: sikd_db
    dan unisan_db adalah database Postgres yang berbeda (lihat
    config/db_router.py::SimdaRouter.allow_relation), jadi resolusi dilakukan
    manual di sini -- pola yang sama dipakai get_simda_dosen_or_none di
    simda_dosen/utils.py.
    """
    if not nidn:
        return None
    return DataDosen.objects.using('simda').filter(nidn=nidn).first()


def get_dosen_serdos_qs():
    """Queryset accounts.User (role=dosen) yang punya Sertifikasi Dosen
    (serdos) berstatus DISETUJUI -- dasar cakupan Laporan Daftar Hadir
    Dosen Serdos ke LLDIKTI (lihat presensi/laporan_serdos.py).

    SENGAJA filter status_validasi='disetujui' (beberapa tempat lain di
    kode, mis. profil/views.py::has_serdos, cuma cek exists() jenis
    sertifikasi tanpa peduli statusnya -- untuk laporan resmi ke
    lembaga eksternal, cuma yang sudah divalidasi yang relevan)."""
    from accounts.models import User
    from profil.models import Sertifikasi

    user_ids = Sertifikasi.objects.filter(
        jenis_sertifikasi="serdos", status_validasi="disetujui",
    ).values_list("user_id", flat=True)
    return User.objects.filter(id__in=user_ids, role="dosen")
