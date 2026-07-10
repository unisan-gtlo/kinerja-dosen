class SimdaRouter:
    """Arahkan app 'simda_dosen' (model unmanaged mirror tabel SIMDA)
    ke koneksi database 'simda'. Semua app lain tetap pakai 'default' (sikd_db).
    """

    simda_app = 'simda_dosen'

    def db_for_read(self, model, **hints):
        if model._meta.app_label == self.simda_app:
            return 'simda'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label == self.simda_app:
            return 'simda'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        simda_labels = {obj1._meta.app_label, obj2._meta.app_label}
        if self.simda_app in simda_labels:
            return simda_labels == {self.simda_app}
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == self.simda_app:
            # Model unmanaged (managed=False) -- tidak pernah dimigrasi dari
            # SIKD, skema tabel dikelola sepenuhnya oleh SIMDA.
            return False
        return db == 'default'
