from datetime import time
import pandas as pd
from django.utils import timezone
from app.models import jarakobyek, kategoriwisata, kecamatan, obyekwisata


def sync_excel(file_path, user):
    # Default values
    created_obyekwisata = "Created ObyekWisata 0"
    updated_obyekwisata = "Updated ObyekWisata 0"
    created_jarakobyek = "Created JarakObyek 0"
    updated_jarakobyek = "Updated JarakObyek 0"

    excel_data = pd.ExcelFile(file_path)

    # ================= Sheet 1: obyekwisata =================
    if "obyekwisata" in excel_data.sheet_names:
        df_wisata = pd.read_excel(excel_data, sheet_name="obyekwisata")

        dict_kecamatan = {data.kecamatanNAMA: data for data in kecamatan.objects.all()}
        dict_kategori = {data.kategoriwisataNAMA: data for data in kategoriwisata.objects.all()}

        dict_existing_obyek = {data.obyekKODE: data for data in obyekwisata.objects.all()}

        list_create = []
        list_update = []

        for _, row in df_wisata.iterrows():
            obyek_kode = row["obyekKODE"]   # pastikan kolom excel ada "kode"
            nama = row["obyekNAMA"]
            nama_formatted = nama.replace(" ", "")
            url_foto = nama_formatted+'.jpg'

            row_kategori = row.get("obyekKATEGORI")

            kecamatan_object = dict_kecamatan.get(row.get("kecamatan"))
            kategori_object = dict_kategori.get(row_kategori)

            date_now = timezone.now().date()

            lat = row.get("obyekLATITUDE") or None
            lon = row.get("obyekLONGITUDE") or None

           # Default None kalau lat/lon kosong
            if lat is not None:
                lat_abs = abs(lat)
                derajat_s = int(lat_abs)
                menit_s = int((lat_abs - derajat_s) * 60)
                detik_s = round((lat_abs - derajat_s - menit_s/60) * 3600, 2)
            else:
                derajat_s = menit_s = detik_s = None

            if lon is not None:
                lon_abs = abs(lon)
                derajat_e = int(lon_abs)
                menit_e = int((lon_abs - derajat_e) * 60)
                detik_e = round((lon_abs - derajat_e - menit_e/60) * 3600, 2)
            else:
                derajat_e = menit_e = detik_e = None


            if obyek_kode in dict_existing_obyek:
                obj = dict_existing_obyek[obyek_kode]
                obj.obyekFOTO = url_foto
                obj.kecamatanKODE = kecamatan_object
                obj.kategoriKODE = kategori_object
                obj.obyekNAMA = row.get("obyekNAMA") or None
                obj.obyekALAMAT = row.get("obyekALAMAT") or None
                obj.obyekDERAJAT_S = derajat_s
                obj.obyekMENIT_S = menit_s
                obj.obyekDETIK_S = detik_s
                obj.obyekLATITUDE = row.get("obyekLATITUDE") or None
                obj.obyekDERAJAT_E = derajat_e
                obj.obyekMENIT_E = menit_e
                obj.obyekDETIK_E = detik_e
                obj.obyekLONGITUDE = row.get("obyekLONGITUDE") or None
                obj.obyekKETINGGIAN = row.get("obyekKETINGGIAN") or None
                obj.obyekJAMBUKA = (
                    time(int(row.get("obyekJAMBUKA")), int((row.get("obyekJAMBUKA") % 1) * 60))
                    if row.get("obyekJAMBUKA") is not None else None
                )

                obj.obyekJAMTUTUP = (
                    time(int(row.get("obyekJAMTUTUP")), int((row.get("obyekJAMTUTUP") % 1) * 60))
                    if row.get("obyekJAMTUTUP") is not None else None
                )
                obj.obyekWAKTUKUNJUNG = kategoriwisata.GetWaktuKunjung(kategoriwisataNAMA=row_kategori)
                obj.obyekPOPULARITAS = (
                        int(round(float(str(row.get("obyekPOPULARITAS")).replace(",", "."))))
                        if row.get("obyekPOPULARITAS") not in (None, "") else None
                )
                obj.obyekKEMUDAHAN = (
                    int(round(float(str(row.get("obyekKEMUDAHAN")).replace(",", "."))))
                    if row.get("obyekKEMUDAHAN") not in (None, "") else None
                )
                obj.obyekDEFINISI = row.get("obyekDEFINISI") or None
                obj.obyekKETERANGAN = row.get("obyekKETERANGAN") or None
                obj.dateupdated = date_now
                obj.userupdated = user

                list_update.append(obj)
            else:
                obj = obyekwisata(
                    obyekKODE=obyek_kode,
                    kecamatanKODE = kecamatan_object,   
                    kategoriKODE = kategori_object,
                    obyekNAMA=row.get("obyekNAMA") or None,
                    obyekALAMAT=row.get("obyekALAMAT") or None,
                    obyekDERAJAT_S=derajat_s,
                    obyekMENIT_S=menit_s,
                    obyekDETIK_S=detik_s,
                    obyekLATITUDE=row.get("obyekLATITUDE") or None,
                    obyekDERAJAT_E=derajat_e,
                    obyekMENIT_E=menit_e,
                    obyekDETIK_E=detik_e,
                    obyekLONGITUDE=row.get("obyekLONGITUDE") or None,
                    obyekKETINGGIAN=row.get("obyekKETINGGIAN") or None,
                    obyekJAMBUKA = (
                        time(int(row.get("obyekJAMBUKA")), int((row.get("obyekJAMBUKA") % 1) * 60))
                        if row.get("obyekJAMBUKA") is not None else None
                    ),

                    obyekJAMTUTUP = (
                        time(int(row.get("obyekJAMTUTUP")), int((row.get("obyekJAMTUTUP") % 1) * 60))
                        if row.get("obyekJAMTUTUP") is not None else None
                    ),
                    obyekWAKTUKUNJUNG=row.get("obyekWAKTUKUNJUNG") or None,
                    obyekPOPULARITAS = (
                        int(round(float(str(row.get("obyekPOPULARITAS")).replace(",", "."))))
                        if row.get("obyekPOPULARITAS") not in (None, "") else None
                    ),
                    obyekKEMUDAHAN = (
                        int(round(float(str(row.get("obyekKEMUDAHAN")).replace(",", "."))))
                        if row.get("obyekKEMUDAHAN") not in (None, "") else None
                    ),
                    obyekDEFINISI=row.get("obyekDEFINISI") or None,
                    obyekKETERANGAN=row.get("obyekKETERANGAN") or None,
                    obyekFOTO = url_foto,
                    datecreated=date_now,
                    usercreated=user
                )
                
                list_create.append(obj)
        # Simpan sekaligus
        if list_update:
            obyekwisata.objects.bulk_update(list_update,
                ["obyekNAMA", "obyekALAMAT", "obyekDERAJAT_S", "obyekMENIT_S", "obyekDETIK_S",
                    "obyekLATITUDE", "obyekDERAJAT_E","obyekMENIT_E","obyekDETIK_E","obyekLONGITUDE",
                    "obyekKETINGGIAN", "obyekJAMBUKA","obyekJAMTUTUP","obyekWAKTUKUNJUNG","obyekKEMUDAHAN","obyekDEFINISI",
                    "obyekKETERANGAN","dateupdated", "obyekFOTO","userupdated", "obyekPOPULARITAS"
                ],
            )
            print(f"Updated ObyekWisata {len(list_update)}")
            updated_obyekwisata = f"Updated ObyekWisata {len(list_update)}"

        if list_create:
            obyekwisata.objects.bulk_create(list_create)
            print(f"Created ObyekWisata {len(list_create)}")
            created_obyekwisata = f"Created ObyekWisata {len(list_create)}"

    # ================= Sheet 2: jarakobyek =================
    if "jarakobyek" in excel_data.sheet_names:
        df_jarak = pd.read_excel(excel_data, sheet_name="jarakobyek")

        # Dict obyekwisata untuk foreign key lookup
        dict_obyek = {data.obyekKODE: data for data in obyekwisata.objects.all()}

        dict_existing_jarak = {
            (str(data.obyekKODEasal.obyekKODE), str(data.obyekKODEtujuan.obyekKODE)): data
            for data in jarakobyek.objects.all()
        }

        
        list_create_jarak = []
        list_update_jarak = []
        date_now = timezone.now().date()

        for _, row in df_jarak.iterrows():
            ruteKODE = row.get("ruteKODE")
            kode_asal = str(row.get("obyekKODEASAL"))
            kode_tujuan = str(row.get("obyekKODETUJUAN"))

            waktu_tempuh = int(row.get("obyektempuh"))

            obyekrute = row.get("obyekrute") or None
            
            obyek_asal = dict_obyek.get(kode_asal)
            obyek_tujuan = dict_obyek.get(kode_tujuan)

            if not obyek_asal or not obyek_tujuan:
                print(f"⚠️ Skip row, obyek asal/tujuan tidak ditemukan: {kode_asal} -> {kode_tujuan}")
                continue

            key = (kode_asal, kode_tujuan)

            if key in dict_existing_jarak:
                obj = dict_existing_jarak[key]
                obj.obyektempuh = waktu_tempuh
                # obj.obyekrute = obyekrute
                list_update_jarak.append(obj)
            else:
                obj = jarakobyek(
                    ruteKODE=ruteKODE,
                    obyekKODEasal=obyek_asal,
                    obyekKODEtujuan=obyek_tujuan,
                    obyektempuh=waktu_tempuh,
                    # obyekrute=obyekrute
                )
                list_create_jarak.append(obj)

        if list_update_jarak:
            jarakobyek.objects.bulk_update(
                list_update_jarak, ["obyektempuh", "obyekrute"]
            )
            print(f"Updated JarakObyek {len(list_update_jarak)}")
            updated_jarakobyek = f"Updated JarakObyek {len(list_update_jarak)}"

        if list_create_jarak:
            jarakobyek.objects.bulk_create(list_create_jarak)
            print(f"Created JarakObyek {len(list_create_jarak)}")
            created_jarakobyek = f"Created JarakObyek {len(list_create_jarak)}"

    return created_obyekwisata, updated_obyekwisata, created_jarakobyek, updated_jarakobyek