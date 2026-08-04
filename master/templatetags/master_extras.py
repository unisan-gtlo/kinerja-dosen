from django import template

register = template.Library()


@register.filter
def format_link(url_template, id_value):
    """Ganti placeholder "{id}" pada template URL profil riset (SINTA/
    Scopus/Google Scholar/ORCID/Garuda, lihat master.Pengaturan) dengan
    nilai ID milik dosen. Return string kosong kalau ID atau template-nya
    kosong, supaya link tidak dirender sama sekali."""
    if not id_value or not url_template:
        return ''
    return url_template.replace('{id}', str(id_value))
