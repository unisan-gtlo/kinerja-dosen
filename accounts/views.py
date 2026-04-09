from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from master.models import Fakultas, Prodi
from .models import User

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.status_akun == 'aktif':
                login(request, user)
                return redirect('dashboard:index')
            else:
                messages.error(request, 'Akun Anda tidak aktif. Hubungi administrator.')
        else:
            messages.error(request, 'Username atau password salah.')
    return render(request, 'accounts/login.html')

def logout_view(request):
    logout(request)
    return redirect('accounts:login')

@login_required
def kelola_user(request):
    if request.user.role != 'admin':
        messages.error(request, 'Anda tidak memiliki akses.')
        return redirect('dashboard:index')

    fakultas_list = Fakultas.objects.filter(status='aktif').order_by('kode_fakultas')
    prodi_list = Prodi.objects.filter(status='aktif').order_by('kode_prodi')

    # Filter
    role_filter = request.GET.get('role', '')
    fakultas_filter = request.GET.get('fakultas', '')
    prodi_filter = request.GET.get('prodi', '')
    cari = request.GET.get('cari', '')

    users = User.objects.all().order_by('kode_fakultas', 'kode_prodi', 'first_name')

    if role_filter:
        users = users.filter(role=role_filter)
    if fakultas_filter:
        users = users.filter(kode_fakultas=fakultas_filter)
    if prodi_filter:
        users = users.filter(kode_prodi=prodi_filter)
    if cari:
        users = users.filter(
            first_name__icontains=cari
        ) | users.filter(
            last_name__icontains=cari
        ) | users.filter(
            username__icontains=cari
        ) | users.filter(
            nidn__icontains=cari
        )

    context = {
        'users': users,
        'fakultas_list': fakultas_list,
        'prodi_list': prodi_list,
        'role_filter': role_filter,
        'fakultas_filter': fakultas_filter,
        'prodi_filter': prodi_filter,
        'cari': cari,
    }
    return render(request, 'accounts/kelola_user.html', context)

@login_required
def tambah_user(request):
    if request.user.role != 'admin':
        return redirect('dashboard:index')

    fakultas_list = Fakultas.objects.filter(status='aktif').order_by('kode_fakultas')
    prodi_list = Prodi.objects.filter(status='aktif').order_by('kode_prodi')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        nidn = request.POST.get('nidn', '').strip()
        role = request.POST.get('role', 'dosen')
        kode_fakultas = request.POST.get('kode_fakultas', '').strip()
        kode_prodi = request.POST.get('kode_prodi', '').strip()
        no_hp = request.POST.get('no_hp', '').strip()
        password = request.POST.get('password', '').strip()

        if not username or not password or not first_name:
            messages.error(request, 'Username, nama depan, dan password wajib diisi.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, f'Username "{username}" sudah digunakan.')
        else:
            user = User.objects.create(
                username=username,
                first_name=first_name,
                last_name=last_name,
                email=email,
                nidn=nidn,
                role=role,
                kode_fakultas=kode_fakultas,
                kode_prodi=kode_prodi,
                no_hp=no_hp,
                password=make_password(password),
                status_akun='aktif'
            )
            messages.success(request, f'User "{username}" berhasil ditambahkan.')
            return redirect('accounts:kelola_user')

    context = {
        'fakultas_list': fakultas_list,
        'prodi_list': prodi_list,
    }
    return render(request, 'accounts/tambah_user.html', context)

@login_required
def edit_user(request, user_id):
    if request.user.role != 'admin':
        return redirect('dashboard:index')

    target_user = get_object_or_404(User, id=user_id)
    fakultas_list = Fakultas.objects.filter(status='aktif').order_by('kode_fakultas')
    prodi_list = Prodi.objects.filter(status='aktif').order_by('kode_prodi')

    if request.method == 'POST':
        target_user.first_name = request.POST.get('first_name', '').strip()
        target_user.last_name = request.POST.get('last_name', '').strip()
        target_user.email = request.POST.get('email', '').strip()
        target_user.nidn = request.POST.get('nidn', '').strip()
        target_user.role = request.POST.get('role', target_user.role)
        target_user.kode_fakultas = request.POST.get('kode_fakultas', '').strip()
        target_user.kode_prodi = request.POST.get('kode_prodi', '').strip()
        target_user.no_hp = request.POST.get('no_hp', '').strip()
        target_user.status_akun = request.POST.get('status_akun', 'aktif')

        password_baru = request.POST.get('password_baru', '').strip()
        if password_baru:
            target_user.password = make_password(password_baru)

        target_user.save()
        messages.success(request, f'User "{target_user.username}" berhasil diupdate.')
        return redirect('accounts:kelola_user')

    context = {
        'target_user': target_user,
        'fakultas_list': fakultas_list,
        'prodi_list': prodi_list,
    }
    return render(request, 'accounts/edit_user.html', context)

@login_required
def hapus_user(request, user_id):
    if request.user.role != 'admin':
        return redirect('dashboard:index')

    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, 'Tidak bisa menghapus akun sendiri.')
    else:
        username = target_user.username
        target_user.delete()
        messages.success(request, f'User "{username}" berhasil dihapus.')
    return redirect('accounts:kelola_user')