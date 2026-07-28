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
