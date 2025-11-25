import base64
from datetime import datetime
from functools import wraps
import hashlib
import json
import os
import re
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.shortcuts import redirect, render, HttpResponse
from django.contrib.auth.hashers import make_password
from app.models import anggota, berita, kabupaten, kategoriberita, kategoriwisata, kecamatan, kegiatan, obyekwisata, pengelola, provinsi
from django.utils import timezone
from django.core.files.storage import FileSystemStorage
from functools import wraps
from django.http import JsonResponse
from django.core.paginator import Paginator
from scripts.algoritma_pso import CalculatePSO
from scripts.excel_importer import sync_excel
from .models import hasilitinerary, jarakobyek, pengelola

# Create your views here.
class HomePage():
    def GetHomeView(request):
        user_id = request.session.get("user_id")

        if user_id:
            try:
                akun_admin = pengelola.objects.filter(pengelolaKODE = user_id).first()
                if akun_admin :
                    request.session["akun_id"] = akun_admin.pengelolaKODE
                    return redirect("admindashboard")
                elif not akun_admin :
                    akun_user = anggota.objects.filter(anggotaKODE = user_id).first()
                    request.session["akun_id"] = akun_user.anggotaKODE
            except Exception as e :
                print(f"Error get akun Home {e}")

        # --- Data Home ---
        query_destinasi = obyekwisata.objects.all().order_by('-obyekPOPULARITAS')[:10]
        query_kegiatan = kegiatan.objects.all().order_by('-eventSELESAI')[:10]
        query_berita = berita.objects.all().order_by('-beritaTGL')[:10]

        # --- Search bar ---
        search_query = request.GET.get("searchdestinasi", "")
        results = []
        if search_query:
            results = obyekwisata.objects.filter(obyekNAMA__icontains=search_query)

        return render(request, "user/home.html", {
            'destinasi': query_destinasi,
            'kegiatan': query_kegiatan,
            'berita' : query_berita,
            'results': results,
            'user_id' : user_id
        })

    def GetDetailDestinasiView(request, obyekKODE):
        object_obyekwisata = obyekwisata.objects.filter(obyekKODE=obyekKODE).first()
        list_object_berita = berita.objects.filter(obyekKODE=obyekKODE)
        list_object_kegiatan = kegiatan.objects.filter(eventNAMA__icontains=object_obyekwisata.obyekNAMA)

        return render(request, "user/detaildestinasi.html", {"obyek": object_obyekwisata, 
                                                             "berita" : list_object_berita,
                                                             "kegiatan" : list_object_kegiatan})

    def GetDetailKegiatanView(request, eventKODE):
        object_kegiatan = kegiatan.objects.filter(eventKODE=eventKODE).first()

        # ambil bagian setelah "-"
        obyekwisata_nama = object_kegiatan.eventNAMA.split(" - ")[-1].strip()
        object_obyekwisata = obyekwisata.objects.filter(obyekNAMA__icontains=obyekwisata_nama).first()

        # list_object_destinasi = obyekwisata.filter()

        return render (request, "user/detailkegiatan.html", {"kegiatan": object_kegiatan, "obyekwisata" : object_obyekwisata})
    
    def GetDetailBeritaView(request, beritaKODE):
        object_berita = berita.objects.filter(beritaKODE = beritaKODE).first()
        object_obyekwisata = object_obyekwisata = object_berita.obyekKODE

        return render(request, "user/detailberita.html", {"berita" : object_berita,
                                                          "obyekwisata" : object_obyekwisata})

class LoginPage():
    def GetLoginView(request):
        if request.method == "POST":
            email = request.POST.get("email")
            password = request.POST.get("password")
            # Hash password input user
            hashed_password = base64.b64encode(
                hashlib.sha1(password.encode()).digest()
            ).decode()

            try :
                akun_admin = pengelola.objects.filter(
                    pengelolaEMAIL=email,
                    pengelolaPASSWORD=hashed_password
                ).first()
                if akun_admin:
                    request.session["user_id"] = akun_admin.pengelolaKODE

                    return redirect("admindashboard")

                elif not akun_admin:
                    akun_anggota = anggota.objects.filter(
                        anggotaEMAIL=email,
                        anggotaPASSWORD=hashed_password
                    ).first()
                    if akun_anggota:
                        request.session["user_id"] = akun_anggota.anggotaKODE

                        return redirect("home")
                    
                # Kalau dua-duanya tidak cocok
                messages.error(request, "Email atau password salah!")
                return redirect("login")
            except Exception as e:
                 messages.error(request, "Email atau password salah!")
                 return redirect("login")

        return render(request, "login.html")
    
    def Logout(request):
        try:
            request.session.flush()  # hapus semua data session
        except Exception as e:
            print(f"Error logout: {e}")
        return redirect("home")  # arahkan balik ke home

class SignupPage():
    def GetSignupView(request):
        if request.method == "POST":
            try:
                email = request.POST.get("email")
                password = request.POST.get("password")
                nama = request.POST.get("nama")
                nomor_handphone = request.POST.get('nomor_handphone')
                konfirmasi_password = request.POST.get('konfirmasi_password')

                # Cek domain email harus @gmail.com
                if not email.endswith("@gmail.com"):
                    messages.error(request, "Email harus menggunakan domain @gmail.com.")
                    return redirect('signup')

                # Cek apakah email sudah terdaftar
                if anggota.objects.filter(anggotaEMAIL=email).exists():
                    messages.error(request, "Email sudah terdaftar. Silakan gunakan email lain.")
                    return redirect('signup')

                # Cek kesamaan password dan konfirmasi password
                if password != konfirmasi_password:
                    messages.error(request, "Password dan konfirmasi password tidak cocok.")
                    return redirect('signup')

                # Validasi kekuatan password
                # - Minimal 8 karakter
                # - Mengandung minimal 1 huruf besar
                # - Mengandung minimal 1 angka
                password_pattern = r'^(?=.*[A-Z])(?=.*\d)[A-Za-z\d]{8,}$'
                if not re.match(password_pattern, password):
                    messages.error(
                        request,
                        "Password harus minimal 8 karakter, mengandung huruf besar dan angka."
                    )
                    return redirect('signup')
                
                # Validasi nomor handphone
                # Harus diawali '08' dan diikuti 7–11 digit angka
                phone_pattern = r'^08[0-9]{7,11}$'
                if not re.match(phone_pattern, nomor_handphone):
                    messages.error(
                        request,
                        "Nomor handphone harus diawali 08 dan memiliki 9–13 digit angka."
                    )
                    return redirect('signup')

                hashed_password = base64.b64encode(hashlib.sha1(password.encode()).digest()).decode()

                user = anggota(
                    anggotaNAMA = nama,
                    anggotaEMAIL = email,
                    anggotaPASSWORD = hashed_password,
                    anggotaHP = nomor_handphone
                ) 
                user.save()

                messages.success(request, 'Pendaftaran berhasil! Silakan login dengan akun Anda.')
                return redirect("login")
            except Exception as e:
                print("Error On Sign Up")
                return render(request, "signup.html")
        return render(request, "signup.html")

class ErrorPage():
    def GetErrorPage(request):
        return render(request, "error.html")

class ItineraryPage():
    def GetItineraryFormPageView(request):
        user_id = request.session.get("user_id")

        if request.method == "POST":
            try:
                judul_perjalanan = request.POST.get("judul_perjalanan")

                hotel_kode = request.POST.get("hotel")
                selected_obyek_str = request.POST.get("selected_obyek")
                kapasitas_hari = request.POST.get("kapasitas_hari")

                jam_mulai = request.POST.get("jam_mulai")
                jam_selesai = request.POST.get("jam_selesai")

                hari_input = request.POST.get("kapasitas_hari")

                # Cek apakah ada field yang kosong
                if not user_id:
                    messages.error(request, "Silahkan Login Lebih Dahulu")
                    return redirect('itineraryform')

                # Cek apakah ada field yang kosong
                if not all([judul_perjalanan, hotel_kode, selected_obyek_str, kapasitas_hari, jam_mulai, jam_selesai]):
                    messages.error(request, "Semua field wajib diisi. Silakan lengkapi data yang kosong.")
                    return redirect('itineraryform')
                
                # Parse selected objek wisata (comma-separated kode)
                selected_obyek_kodes = selected_obyek_str.split(",")

                # Process itinerary creation here
                dict_routes, dict_destination, mapping_destination = CalculatePSO().get_routes(hotel_kode=hotel_kode, list_obyek_kode=selected_obyek_kodes)
                value_time_rating, optimal_routes, destination_cant_visit, total_time_spend, routes_schedule = CalculatePSO().calculate_itinerary(kapasitas_hari=kapasitas_hari, dict_routes=dict_routes, dict_destination=dict_destination, jam_mulai=jam_mulai, jam_selesai=jam_selesai, judul_itinerary=judul_perjalanan)
     
                
                hasilitinerary = CalculatePSO().saveItinerary(jam_mulai=jam_mulai, jam_selesai=jam_selesai, hari_input=hari_input, mapping_destination=mapping_destination
                                                              ,destination_cant_visit=destination_cant_visit, user_id=user_id, judul_perjalanan=judul_perjalanan,
                                                              routes_schedule=routes_schedule, score=value_time_rating)


                hasil_kode = hasilitinerary.hasilKODE
                return redirect('itinerarydetail', hasilKODE=hasil_kode)
            except Exception as e:
                print(f"Error creating itinerary: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat membuat itinerary.")
                return redirect('itineraryform')

        list_object_obyekwisata_hotel = obyekwisata.objects.filter(kategoriKODE__kategoriwisataNAMA='Penginapan')
        list_object_obyekwisata = obyekwisata.objects.exclude(kategoriKODE__kategoriwisataNAMA='Penginapan').order_by("obyekNAMA")


        return render(request, "user/itineraryform.html", {
        "list_object_obyekwisata_hotel": list_object_obyekwisata_hotel,
        "list_object_obyekwisata" : list_object_obyekwisata
    })
    
    def GetItineraryHistoryView(request):
        user_id = request.session.get("user_id")
        akun_user = anggota.objects.filter(anggotaKODE=user_id).first()

        list_obj = hasilitinerary.objects.filter(anggotaKODE = akun_user).order_by('-datecreated')

        return render(request, "user/itineraryhistory.html", {"list_itinerary": list_obj})

    def GetItineraryMapView(request, hasilKODE):
        """View utama - load halaman dulu tanpa map"""
        # Hanya ambil data dasar untuk sidebar, tanpa generate map
        dict_map = CalculatePSO().create_map_data_basic(hasilKODE=hasilKODE)
        
        return render(request, 'user/itinerarymap.html', {
            'dict_map': dict_map,
            'hasil_kode': hasilKODE
        })

    def GetItineraryMapDataView(request, hasilKODE):
        """API endpoint - load map secara async"""
        if request.method == 'GET':
            try:
                # Generate map (proses yang lama)
                _, map = CalculatePSO().create_map_data(hasilKODE=hasilKODE)
                map_html = map._repr_html_()
                
                return JsonResponse({
                    'success': True,
                    'map_html': map_html
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': str(e)
                }, status=500)
        
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)

    def GetAllDestinationsMapView(request):
        """Render map langsung tanpa async"""
        if request.method == 'GET':
            try:
                # Generate map langsung
                map = CalculatePSO().create_all_destinations_map()
                map_html = map._repr_html_()
                
                # Render template dengan map HTML
                return render(request, 'user/map_all_destinations.html', {
                    'map_html': map_html
                })
                
            except Exception as e:
                # Jika error, render template dengan error message
                return render(request, 'user/map_all_destinations.html', {
                    'error': str(e)
                })


def admin_required(view_func):
    """Reusable decorator buat ngecek apakah user admin (pengelola)."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        user_id = request.session.get("user_id")

        if not user_id:
            messages.error(request, "Unauthorized, login required.")
            return redirect("error")

        if pengelola.objects.filter(pengelolaKODE=user_id).exists():
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "Forbidden, only admin can access this page.")
            return redirect("error")
        
    return _wrapped_view

class AdminPage():
    @admin_required
    def GetDashboardView(request):
        user_id = request.session.get("user_id")
        akun_admin = pengelola.objects.filter(pengelolaKODE=user_id).first()

        obyekwisata_count = obyekwisata.objects.count()
        kegiatan_count = kegiatan.objects.count()
        berita_count = berita.objects.count()
        kategoriwisata_count = kategoriwisata.objects.count()
        kategoriberita_count = kategoriberita.objects.count()
        provinsi_count = provinsi.objects.count()
        kabupaten_count = kabupaten.objects.count()
        kecamatan_count = kecamatan.objects.count()
        jarakobyek_count = jarakobyek.objects.count()

        count_dict = {
            'obyekwisata_count' : obyekwisata_count,
            'kegiatan_count' : kegiatan_count,
            'berita_count' : berita_count,
            'kategoriwisata_count' : kategoriwisata_count,
            'kategoriberita_count' : kategoriberita_count,
            'provinsi_count' : provinsi_count,
            'kabupaten_count' : kabupaten_count,
            'kecamatan_count' : kecamatan_count,
            'jarakobyek_count' : jarakobyek_count
        }

        return render(request, "admin/admindashboard.html", {"akun": akun_admin, "dict_count" : count_dict})
    
    #provinsi
    @admin_required
    def GetTambahProvinsiView(request):
        if request.method == "POST":
            try:
                kode = request.POST.get("kode")
                nama = request.POST.get("nama")
                keterangan = request.POST.get("keterangan")
                alamat = request.POST.get('alamat')

                user_id = request.session.get("user_id")
                user = pengelola.objects.get(pengelolaKODE=user_id)

                required_fields = {
                    "Kode": kode,
                    "Nama": nama,
                    "Alamat": alamat
                }

                # Cek mana yang kosong
                missing = [key for key, value in required_fields.items() if not value or value.strip() == ""]

                if missing:
                    messages.error(
                        request,
                        f"Silahkan isi kolom : {', '.join(missing)}."
                    )
                    return redirect("tambahprovinsi")

                date_now = timezone.now().date()
                 # Cek kalau kode sudah ada
                if provinsi.objects.filter(provinsiKODE=kode).exists():
                    messages.error(request, f"❌ Kode {kode} sudah terdaftar, silakan pakai kode lain.")
                    return redirect('tambahprovinsi')

                provinsi_insert = provinsi(
                    provinsiKODE = kode,
                    provinsiNAMA = nama,
                    provinsiKET = keterangan,
                    provinsiALAMAT = alamat,
                    datecreated = date_now,
                    usercreated = user
                )

                provinsi_insert.save()
                messages.success(request, "✅ Anda berhasil input provinsi baru!")
                return redirect('tambahprovinsi')
            except Exception as e:
                print("Error On Tambah Provinsi")
                return redirect('tambahprovinsi')
            
        list_obj_provinsi = provinsi.objects.all().order_by("provinsiKODE")
        return render(request, "admin/provinsi.html", {"provinsi": list_obj_provinsi})
    
    @admin_required
    def GetEditProvinsiView(request, provinsiKODE):
        list_obj_provinsi = provinsi.objects.all().order_by("provinsiKODE")
        provinsi_obj = provinsi.objects.filter(provinsiKODE=provinsiKODE).first()

        if request.method == "POST":
            try : 
                user_id = request.session.get("user_id")
                user = pengelola.objects.get(pengelolaKODE=user_id)

                date_now = timezone.now().date()

                provinsi_obj.provinsiNAMA = request.POST.get("nama")
                provinsi_obj.provinsiKET = request.POST.get("keterangan")
                provinsi_obj.provinsiALAMAT = request.POST.get("alamat")
                provinsi_obj.dateupdated = date_now
                provinsi_obj.userupdated = user

                
                provinsi_obj.save()
                messages.success(request, "✅ Data provinsi berhasil diupdate!")
                return redirect("tambahprovinsi")
            except Exception as e:
                print(f"Error On Edit Provinsi: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat mengupdate Provinsi.")
                return redirect('editprovinsi', provinsiKODE=provinsiKODE)
        
        
        return render(request, "admin/provinsi.html", {
            "provinsi": list_obj_provinsi,
            "edit_prov": provinsi_obj,
        })
    
    @admin_required
    def GetDeleteProvinsiView(request, provinsiKODE):
        list_obj_provinsi = provinsi.objects.all().order_by("provinsiKODE")
        provinsi_obj = provinsi.objects.filter(provinsiKODE=provinsiKODE).first()

        if request.method == "POST":
            provinsi_obj.delete()
            messages.success(request, "🗑️ Data provinsi berhasil dihapus!")
            return redirect('tambahprovinsi')

        return render(request, "admin/provinsi.html", {
            "provinsi": list_obj_provinsi,
            "delete_prov": provinsi_obj,
        })
    
    #kabupaten
    @admin_required
    def GetTambahKabupatenView(request):
        if request.method == "POST":
            kode = request.POST.get("kode")
            provinsi_kode = request.POST.get("provinsi")
            nama = request.POST.get("nama")
            keterangan = request.POST.get("keterangan")
            alamat = request.POST.get("alamat")
            foto_icon_file = request.FILES.get("foto_icon")
            foto_icon_ket = request.POST.get('foto_icon_ket')

            required_fields = {
                "Kode": kode,
                "Provinsi": provinsi_kode,
                "Nama": nama,
                "Alamat" : alamat
            }

            # Cek mana yang kosong
            missing = [key for key, value in required_fields.items() if not value or value.strip() == ""]

            if missing:
                messages.error(
                    request,
                    f"Silahkan isi kolom : {', '.join(missing)}."
                )
                return redirect("tambahkabupaten")
            
            # Get provinsi object
            provinsi_obj = None 
            if provinsi_kode:
                provinsi_obj = provinsi.objects.get(provinsiKODE=provinsi_kode)

                kode = provinsi_obj.provinsiKODE + '.' + kode
            
            user_id = request.session.get("user_id")
            user = pengelola.objects.get(pengelolaKODE=user_id)

            date_now = timezone.now().date()

            foto_icon_path = None
            file_name = None
            if foto_icon_file:
                # folder simpan file
                upload_dir = os.path.join(settings.MEDIA_ROOT, "kabupaten")
                os.makedirs(upload_dir, exist_ok=True)

                # path file
                file_name = f"{kode}_{foto_icon_file.name}"
                file_path = os.path.join(upload_dir, file_name)

                # simpan file fisik
                with open(file_path, "wb+") as dest:
                    for chunk in foto_icon_file.chunks():
                        dest.write(chunk)

                # simpan path relatif (untuk database)
                foto_icon_path = f"kabupaten/{file_name}"

            kabupaten_obj = kabupaten(
                kabupatenKODE=kode,
                provinsiKODE=provinsi_obj,
                kabupatenNAMA=nama,
                kabupatenKET=keterangan,
                kabupatenALAMAT=alamat,
                kabupatenFOTOICON=file_name,
                kabupatenFOTOICONKET = foto_icon_ket,
                datecreated=date_now,
                usercreated=user
            )
            kabupaten_obj.save()
            messages.success(request, "✅ Data kabupaten berhasil disimpan!")
            return redirect("tambahkabupaten")

        list_obj_kabupaten = kabupaten.objects.all().order_by("kabupatenKODE")
        list_obj_provinsi =  provinsi.objects.all().order_by("provinsiNAMA")
        return render(request, "admin/kabupaten.html", {
            "kabupaten": list_obj_kabupaten,
            "provinsi": list_obj_provinsi
        })
    
    @admin_required
    def GetEditKabupatenView(request, kabupatenKODE):
        list_obj_kabupaten = kabupaten.objects.all().order_by("kabupatenKODE")
        list_obj_provinsi =  provinsi.objects.all().order_by("provinsiNAMA")
        kabupaten_obj = kabupaten.objects.filter(kabupatenKODE= kabupatenKODE).first()

        if request.method == "POST":
            try:
                user_id = request.session.get("user_id")
                user = pengelola.objects.get(pengelolaKODE=user_id)

                date_now = timezone.now().date()

                kabupaten_obj.kabupatenNAMA = request.POST.get("nama")
                kabupaten_obj.kabupatenKET = request.POST.get("keterangan")
                kabupaten_obj.kabupatenALAMAT = request.POST.get("alamat")
                foto = request.FILES.get("foto_icon")
                if foto:
                    fs = FileSystemStorage(location='media/kabupaten')
                    filename = fs.save(foto.name, foto)
                    kabupaten_obj.kabupatenFOTOICON = filename
                kabupaten_obj.kabupatenFOTOICONKET = request.POST.get("foto_icon_ket")
                kabupaten_obj.dateupdated = date_now
                kabupaten_obj.userupdated = user

                kabupaten_obj.save()
                messages.success(request, "✅ Data kabupaten berhasil diupdate!")
                return redirect("tambahkabupaten")
            except Exception as e:
                print(f"Error On Edit Kabupaten: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat mengupdate kabupaten.")
                return redirect('editkabupaten', kabupatenKODE=kabupatenKODE)
        
        return render(request, "admin/kabupaten.html", {
            "kabupaten": list_obj_kabupaten,
            "provinsi": list_obj_provinsi,
            "edit_kab": kabupaten_obj,
        })

    @admin_required
    def GetDeleteKabupatenView(request, kabupatenKODE):
        list_obj_kabupaten = kabupaten.objects.all()
        list_obj_provinsi = provinsi.objects.all()
        kabupaten_obj = kabupaten.objects.filter(kabupatenKODE= kabupatenKODE).first()

        if request.method == "POST":
            try:
                kabupaten_obj.delete()
                messages.success(request, "🗑️ Data kabupaten berhasil dihapus!")
                return redirect('tambahkabupaten')
            except Exception as e:
                print(f"Error On Delete Kabupaten: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat menghapus kabupaten.")
                return redirect('tambahkabupaten')

        return render(request, "admin/kabupaten.html", {
            "kabupaten": list_obj_kabupaten,
            "provinsi": list_obj_provinsi,
            "delete_kab": kabupaten_obj,
        })

    #kecamatan
    @admin_required
    def GetTambahKecamatanView(request):
        if request.method == "POST":
            try:
                kode = request.POST.get("kode")
                kabupaten_kode = request.POST.get("kabupaten")
                nama = request.POST.get("nama")
                alamat = request.POST.get('alamat')
                keterangan = request.POST.get("keterangan")

                required_fields = {
                    "Kode": kode,
                    "kabupaten": kabupaten_kode,
                    "Nama": nama,
                    "Alamat" : alamat
                }

                # Cek mana yang kosong
                missing = [key for key, value in required_fields.items() if not value or value.strip() == ""]

                if missing:
                    messages.error(
                        request,
                        f"Silahkan isi kolom : {', '.join(missing)}."
                    )
                    return redirect("tambahkecamatan")

                user_id = request.session.get("user_id")
                user = pengelola.objects.get(pengelolaKODE=user_id)

                date_now = timezone.now().date()

                kabupaten_obj = None
                if kabupaten_kode:
                    kabupaten_obj = kabupaten.objects.get(kabupatenKODE=kabupaten_kode)

                    kode = kabupaten_obj.kabupatenKODE +'.'+kode

                kecamatan_insert = kecamatan(
                    kecamatanKODE=kode,
                    kabupatenKODE=kabupaten_obj,
                    kecamatanNAMA=nama,
                    kecamatanALAMAT=alamat,
                    kecamatanKET=keterangan,
                    datecreated=date_now,
                    usercreated=user
                )

                kecamatan_insert.save()
                messages.success(request, "✅ Anda berhasil input kecamatan baru!")
                return redirect('tambahkecamatan')
            except Exception as e:
                print(f"Error On Tambah Kecamatan: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat menambah kecamatan.")
                return redirect('tambahkecamatan')
            
        list_obj_kecamatan = kecamatan.objects.all().order_by("kecamatanKODE")
        list_obj_kabupaten = kabupaten.objects.all().order_by("kabupatenNAMA")
        return render(request, "admin/kecamatan.html", {
            "kecamatan": list_obj_kecamatan,
            "kabupaten": list_obj_kabupaten
        })

    @admin_required
    def GetEditKecamatanView(request, kecamatanKODE):
        list_obj_kecamatan = kecamatan.objects.all().order_by("kecamatanKODE")
        list_obj_kabupaten = kabupaten.objects.all().order_by("kabupatenNAMA")
        kecamatan_obj = kecamatan.objects.filter(kecamatanKODE = kecamatanKODE).first()

        if request.method == "POST":
            try:
                user_id = request.session.get("user_id")
                user = pengelola.objects.get(pengelolaKODE=user_id)

                date_now = timezone.now().date()
                
                kecamatan_obj.kecamatanNAMA = request.POST.get("nama")
                kecamatan_obj.kecamatanALAMAT = request.POST.get("alamat")
                kecamatan_obj.kecamatanKET = request.POST.get("keterangan")
                kecamatan_obj.dateupdated = date_now
                kecamatan_obj.userupdated = user

                kecamatan_obj.save()
                messages.success(request, "✅ Data kecamatan berhasil diupdate!")
                return redirect("tambahkecamatan")
            except Exception as e:
                print(f"Error On Edit Kecamatan: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat mengupdate kecamatan.")
                return redirect('editkecamatan', kecamatanKODE=kecamatanKODE)
        
        return render(request, "admin/kecamatan.html", {
            "kecamatan": list_obj_kecamatan,
            "kabupaten": list_obj_kabupaten,
            "edit_kec": kecamatan_obj,
        })

    @admin_required
    def GetDeleteKecamatanView(request, kecamatanKODE):
        list_obj_kecamatan = kecamatan.objects.all()
        list_obj_kabupaten = kabupaten.objects.all()
        kecamatan_obj = kecamatan.objects.filter(kecamatanKODE = kecamatanKODE).first()

        if request.method == "POST":
            try:
                kecamatan_obj.delete()
                messages.success(request, "🗑️ Data kecamatan berhasil dihapus!")
                return redirect('tambahkecamatan')
            except Exception as e:
                print(f"Error On Delete Kecamatan: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat menghapus kecamatan.")
                return redirect('tambahkecamatan')

        return render(request, "admin/kecamatan.html", {
            "kecamatan": list_obj_kecamatan,
            "kabupaten": list_obj_kabupaten,
            "delete_kec": kecamatan_obj,
        })
    
    #kategoriberita
    @admin_required
    def GetTambahKategoriberitaView(request):
        if request.method == "POST":
            kode = request.POST.get("kode")
            nama = request.POST.get("nama")
            keterangan = request.POST.get("keterangan")

            required_fields = {
                "Kode": kode,
                "Nama": nama,
                "Keterangan": keterangan
            }

            # Cek mana yang kosong
            missing = [key for key, value in required_fields.items() if not value or value.strip() == ""]

            if missing:
                messages.error(
                    request,
                    f"Silahkan isi kolom : {', '.join(missing)}."
                )
                return redirect("tambahkategoriwisata")


            kategoriberita_obj = kategoriberita(
                kategoriberitaKODE=kode,
                kategoriberitaNAMA=nama,
                kategoriberitaKET=keterangan,
            )
            kategoriberita_obj.save()
            messages.success(request, "✅ Data kategori berita berhasil disimpan!")
            return redirect("tambahkategoriberita")

        new_kode = kategoriberita.GenerateKode()
        list_obj_kategoriberita = kategoriberita.objects.all().order_by("kategoriberitaKODE")
        return render(request, "admin/kategoriberita.html", {
            "kategoriberita": list_obj_kategoriberita,
            'new_kode' : new_kode
        })

    @admin_required
    def GetEditKategoriberitaView(request, kategoriberitaKODE):
        list_obj_kategoriberita = kategoriberita.objects.all().order_by("kategoriberitaKODE")
        kategoriberita_obj = kategoriberita.objects.filter(kategoriberitaKODE = kategoriberitaKODE).first()

        if request.method == "POST":
            try:
                kategoriberita_obj.kategoriberitaNAMA = request.POST.get("nama")
                kategoriberita_obj.kategoriberitaKET = request.POST.get("keterangan")

                kategoriberita_obj.save()
                messages.success(request, "✅ Data kategori berita berhasil diupdate!")
                return redirect("tambahkategoriberita")
            except Exception as e:
                print(f"Error On Edit Kategori Berita: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat mengupdate kategori berita.")
                return redirect('editkategoriberita', kategoriberitaKODE=kategoriberitaKODE)
        
        return render(request, "admin/kategoriberita.html", {
            "kategoriberita": list_obj_kategoriberita,
            "edit_kategoriberita": kategoriberita_obj,
        })

    @admin_required
    def GetDeleteKategoriberitaView(request, kategoriberitaKODE):
        list_obj_kategoriberita = kategoriberita.objects.all()
        kategoriberita_obj = kategoriberita.objects.filter(kategoriberitaKODE = kategoriberitaKODE).first()

        if request.method == "POST":
            try:
                kategoriberita_obj.delete()
                messages.success(request, "🗑️ Data kategori berita berhasil dihapus!")
                return redirect('tambahkategoriberita')
            except Exception as e:
                print(f"Error On Delete Kategori Berita: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat menghapus kategori berita.")
                return redirect('tambahkategoriberita')

        return render(request, "admin/kategoriberita.html", {
            "kategoriberita": list_obj_kategoriberita,
            "delete_kategoriberita": kategoriberita_obj,
        })
    
    #kategoriwisata
    @admin_required
    def GetTambahKategoriwisataView(request):
        if request.method == "POST":
            kode = request.POST.get("kode")
            nama = request.POST.get("nama")
            keterangan = request.POST.get("keterangan")
            reference = request.POST.get("reference")

            required_fields = {
                "Kode": kode,
                "Nama": nama,
                "Keterangan": keterangan
            }

            # Cek mana yang kosong
            missing = [key for key, value in required_fields.items() if not value or value.strip() == ""]

            if missing:
                messages.error(
                    request,
                    f"Silahkan isi kolom : {', '.join(missing)}."
                )
                return redirect("tambahkategoriwisata")

            kategoriwisata_obj = kategoriwisata(
                kategoriwisataKODE=kode,
                kategoriwisataNAMA=nama,
                kategoriwisataKET=keterangan,
                kategoriREFERENCE=reference,
            )
            kategoriwisata_obj.save()
            messages.success(request, "✅ Data kategori wisata berhasil diupdate!")
            return redirect("tambahkategoriwisata")

        new_kode = kategoriwisata.GenerateKode()
        list_obj_kategoriwisata = kategoriwisata.objects.all().order_by("kategoriwisataKODE")
        return render(request, "admin/kategoriwisata.html", {
            "kategoriwisata": list_obj_kategoriwisata,
            "new_kode" : new_kode
        })

    @admin_required
    def GetEditKategoriwisataView(request, kategoriwisataKODE):
        list_obj_kategoriwisata = kategoriwisata.objects.all().order_by("kategoriwisataKODE")
        kategoriwisata_obj = kategoriwisata.objects.filter(kategoriwisataKODE = kategoriwisataKODE).first()

        if request.method == "POST":
            try:
                kategoriwisata_obj.kategoriwisataNAMA = request.POST.get("nama")
                kategoriwisata_obj.kategoriwisataKET = request.POST.get("keterangan")
                kategoriwisata_obj.kategoriREFERENCE = request.POST.get("reference")

                kategoriwisata_obj.save()
                messages.success(request, "✅ Data kategori wisata berhasil diupdate!")
                return redirect("tambahkategoriwisata")
            except Exception as e:
                print(f"Error On Edit Kategori Wisata: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat mengupdate kategori wisata.")
                return redirect('editkategoriwisata', kategoriwisataKODE=kategoriwisataKODE)
        
        return render(request, "admin/kategoriwisata.html", {
            "kategoriwisata": list_obj_kategoriwisata,
            "edit_kategoriwisata": kategoriwisata_obj,
        })

    @admin_required
    def GetDeleteKategoriwisataView(request, kategoriwisataKODE):
        list_obj_kategoriwisata = kategoriwisata.objects.all()
        kategoriwisata_obj = kategoriwisata.objects.filter(kategoriwisataKODE = kategoriwisataKODE).first()

        if request.method == "POST":
            try:
                kategoriwisata_obj.delete()
                messages.success(request, "🗑️ Data kategori wisata berhasil dihapus!")
                return redirect('tambahkategoriwisata')
            except Exception as e:
                print(f"Error On Delete Kategori Wisata: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat menghapus kategori wisata.")
                return redirect('tambahkategoriwisata')

        return render(request, "admin/kategoriwisata.html", {
            "kategoriwisata": list_obj_kategoriwisata,
            "delete_kategoriwisata": kategoriwisata_obj,
        })
    
    #kegiatan
    @admin_required
    def GetTambahKegiatanView(request):
        if request.method == "POST":
            kode = request.POST.get("kode")
            nama = request.POST.get("nama")
            kabupaten_kode = request.POST.get("kabupaten")
            keterangan = request.POST.get("keterangan")

            tanggal_mulai = request.POST.get("tanggal_mulai")
            tanggal_selesai = request.POST.get("tanggal_selesai")

            

            sumber = request.POST.get("sumber")
            poster_file = request.FILES.get("poster")

            required_fields = {
                "Kode": kode,
                "Nama": nama,
                "Kabupaten": kabupaten_kode,
                "Alamat": keterangan,
                "Tanggal Mulai": tanggal_mulai,
                "Tanggal Selesai": tanggal_selesai,
                "Sumber" : sumber
            }

            # Cek mana yang kosong
            missing = [key for key, value in required_fields.items() if not value or value.strip() == ""]

            if missing:
                messages.error(
                    request,
                    f"Silahkan isi kolom : {', '.join(missing)}."
                )
                return redirect("tambahkegiatan")
            
            mulai = datetime.strptime(tanggal_mulai, "%Y-%m-%d").date()
            selesai = datetime.strptime(tanggal_selesai, "%Y-%m-%d").date()
            # Cek apakah tanggal selesai lebih besar dari tanggal mulai
            if selesai <= mulai:
                messages.error(request, "Tanggal selesai harus setelah tanggal mulai.")
                return redirect("tambahkegiatan")
            
            # Get kabupaten object
            kabupaten_obj = None
            if kabupaten_kode:
                kabupaten_obj = kabupaten.objects.get(kabupatenKODE=kabupaten_kode)
            
            user_id = request.session.get("user_id")
            user = pengelola.objects.get(pengelolaKODE=user_id)

            date_now = timezone.now().date()

            poster_path = None
            file_name = None
            if poster_file:
                # folder simpan file
                upload_dir = os.path.join(settings.MEDIA_ROOT, "kegiatan")
                os.makedirs(upload_dir, exist_ok=True)

                # path file
                file_name = f"{kode}_{poster_file.name}"
                file_path = os.path.join(upload_dir, file_name)

                # simpan file fisik
                with open(file_path, "wb+") as dest:
                    for chunk in poster_file.chunks():
                        dest.write(chunk)

                # simpan path relatif (untuk database)
                poster_path = f"kegiatan/{file_name}"

            # Convert string dates to date objects
            event_mulai = None
            event_selesai = None
            if tanggal_mulai:
                event_mulai = datetime.strptime(tanggal_mulai, "%Y-%m-%d").date()
            if tanggal_selesai:
                event_selesai = datetime.strptime(tanggal_selesai, "%Y-%m-%d").date()

            kegiatan_obj = kegiatan(
                eventKODE=kode,
                eventNAMA=nama,
                kabupatenKODE=kabupaten_obj,
                eventKET=keterangan,
                eventMULAI=event_mulai,
                eventSELESAI=event_selesai,
                eventPOSTER=file_name,
                eventSUMBER=sumber,
                datecreated=date_now,
                usercreated=user
            )
            kegiatan_obj.save()
            messages.success(request, "✅ Data kegiatan berhasil ditambahkan!")
            return redirect("tambahkegiatan")

        # Generate kode otomatis
        new_kode = kegiatan.GenerateKode()
        list_obj_kegiatan = kegiatan.objects.all().order_by("eventKODE")
        list_obj_kabupaten = kabupaten.objects.all().order_by("kabupatenNAMA")
        return render(request, "admin/kegiatan.html", {
            "kegiatan": list_obj_kegiatan,
            "kabupaten": list_obj_kabupaten,
            'new_kode' : new_kode
        })

    @admin_required
    def GetEditKegiatanView(request, eventKODE):
        list_obj_kegiatan = kegiatan.objects.all().order_by("eventKODE")
        list_obj_kabupaten = kabupaten.objects.all().order_by("kabupatenNAMA")
        kegiatan_obj = kegiatan.objects.filter(eventKODE = eventKODE).first()

        if request.method == "POST":
            try:
                user_id = request.session.get("user_id")
                user = pengelola.objects.get(pengelolaKODE=user_id)

                date_now = timezone.now().date()
                
                kabupaten_kode = request.POST.get("kabupaten")
                kabupaten_obj = None
                if kabupaten_kode:
                    kabupaten_obj = kabupaten.objects.get(kabupatenKODE=kabupaten_kode)

                kegiatan_obj.eventNAMA = request.POST.get("nama")
                kegiatan_obj.kabupatenKODE = kabupaten_obj
                kegiatan_obj.eventKET = request.POST.get("keterangan")
                kegiatan_obj.eventSUMBER = request.POST.get("sumber")
                
                # Handle dates
                tanggal_mulai = request.POST.get("tanggal_mulai")
                tanggal_selesai = request.POST.get("tanggal_selesai")
                
                if tanggal_mulai:
                    kegiatan_obj.eventMULAI = datetime.strptime(tanggal_mulai, "%Y-%m-%d").date()
                else:
                    kegiatan_obj.eventMULAI = None
                    
                if tanggal_selesai:
                    kegiatan_obj.eventSELESAI = datetime.strptime(tanggal_selesai, "%Y-%m-%d").date()
                else:
                    kegiatan_obj.eventSELESAI = None

                # Handle poster upload
                poster = request.FILES.get("poster")
                if poster:
                    fs = FileSystemStorage(location='media/kegiatan')
                    filename = fs.save(poster.name, poster)
                    kegiatan_obj.eventPOSTER = filename

                kegiatan_obj.dateupdated = date_now
                kegiatan_obj.userupdated = user

                kegiatan_obj.save()
                messages.success(request, "✅ Data kegiatan berhasil diupdate!")
                return redirect("tambahkegiatan")
            except Exception as e:
                print(f"Error On Edit Kegiatan: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat mengupdate kegiatan.")
                return redirect('editkegiatan', eventKODE=eventKODE)
        
        return render(request, "admin/kegiatan.html", {
            "kegiatan": list_obj_kegiatan,
            "kabupaten": list_obj_kabupaten,
            "edit_kegiatan": kegiatan_obj,
        })

    @admin_required
    def GetDeleteKegiatanView(request, eventKODE):
        list_obj_kegiatan = kegiatan.objects.all()
        list_obj_kabupaten = kabupaten.objects.all()
        kegiatan_obj = kegiatan.objects.filter(eventKODE = eventKODE).first()

        if request.method == "POST":
            try:
                kegiatan_obj.delete()
                messages.success(request, "🗑️ Data kegiatan berhasil dihapus!")
                return redirect('tambahkegiatan')
            except Exception as e:
                print(f"Error On Delete Kegiatan: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat menghapus kegiatan.")
                return redirect('tambahkegiatan')

        return render(request, "admin/kegiatan.html", {
            "kegiatan": list_obj_kegiatan,
            "kabupaten": list_obj_kabupaten,
            "delete_kegiatan": kegiatan_obj,
        })

    #obyekwisata
    @admin_required
    def GetTambahObyekWisataView(request):
        if request.method == "POST":
            kode = request.POST.get("kode")
            nama = request.POST.get("nama")
            kecamatan_kode = request.POST.get("kecamatan")
            kategori_kode = request.POST.get("kategori")
            alamat = request.POST.get("alamat")
            latitude = request.POST.get("latitude")
            longitude = request.POST.get("longitude")
            popularitas = request.POST.get("popularitas")

            required_fields = {
                "Kode": kode,
                "Nama": nama,
                "Kecamatan": kecamatan_kode,
                "Kategori": kategori_kode,
                "Alamat": alamat,
                "Latitude": latitude,
                "Longitude": longitude,
                "Popularitas" : popularitas
            }

            # Cek mana yang kosong
            missing = [key for key, value in required_fields.items() if not value or value.strip() == ""]

            if missing:
                messages.error(
                    request,
                    f"Silahkan isi kolom : {', '.join(missing)}."
                )
                return redirect("tambahobyekwisata")

            # Cek apakah masih dalam rentang valid koordinat bumi
            if not (-90 <= float(latitude) <= 90):
                messages.error(request, "Latitude harus berada di antara -90 hingga 90 derajat.")
                return redirect("tambahobyekwisata")

            if not (-180 <= float(longitude) <= 180):
                messages.error(request, "Longitude harus berada di antara -180 hingga 180 derajat.")
                return redirect("tambahobyekwisata")
            
            jam_buka = request.POST.get("jam_buka")
            jam_tutup = request.POST.get("jam_tutup")

            # Cek apakah jam tutup lebih besar dari jam buka
            buka = datetime.strptime(jam_buka, "%H:%M").time()
            tutup = datetime.strptime(jam_tutup, "%H:%M").time()
            if tutup <= buka:
                messages.error(request, "Jam tutup harus lebih lambat dari jam buka.")
                return redirect("tambahobyekwisata")
                    
            definisi = request.POST.get("definisi")
            keterangan = request.POST.get("keterangan")
            foto_file = request.FILES.get("foto")
            
            # derajat_s, menit_s, detik_s, derajat_e, menit_e, detik_e = obyekwisata.get_derajat(latitude=latitude, longtitude=longitude)

            # Get foreign key objects
            kecamatan_obj = None
            if kecamatan_kode:
                kecamatan_obj = kecamatan.objects.get(kecamatanKODE=kecamatan_kode)

                kode = kecamatan_obj.kecamatanKODE +'-' +str(kode)
            
            kategori_obj = None
            if kategori_kode:
                kategori_obj = kategoriwisata.objects.get(kategoriwisataKODE=kategori_kode)
            
            user_id = request.session.get("user_id")
            user = pengelola.objects.get(pengelolaKODE=user_id)

            date_now = timezone.now().date()

            # Handle photo upload
            foto_path = None
            file_name = None
            if foto_file:
                upload_dir = os.path.join(settings.MEDIA_ROOT, "obyekwisata")
                os.makedirs(upload_dir, exist_ok=True)

                file_name = f"{kode}_{foto_file.name}"
                file_path = os.path.join(upload_dir, file_name)

                with open(file_path, "wb+") as dest:
                    for chunk in foto_file.chunks():
                        dest.write(chunk)
            # Handle time fields
            obyek_jam_buka = None
            obyek_jam_tutup = None
            if jam_buka:
                obyek_jam_buka = datetime.strptime(jam_buka, "%H:%M").time()
            if jam_tutup:
                obyek_jam_tutup = datetime.strptime(jam_tutup, "%H:%M").time()

            # Convert numeric fields
            obyek_latitude = None
            obyek_longitude = None
            obyek_popularitas = None

            if latitude:
                obyek_latitude = float(latitude)
            if longitude:
                obyek_longitude = float(longitude)
            if popularitas:
                obyek_popularitas = int(popularitas)
            
            waktu_kunjung = kategoriwisata.GetWaktuKunjung(kategoriwisataNAMA=kategori_obj.kategoriwisataNAMA)

            # Create the object
            obyekwisata_obj = obyekwisata(
                obyekKODE=kode,
                obyekNAMA=nama,
                obyekWAKTUKUNJUNG = waktu_kunjung,
                kecamatanKODE=kecamatan_obj,
                kategoriKODE=kategori_obj,
                obyekALAMAT=alamat,
                obyekLATITUDE=obyek_latitude,
                obyekLONGITUDE=obyek_longitude,
                obyekJAMBUKA=obyek_jam_buka,
                obyekJAMTUTUP=obyek_jam_tutup,
                obyekPOPULARITAS=obyek_popularitas,
                obyekDEFINISI=definisi,
                obyekKETERANGAN=keterangan,
                obyekFOTO=file_name,
                datecreated=date_now,
                usercreated=user
            )
            obyekwisata_obj.save()
            messages.success(request, "✅ Data obyek wisata berhasil ditambahkan!")
            return redirect("tambahobyekwisata")

        list_obj_obyekwisata = obyekwisata.objects.all().order_by("obyekKODE")
        list_obj_kategori = kategoriwisata.objects.all().order_by("kategoriwisataNAMA")
        list_obj_kecamatan = kecamatan.objects.all().order_by("kecamatanNAMA")
        
        return render(request, "admin/obyekwisata.html", {
            "obyekwisata": list_obj_obyekwisata,
            "kecamatan": list_obj_kecamatan,
            "kategoriwisata": list_obj_kategori
        })

    @admin_required
    def SyncObyekWisata(request):
        if request.method == "POST":
            file_excel = request.FILES.get('excel_file')
            date_now = timezone.now().date()

            if file_excel:
                 # simpan ke folder media/obyekwisata/
                fs = FileSystemStorage(location="media/obyekwisata")
                filename = f"{date_now}_{file_excel.name}"  # contoh: 20250916203000_data.xlsx
                
                # cek apakah file dengan nama itu sudah ada
                if fs.exists(filename):
                    # langsung ambil path & url tanpa upload ulang
                    saved_path = filename
                    print("⚠️ File sudah ada, tidak diupload ulang.")
                else:
                    # upload baru
                    saved_path = fs.save(filename, file_excel)
                    print("✅ File berhasil diupload.")

                # path lengkap di server (untuk pandas)
                full_path = fs.path(saved_path)

                # url untuk akses via browser
                file_url = fs.url(saved_path)
                
                user_id = request.session.get("user_id")
                user = pengelola.objects.get(pengelolaKODE=user_id)
                created_obyekwisata, updated_obyekwisata, created_jarakobyek, updated_jarakobyek = sync_excel(file_path = full_path, user=user)

                # kasih notifikasi ke user
                messages.success(
                    request,
                    f"✅ Sinkronisasi selesai! "
                    f"{created_obyekwisata}, {updated_obyekwisata}, "
                    f"{created_jarakobyek}, {updated_jarakobyek}"
                )
                return redirect("tambahobyekwisata")
            else:
                messages.error(request, "❌ Tidak ada file yang diupload.")
                return redirect("tambahobyekwisata")
            
    @admin_required
    def GetEditObyekWisataView(request, obyekKODE):
        list_obj_obyekwisata = obyekwisata.objects.all().order_by("obyekKODE")
        list_obj_kecamatan = kecamatan.objects.all().order_by("kecamatanNAMA")
        list_obj_kategori = kategoriwisata.objects.all().order_by("kategoriwisataNAMA")
        obyekwisata_obj = obyekwisata.objects.filter(obyekKODE=obyekKODE).first()

        if request.method == "POST":
            try:
                user_id = request.session.get("user_id")
                user = pengelola.objects.get(pengelolaKODE=user_id)
                date_now = timezone.now().date()

                kategori_kode = request.POST.get("kategori")
                kategori_obj = None
                if kategori_kode:
                    kategori_obj = kategoriwisata.objects.get(kategoriwisataKODE=kategori_kode)

                # Update basic fields
                obyekwisata_obj.obyekNAMA = request.POST.get("nama")
                obyekwisata_obj.kategoriKODE = kategori_obj
                obyekwisata_obj.obyekALAMAT = request.POST.get("alamat")
                obyekwisata_obj.obyekDEFINISI = request.POST.get("definisi")
                obyekwisata_obj.obyekKETERANGAN = request.POST.get("keterangan")

                # Handle numeric fields
                latitude = request.POST.get("latitude")
                longitude = request.POST.get("longitude")
                ketinggian = request.POST.get("ketinggian")
                popularitas = request.POST.get("popularitas")

                if latitude:
                    obyekwisata_obj.obyekLATITUDE = float(latitude)
                else:
                    obyekwisata_obj.obyekLATITUDE = None

                if longitude:
                    obyekwisata_obj.obyekLONGITUDE = float(longitude)
                else:
                    obyekwisata_obj.obyekLONGITUDE = None

                if ketinggian:
                    obyekwisata_obj.obyekKETINGGIAN = int(ketinggian)
                else:
                    obyekwisata_obj.obyekKETINGGIAN = None

                if popularitas:
                    obyekwisata_obj.obyekPOPULARITAS = int(popularitas)
                else:
                    obyekwisata_obj.obyekPOPULARITAS = None

                # Handle time fields
                jam_buka = request.POST.get("jam_buka")
                jam_tutup = request.POST.get("jam_tutup")
                
                if jam_buka:
                    obyekwisata_obj.obyekJAMBUKA = datetime.strptime(jam_buka, "%H:%M").time()
                else:
                    obyekwisata_obj.obyekJAMBUKA = None
                    
                if jam_tutup:
                    obyekwisata_obj.obyekJAMTUTUP = datetime.strptime(jam_tutup, "%H:%M").time()
                else:
                    obyekwisata_obj.obyekJAMTUTUP = None

                # Handle foto upload
                foto = request.FILES.get("foto")
                if foto:
                    upload_dir = os.path.join(settings.MEDIA_ROOT, "obyekwisata")
                    os.makedirs(upload_dir, exist_ok=True)

                    file_name = f"{obyekKODE}_{foto.name}"
                    file_path = os.path.join(upload_dir, file_name)

                    with open(file_path, "wb+") as dest:
                        for chunk in foto.chunks():
                            dest.write(chunk)

                    obyekwisata_obj.obyekFOTO = f"obyekwisata/{file_name}"

                obyekwisata_obj.dateupdated = date_now
                obyekwisata_obj.userupdated = user

                obyekwisata_obj.save()
                messages.success(request, "✅ Data obyek wisata berhasil diupdate!")
                return redirect("tambahobyekwisata")
            except Exception as e:
                print(f"Error On Edit Obyek Wisata: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat mengupdate obyek wisata.")
                return redirect('editobyekwisata', obyekKODE=obyekKODE)
        
        return render(request, "admin/obyekwisata.html", {
            "obyekwisata": list_obj_obyekwisata,
            "kecamatan": list_obj_kecamatan,
            "kategoriwisata": list_obj_kategori,
            "edit_obyekwisata": obyekwisata_obj,
        })

    @admin_required
    def GetDeleteObyekWisataView(request, obyekKODE):
        list_obj_obyekwisata = obyekwisata.objects.all()
        list_obj_kecamatan = kecamatan.objects.all()
        list_obj_kategori = kategoriwisata.objects.all()
        obyekwisata_obj = obyekwisata.objects.filter(obyekKODE=obyekKODE).first()

        if request.method == "POST":
            try:
                # Delete associated photo file if exists
                if obyekwisata_obj.obyekFOTO:
                    foto_path = os.path.join(settings.MEDIA_ROOT, obyekwisata_obj.obyekFOTO)
                    if os.path.exists(foto_path):
                        os.remove(foto_path)
                
                obyekwisata_obj.delete()
                messages.success(request, "🗑️ Data obyek wisata berhasil dihapus!")
                return redirect('tambahobyekwisata')
            except Exception as e:
                print(f"Error On Delete Obyek Wisata: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat menghapus obyek wisata.")
                return redirect('tambahobyekwisata')

        return render(request, "admin/obyekwisata.html", {
            "obyekwisata": list_obj_obyekwisata,
            "kecamatan": list_obj_kecamatan,
            "kategoriwisata": list_obj_kategori,
            "delete_obyekwisata": obyekwisata_obj,
        })
    
    @admin_required
    def GetTambahJarakObyekView(request):
        if request.method == "POST":
            ruteKODE = request.POST.get("ruteKODE")
            obyekKODEasal = request.POST.get("obyekKODEasal")
            obyekKODEtujuan = request.POST.get("obyekKODEtujuan")
            obyektempuh = request.POST.get("obyektempuh")
            obyekrute = request.POST.get("obyekrute")

            required_fields = {
                "Kode": ruteKODE,
                "Obyek Asal": obyekKODEasal,
                "Obyek Tujuan": obyekKODEtujuan,
                "Waktu Tempuh": obyektempuh,
                "Jarak Tempuh": obyekrute
            }

            # Cek field yang kosong
            missing = [key for key, value in required_fields.items() if not value or str(value).strip() == ""]

            if missing:
                messages.error(
                    request,
                    f"Silahkan isi kolom : {', '.join(missing)}."
                )
                return redirect("tambahjarakobyek")

            # Validasi obyek asal dan tujuan tidak boleh sama
            if obyekKODEasal == obyekKODEtujuan:
                messages.error(request, "Obyek asal dan tujuan tidak boleh sama.")
                return redirect("tambahjarakobyek")

            # Validasi waktu tempuh harus positif
            if int(obyektempuh) <= 0:
                messages.error(request, "Waktu tempuh harus lebih dari 0 menit.")
                return redirect("tambahjarakobyek")

            # Get foreign key objects
            obyek_asal = obyekwisata.objects.get(obyekKODE=obyekKODEasal)
            obyek_tujuan = obyekwisata.objects.get(obyekKODE=obyekKODEtujuan)

            # Create the object
            jarakobyek_obj = jarakobyek(
                ruteKODE=ruteKODE,
                obyekKODEasal=obyek_asal,
                obyekKODEtujuan=obyek_tujuan,
                obyektempuh=int(obyektempuh),
                obyekrute=obyekrute,
            )
            jarakobyek_obj.save()
            messages.success(request, "✅ Data jarak obyek berhasil ditambahkan!")
            return redirect("tambahjarakobyek")
        
        list_obj_jarakobyek = jarakobyek.objects.all().order_by("ruteKODE")
        paginator = Paginator(list_obj_jarakobyek, 10)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        list_obj_obyekwisata = obyekwisata.objects.all().order_by("obyekNAMA")
        new_kode = jarakobyek.GenerateKode()

        return render(request, "admin/jarakobyek.html", {
            "page_obj": page_obj,
            'list_obj_jarakobyek': list_obj_jarakobyek,
            'list_obj_obyekwisata': list_obj_obyekwisata,
            "new_kode": new_kode
        })

    @admin_required
    def GetEditJarakObyekView(request, ruteKODE):
        jarakobyek_obj = jarakobyek.objects.filter(ruteKODE=ruteKODE).first()

        if request.method == "POST":
            try:
                obyekKODEasal = request.POST.get("obyekKODEasal")
                obyekKODEtujuan = request.POST.get("obyekKODEtujuan")
                obyektempuh = request.POST.get("obyektempuh")
                obyekrute = request.POST.get("obyekrute")

                # Validasi obyek asal dan tujuan tidak boleh sama
                if obyekKODEasal == obyekKODEtujuan:
                    messages.error(request, "Obyek asal dan tujuan tidak boleh sama.")
                    return redirect('editjarakobyek', ruteKODE=ruteKODE)

                # Update fields
                if obyekKODEasal:
                    jarakobyek_obj.obyekKODEasal = obyekwisata.objects.get(obyekKODE=obyekKODEasal)
                
                if obyekKODEtujuan:
                    jarakobyek_obj.obyekKODEtujuan = obyekwisata.objects.get(obyekKODE=obyekKODEtujuan)

                if obyektempuh:
                    jarakobyek_obj.obyektempuh = int(obyektempuh)

                if obyekrute:
                    jarakobyek_obj.obyekrute = obyekrute

                jarakobyek_obj.save()
                messages.success(request, "✅ Data jarak obyek berhasil diupdate!")
                return redirect("tambahjarakobyek")
            except Exception as e:
                print(f"Error On Edit Jarak Obyek: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat mengupdate jarak obyek.")
                return redirect('editjarakobyek', ruteKODE=ruteKODE)
        
        list_obj_jarakobyek = jarakobyek.objects.all().order_by("ruteKODE")
        paginator = Paginator(list_obj_jarakobyek, 10)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        list_obj_obyekwisata = obyekwisata.objects.all().order_by("obyekNAMA")
        new_kode = jarakobyek.GenerateKode()
        
        return render(request, "admin/jarakobyek.html", {
            "page_obj": page_obj,
            'list_obj_jarakobyek': list_obj_jarakobyek,
            'list_obj_obyekwisata': list_obj_obyekwisata,
            'new_kode': new_kode,
            'edit_jarakobyek': jarakobyek_obj,
        })


    @admin_required
    def GetDeleteJarakObyekView(request, ruteKODE):
        jarakobyek_obj = jarakobyek.objects.filter(ruteKODE=ruteKODE).first()

        if request.method == "POST":
            try:
                jarakobyek_obj.delete()
                messages.success(request, "🗑️ Data jarak obyek berhasil dihapus!")
                return redirect('tambahjarakobyek')
            except Exception as e:
                print(f"Error On Delete Jarak Obyek: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat menghapus jarak obyek.")
                return redirect('tambahjarakobyek')

        list_obj_jarakobyek = jarakobyek.objects.all().order_by("ruteKODE")
        paginator = Paginator(list_obj_jarakobyek, 10)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        list_obj_obyekwisata = obyekwisata.objects.all().order_by("obyekNAMA")
        new_kode = jarakobyek.GenerateKode()
        
        return render(request, "admin/jarakobyek.html", {
            "page_obj": page_obj,
            'list_obj_jarakobyek': list_obj_jarakobyek,
            'list_obj_obyekwisata': list_obj_obyekwisata,
            'new_kode': new_kode,
            'delete_jarakobyek': jarakobyek_obj,
        })
        

    #berita
    @admin_required
    def GetTambahBeritaView(request):
        if request.method == "POST":
            kode = request.POST.get("kode")
            judul = request.POST.get("judul")
            kategori_kode = request.POST.get("kategori")
            kegiatan_kode = request.POST.get("kegiatan")
            obyek_kode = request.POST.get("obyek")
            kabupaten_kode = request.POST.get("kabupaten")
            penulis = request.POST.get("penulis")
            tanggal = request.POST.get("tanggal")
            sumber = request.POST.get("sumber")
            isi = request.POST.get("isi")
            isi2 = request.POST.get("isi2")
            foto_file = request.FILES.get("foto")

            required_fields = {
                "Kode": kode,
                "Judul": judul,
                "Kategori": kategori_kode,
                'Tanggal' : tanggal,
                'Isi' : isi
            }

            # Cek mana yang kosong
            missing = [key for key, value in required_fields.items() if not value or value.strip() == ""]

            if missing:
                messages.error(
                    request,
                    f"Silahkan isi kolom : {', '.join(missing)}."
                )
                return redirect("tambahobyekwisata")
            
            # Get foreign key objects
            kategori_obj = None
            if kategori_kode:
                kategori_obj = kategoriberita.objects.get(kategoriberitaKODE=kategori_kode)
            
            kegiatan_obj = None
            if kegiatan_kode:
                kegiatan_obj = kegiatan.objects.get(eventKODE=kegiatan_kode)
            
            obyek_obj = None
            if obyek_kode:
                obyek_obj = obyekwisata.objects.get(obyekKODE=obyek_kode)
            
            kabupaten_obj = None
            if kabupaten_kode:
                kabupaten_obj = kabupaten.objects.get(kabupatenKODE=kabupaten_kode)
            
            user_id = request.session.get("user_id")
            user = pengelola.objects.get(pengelolaKODE=user_id)

            date_now = timezone.now().date()

            foto_path = None
            file_name = None
            if foto_file:
                # folder simpan file
                upload_dir = os.path.join(settings.MEDIA_ROOT, "berita")
                os.makedirs(upload_dir, exist_ok=True)

                # path file
                file_name = f"{kode}_{foto_file.name}"
                file_path = os.path.join(upload_dir, file_name)

                # simpan file fisik
                with open(file_path, "wb+") as dest:
                    for chunk in foto_file.chunks():
                        dest.write(chunk)

                # simpan path relatif (untuk database)
                foto_path = f"berita/{file_name}"

            # Convert string date to date object
            berita_tanggal = None
            if tanggal:
                berita_tanggal = datetime.strptime(tanggal, "%Y-%m-%d").date()

            berita_obj = berita(
                beritaKODE=kode,
                beritaJUDUL=judul,
                kategoriberitaKODE=kategori_obj,
                eventKODE=kegiatan_obj,
                obyekKODE=obyek_obj,
                kabupatenKODE=kabupaten_obj,
                beritaISI=isi,
                beritaISI2=isi2,
                beritaSUMBER=sumber,
                beritaPENULIS=penulis,
                beritaTGL=berita_tanggal,
                beritaICONFOTO=file_name,
                datecreated=date_now,
                usercreated=user
            )
            berita_obj.save()
            messages.success(request, "✅ Data berita berhasil ditambahkan!")
            return redirect("tambahberita")

        new_kode = berita.GenerateKode()
        list_obj_berita = berita.objects.all().order_by("beritaKODE")
        list_obj_kategori = kategoriberita.objects.all().order_by("kategoriberitaNAMA")
        list_obj_kegiatan = kegiatan.objects.all().order_by("eventNAMA")
        list_obj_obyekwisata = obyekwisata.objects.all().order_by("obyekNAMA")
        list_obj_kabupaten = kabupaten.objects.all().order_by("kabupatenNAMA")
        
        return render(request, "admin/berita.html", {
            "berita": list_obj_berita,
            "kategoriberita": list_obj_kategori,
            "kegiatan": list_obj_kegiatan,
            "obyekwisata": list_obj_obyekwisata,
            "kabupaten": list_obj_kabupaten,
            "new_kode":new_kode
        })

    @admin_required
    def GetEditBeritaView(request, beritaKODE):
        list_obj_berita = berita.objects.all().order_by("beritaKODE")
        list_obj_kategori = kategoriberita.objects.all().order_by("kategoriberitaNAMA")
        list_obj_kegiatan = kegiatan.objects.all().order_by("eventNAMA")
        list_obj_obyekwisata = obyekwisata.objects.all().order_by("obyekNAMA")
        list_obj_kabupaten = kabupaten.objects.all().order_by("kabupatenNAMA")
        berita_obj = berita.objects.filter(beritaKODE = beritaKODE).first()

        if request.method == "POST":
            try:
                user_id = request.session.get("user_id")
                user = pengelola.objects.get(pengelolaKODE=user_id)

                date_now = timezone.now().date()
                
                # Get foreign key objects
                kategori_kode = request.POST.get("kategori")
                kategori_obj = None
                if kategori_kode:
                    kategori_obj = kategoriberita.objects.get(kategoriberitaKODE=kategori_kode)

                kegiatan_kode = request.POST.get("kegiatan")
                kegiatan_obj = None
                if kegiatan_kode:
                    kegiatan_obj = kegiatan.objects.get(eventKODE=kegiatan_kode)

                obyek_kode = request.POST.get("obyek")
                obyek_obj = None
                if obyek_kode:
                    obyek_obj = obyekwisata.objects.get(obyekKODE=obyek_kode)

                kabupaten_kode = request.POST.get("kabupaten")
                kabupaten_obj = None
                if kabupaten_kode:
                    kabupaten_obj = kabupaten.objects.get(kabupatenKODE=kabupaten_kode)

                berita_obj.beritaJUDUL = request.POST.get("judul")
                berita_obj.kategoriberitaKODE = kategori_obj
                berita_obj.eventKODE = kegiatan_obj
                berita_obj.obyekKODE = obyek_obj
                berita_obj.kabupatenKODE = kabupaten_obj
                berita_obj.beritaISI = request.POST.get("isi")
                berita_obj.beritaISI2 = request.POST.get("isi2")
                berita_obj.beritaSUMBER = request.POST.get("sumber")
                berita_obj.beritaPENULIS = request.POST.get("penulis")
                
                # Handle date
                tanggal = request.POST.get("tanggal")
                if tanggal:
                    berita_obj.beritaTGL = datetime.strptime(tanggal, "%Y-%m-%d").date()
                else:
                    berita_obj.beritaTGL = None

                # Handle foto upload
                foto = request.FILES.get("foto")
                if foto:
                    upload_dir = os.path.join(settings.MEDIA_ROOT, "berita")
                    os.makedirs(upload_dir, exist_ok=True)

                    file_name = f"{beritaKODE}_{foto.name}"
                    file_path = os.path.join(upload_dir, file_name)

                    with open(file_path, "wb+") as dest:
                        for chunk in foto.chunks():
                            dest.write(chunk)

                    berita_obj.beritaICONFOTO = file_name

                berita_obj.dateupdated = date_now
                berita_obj.userupdated = user

                berita_obj.save()
                messages.success(request, "✅ Data berita berhasil diupdate!")
                return redirect("tambahberita")
            except Exception as e:
                print(f"Error On Edit Berita: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat mengupdate berita.")
                return redirect('editberita', beritaKODE=beritaKODE)
        
        return render(request, "admin/berita.html", {
            "berita": list_obj_berita,
            "kategoriberita": list_obj_kategori,
            "kegiatan": list_obj_kegiatan,
            "obyekwisata": list_obj_obyekwisata,
            "kabupaten": list_obj_kabupaten,
            "edit_berita": berita_obj,
        })

    @admin_required
    def GetDeleteBeritaView(request, beritaKODE):
        list_obj_berita = berita.objects.all()
        list_obj_kategori = kategoriberita.objects.all()
        list_obj_kegiatan = kegiatan.objects.all()
        list_obj_obyekwisata = obyekwisata  .objects.all()
        list_obj_kabupaten = kabupaten.objects.all()
        berita_obj = berita.objects.filter(beritaKODE = beritaKODE).first()

        if request.method == "POST":
            try:
                # Delete associated photo file if exists
                if berita_obj.beritaICONFOTO:
                    foto_path = os.path.join(settings.MEDIA_ROOT, berita_obj.beritaICONFOTO)
                    if os.path.exists(foto_path):
                        os.remove(foto_path)
                        
                berita_obj.delete()
                messages.success(request, "🗑️ Data berita berhasil dihapus!")
                return redirect('tambahberita')
            except Exception as e:
                print(f"Error On Delete Berita: {e}")
                messages.error(request, "❌ Terjadi kesalahan saat menghapus berita.")
                return redirect('tambahberita')

        return render(request, "admin/berita.html", {
            "berita": list_obj_berita,
            "kategoriberita": list_obj_kategori,
            "kegiatan": list_obj_kegiatan,
            "obyekwisata": list_obj_obyekwisata,
            "kabupaten": list_obj_kabupaten,
            "delete_berita": berita_obj,
        })