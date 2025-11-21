import ast
from datetime import datetime
from django.db import models


class pengelola(models.Model):
    pengelolaKODE = models.CharField(max_length=3, primary_key=True)
    pengelolaPASSWORD = models.CharField(max_length=60)
    pengelolaEMAIL = models.CharField(max_length=255, unique=True)
    pengelolaNAMA1 = models.CharField(max_length=60)
    pengelolaNAMA2 = models.CharField(max_length=60)

    class Meta:
        db_table = "pengelola"

    #wistineraryadmin@gmail.com
    #Wistinerary12345

class anggota(models.Model):
    anggotaKODE = models.IntegerField(primary_key=True)
    anggotaNAMA = models.CharField(max_length=60)
    anggotaHP = models.CharField(max_length=15)
    anggotaEMAIL = models.CharField(max_length=60, unique=True)
    anggotaPASSWORD = models.CharField(max_length=60)

    #user01@gmail.com
    #Wistinerary12345

    class Meta:
        db_table = "anggota"
    
    def save(self, *args, **kwargs):
        if not self.anggotaKODE:  # kalau belum ada kode
            last = anggota.objects.order_by('-anggotaKODE').first()
            self.anggotaKODE = 1 if not last else last.anggotaKODE + 1
        super().save(*args, **kwargs)

class provinsi(models.Model):
    provinsiKODE = models.CharField(max_length=2, primary_key=True)
    provinsiNAMA = models.CharField(max_length=30)
    provinsiKET = models.CharField(max_length=255, null=True, blank=True)
    provinsiALAMAT = models.CharField(max_length=100, null=True, blank=True)
    datecreated = models.DateField(null=True, blank=True)
    usercreated = models.ForeignKey(pengelola, on_delete=models.SET_NULL, null=True, blank=True, db_column='usercreated', related_name="provinsi_created")
    dateupdated = models.DateField(null=True, blank=True)
    userupdated = models.ForeignKey(pengelola, on_delete=models.SET_NULL, null=True, blank=True, db_column='userupdated', related_name="provinsi_updated")

    class Meta:
        db_table = "provinsi"

class kabupaten(models.Model):
    kabupatenKODE = models.CharField(max_length=5, primary_key=True)
    kabupatenNAMA = models.CharField(max_length=60, null=True, blank=True)
    provinsiKODE = models.ForeignKey(provinsi, on_delete=models.SET_NULL, null=True, blank=True, db_column="provinsiKODE")
    kabupatenKET = models.TextField(null=True, blank=True)
    kabupatenALAMAT = models.CharField(max_length=255, null=True, blank=True)
    kabupatenFOTOICON = models.CharField(max_length=255, null=True, blank=True)
    kabupatenFOTOICONKET = models.TextField(null=True, blank=True)
    datecreated = models.DateField(null=True, blank=True)
    usercreated = models.ForeignKey(pengelola, on_delete=models.SET_NULL, null=True, blank=True, db_column='usercreated', related_name="kabupaten_created")
    dateupdated = models.DateField(null=True, blank=True)
    userupdated = models.ForeignKey(pengelola, on_delete=models.SET_NULL, null=True, blank=True, db_column='userupdated', related_name="kabupaten_updated")

    class Meta:
        db_table = "kabupaten"

class kecamatan(models.Model):
    kecamatanKODE = models.CharField(max_length=8, primary_key=True)
    kabupatenKODE = models.ForeignKey(kabupaten, on_delete=models.SET_NULL, null=True, blank=True, db_column="kabupatenKODE")
    kecamatanNAMA = models.CharField(max_length=30)
    kecamatanALAMAT = models.CharField(max_length=255, null=True, blank=True)
    kecamatanKET = models.TextField(null=True, blank=True)
    datecreated = models.DateField(null=True, blank=True)
    usercreated = models.ForeignKey(pengelola, on_delete=models.SET_NULL, null=True, blank=True, db_column='usercreated', related_name="kecamatan_created")
    dateupdated = models.DateField(null=True, blank=True)
    userupdated = models.ForeignKey(pengelola, on_delete=models.SET_NULL, null=True, blank=True, db_column='userupdated', related_name="kecamatan_updated")

    class Meta:
        db_table = "kecamatan"

class kategoriberita(models.Model):
    kategoriberitaKODE = models.CharField(max_length=4, primary_key=True)
    kategoriberitaNAMA = models.CharField(max_length=60)
    kategoriberitaKET = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "kategoriberita"
    
    def GenerateKode():
        last_data = kategoriberita.objects.order_by('-kategoriberitaKODE').first()
        if last_data:
            last_number = int(last_data.kategoriberitaKODE[2:])
            new_number = last_number + 1
        else :
            new_number = 1
        
        return f'KB{new_number:02d}'

class kategoriwisata(models.Model):
    kategoriwisataKODE = models.CharField(max_length=4, primary_key=True)
    kategoriwisataNAMA = models.CharField(max_length=60)
    kategoriwisataKET = models.TextField(null=True, blank=True)
    kategoriREFERENCE = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "kategoriwisata"

    def GenerateKode():
        last_data = kategoriwisata.objects.order_by('-kategoriwisataKODE').first()
        if last_data :
            last_number = int(last_data.kategoriwisataKODE[2:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"KW{new_number:02d}"
    
    def GetWaktuKunjung(kategoriwisataNAMA):
        waktu_kunjung = 0
        if kategoriwisataNAMA == 'Wisata Alam':
            waktu_kunjung = 3 * 60
        elif kategoriwisataNAMA == 'Pusat Perbelanjaan':
            waktu_kunjung = 2.5 * 60
        elif kategoriwisataNAMA == 'Taman Alam Buatan':
            waktu_kunjung = 2 * 60
        elif kategoriwisataNAMA == 'Kuliner':
            waktu_kunjung = 1 * 60
        elif kategoriwisataNAMA == 'Taman Hiburan':
            waktu_kunjung = 5 * 60
        
        return waktu_kunjung


class kegiatan(models.Model):
    eventKODE = models.CharField(max_length=10, primary_key=True)
    eventNAMA = models.CharField(max_length=255)
    kabupatenKODE = models.ForeignKey(kabupaten, on_delete=models.SET_NULL, null=True, blank=True, db_column="kabupatenKODE")
    eventKET = models.TextField(null=True, blank=True)
    eventMULAI = models.DateField(null=True, blank=True)
    eventSELESAI = models.DateField(null=True, blank=True)
    eventPOSTER = models.CharField(max_length=120, null=True, blank=True)
    eventSUMBER = models.CharField(max_length=120, null=True, blank=True)
    datecreated = models.DateField(null=True, blank=True)
    usercreated = models.ForeignKey(pengelola, on_delete=models.SET_NULL, null=True, blank=True, db_column='usercreated', related_name="kegiatan_created")
    dateupdated = models.DateField(null=True, blank=True)
    userupdated = models.ForeignKey(pengelola, on_delete=models.SET_NULL, null=True, blank=True, db_column='userupdated', related_name="kegiatan_updated")

    class Meta:
        db_table = "kegiatan"
    
    def GenerateKode ():
        last_data = kegiatan.objects.order_by('-eventKODE').first()
        if last_data:
            # Ambil angka dari kode, contoh: E000000001 -> 1
            last_number = int(last_data.eventKODE[1:])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"E{new_number:09d}"

class obyekwisata(models.Model):
    obyekKODE = models.CharField(max_length=12, primary_key=True)
    obyekNAMA = models.CharField(max_length=120)
    kecamatanKODE = models.ForeignKey(kecamatan, on_delete=models.SET_NULL, null=True, blank=True, db_column="kecamatanKODE")
    kategoriKODE = models.ForeignKey(kategoriwisata, on_delete=models.SET_NULL, null=True, blank=True, db_column="kategoriKODE")
    obyekALAMAT = models.CharField(max_length=255, null=True, blank=True)
    obyekDERAJAT_S = models.IntegerField(null=True, blank=True, editable=True)
    obyekMENIT_S = models.IntegerField(null=True, blank=True, editable=True)
    obyekDETIK_S = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, editable=True)
    obyekLATITUDE = models.DecimalField(max_digits=15, decimal_places=11, null=True, blank=True, editable=True)
    obyekDERAJAT_E = models.IntegerField(null=True, blank=True, editable=True)
    obyekMENIT_E = models.IntegerField(null=True, blank=True, editable=True)
    obyekDETIK_E = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, editable=True)
    obyekLONGITUDE = models.DecimalField(max_digits=15, decimal_places=11, null=True, blank=True, editable=True)
    obyekKETINGGIAN = models.IntegerField(null=True, blank=True, editable=True)
    obyekJAMBUKA = models.TimeField(null=True, blank=True)
    obyekJAMTUTUP = models.TimeField(null=True, blank=True)
    obyekWAKTUKUNJUNG =  models.IntegerField(null=True, blank=True, editable=True)
    obyekPOPULARITAS = models.IntegerField(null=True, blank=True, editable=True)
    obyekKEMUDAHAN = models.IntegerField(null=True, blank=True, editable=True)
    obyekDEFINISI = models.TextField(null=True, blank=True)
    obyekKETERANGAN = models.TextField(null=True, blank=True)
    obyekFOTO = models.CharField(max_length=255, null=True, blank=True)
    datecreated = models.DateField(null=True, blank=True)
    usercreated = models.ForeignKey(pengelola, on_delete=models.SET_NULL, null=True, blank=True, db_column='usercreated', related_name="obyekwisata_created")
    dateupdated = models.DateField(null=True, blank=True)
    userupdated = models.ForeignKey(pengelola, on_delete=models.SET_NULL, null=True, blank=True, db_column='userupdated', related_name="obyekwisata_updated")

    class Meta:
        db_table = "obyekwisata"
    
    def get_derajat(latitude, longtitude):
        """
        Konversi latitude (selalu S) dan longitude (selalu E) desimal ke DMS

        latitude = -7.84744453430

        derajat = 7
        menit = 7 - 7.84744453430 = 84744453430*60 = 50.846672058
        detik = 50.846672058 - 50 = 846672058*60 = 50.80
        """
        lat = float(latitude)
        lon = float(longtitude)

        # Latitude S
        lat_abs = abs(lat)
        derajat_s = int(lat_abs)
        menit_s = int((lat_abs - derajat_s) * 60)
        detik_s = (lat_abs - derajat_s - menit_s/60) * 3600

        # Longitude E
        lon_abs = abs(lon)
        derajat_e = int(lon_abs)
        menit_e = int((lon_abs - derajat_e) * 60)
        detik_e = (lon_abs - derajat_e - menit_e/60) * 3600

        # Round detik untuk presisi 2 angka desimal
        detik_s = round(detik_s, 2)
        detik_e = round(detik_e, 2)

        return derajat_s, menit_s, detik_s, derajat_e, menit_e, detik_e

class berita(models.Model):
    beritaKODE = models.CharField(max_length=11, primary_key=True)
    beritaJUDUL = models.CharField(max_length=255)
    kategoriberitaKODE = models.ForeignKey(kategoriberita, on_delete=models.SET_NULL, null=True, blank=True, db_column="kategoriberitaKODE")
    eventKODE = models.ForeignKey(kegiatan, on_delete=models.SET_NULL, null=True, blank=True, db_column="eventKODE")
    obyekKODE = models.ForeignKey(obyekwisata, on_delete=models.SET_NULL, null=True, blank=True, db_column="obyekKODE")
    kabupatenKODE = models.ForeignKey(kabupaten, on_delete=models.SET_NULL, null=True, blank=True, db_column="kabupatenKODE")
    beritaISI = models.TextField(null=True, blank=True)
    beritaISI2 = models.TextField(null=True, blank=True)
    beritaSUMBER = models.CharField(max_length=255, null=True, blank=True)
    beritaPENULIS = models.CharField(max_length=60, null=True, blank=True)
    beritaTGL = models.DateField(null=True, blank=True)
    beritaICONFOTO = models.CharField(max_length=255, null=True, blank=True)
    datecreated = models.DateField(null=True, blank=True)
    usercreated = models.ForeignKey(pengelola, on_delete=models.SET_NULL, null=True, blank=True, db_column='usercreated', related_name="berita_created")
    dateupdated = models.DateField(null=True, blank=True)
    userupdated = models.ForeignKey(pengelola, on_delete=models.SET_NULL, null=True, blank=True, db_column='userupdated', related_name="berita_updated")

    class Meta:
        db_table = "berita"
    
    def GenerateKode():
        last_data = berita.objects.order_by('-beritaKODE').first()
        if last_data : 
            last_number = int(last_data.beritaKODE[1:])
            new_number = last_number+1
        else:
            new_number = 1
        
        return f"B{new_number:010d}"
    
class jarakobyek(models.Model):
    ruteKODE = models.IntegerField(primary_key=True)
    obyekKODEasal = models.ForeignKey(obyekwisata, on_delete=models.SET_NULL, null=True, blank=True, db_column='obyekKODEasal', related_name="obyekKODEasal")
    obyekKODEtujuan = models.ForeignKey(obyekwisata, on_delete=models.SET_NULL, null=True, blank=True, db_column='obyekKODEtujuan', related_name="obyekKODEtujuan")
    obyektempuh = models.TextField(null=True, blank=True)
    obyekrute = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "jarakobyek"
    
    def GenerateKode():
        last_data = jarakobyek.objects.order_by('-ruteKODE').first()
        if last_data :
            new_number = last_data.ruteKODE + 1
        else:
            new_number = 1
        
        return new_number
    

class hasilitinerary(models.Model):
    hasilKODE = models.AutoField(primary_key=True)
    anggotaKODE = models.ForeignKey(anggota, on_delete=models.SET_NULL, null=True, blank=True, db_column='anggotaKODE', related_name="anggotaKODEitinerary")
    judul_itinerary = models.CharField(max_length=255, null=True, blank=True)
    jam_mulai = models.TimeField(null=True, blank=True, editable=True)
    jam_selesai = models.TimeField(null=True, blank=True, editable=True)
    score = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, editable=True)
    datecreated = models.DateField(null=True, blank=True)
    hari_input = models.IntegerField(null=True, blank=True, editable=True)

    class Meta:
        db_table = "hasilitinerary"

class headeritinerary(models.Model):
    headerKODE = models.AutoField(primary_key=True)
    hari = models.IntegerField(null=True, blank=True, editable=True)
    hasilKODE = models.ForeignKey(hasilitinerary, on_delete=models.SET_NULL, null=True, blank=True, db_column='hasilKODE', related_name="hasilitineraryheader")
    jam_mulai = models.TimeField(null=True, blank=True, editable=True)
    jam_selesai = models.TimeField(null=True, blank=True, editable=True)
    
    class Meta:
        db_table = "headeritinerary"

        constraints = [
            models.UniqueConstraint(
                fields=['hasilKODE', 'hari'], 
                name='unique_header_hasil_hari'
            )
        ]

class detailitinerary(models.Model):
    detailKODE = models.AutoField(primary_key=True)
    obyekKODEasal = models.ForeignKey(obyekwisata, on_delete=models.SET_NULL, null=True, blank=True, db_column='obyekKODEasal', related_name="detailobyekKODEasal")
    obyekKODEtujuan = models.ForeignKey(obyekwisata, on_delete=models.SET_NULL, null=True, blank=True, db_column='obyekKODEtujuan', related_name="detailobyekKODEtujuan")
    headerKODE = models.ForeignKey(headeritinerary, on_delete=models.SET_NULL, null=True, blank=True, db_column='headerKODE', related_name="detailheaderKODE")
    urutan = models.IntegerField(null=True, blank=True, editable=True)
    jam_mulai = models.TimeField(null=True, blank=True, editable=True)
    jam_selesai = models.TimeField(null=True, blank=True, editable=True)

    class Meta:
        db_table = "detailitinerary"

        constraints = [
            models.UniqueConstraint(
                fields=['obyekKODEasal', 'obyekKODEtujuan', 'headerKODE', 'urutan'], 
                name='unique_detail_itinerary'
            )
        ]

class skipitinerary(models.Model):
    skipKODE = models.AutoField(primary_key=True)
    obyekKODE = models.ForeignKey(obyekwisata, on_delete=models.SET_NULL, null=True, blank=True, db_column="obyekKODE")
    hasilKODE = models.ForeignKey(hasilitinerary, on_delete=models.SET_NULL, null=True, blank=True, db_column='hasilKODE', related_name="skiphasilitinerary")

    class Meta:
        db_table = "skipitinerary"     

        constraints = [
            models.UniqueConstraint(
                fields=['obyekKODE', 'hasilKODE'], 
                name='unique_skip_obyek'
            )
        ]