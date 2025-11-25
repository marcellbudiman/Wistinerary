import base64
import math
import random
from datetime import datetime, time
from itertools import permutations

from django.utils import timezone
import hashlib
import os
import sys
import pandas as pd
import django

from algoritma_pso import CalculatePSO

# Tambahkan root project ke sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wistinerary.settings")
django.setup()

from app.models import anggota, detailitinerary, hasilitinerary, headeritinerary, jarakobyek, kabupaten, kategoriwisata, kecamatan, obyekwisata, provinsi, pengelola, skipitinerary

import numpy as np
import pandas as pd

def run():
    # .venv\Scripts\activate

    # user_id = 1
    # judul_perjalanan = '2hari10destinasi --6'

    # hotel_kode = '32.01.05-008'
    # selected_obyek_str = '32.01.25-006,32.01.26-007,32.01.26-002,32.01.05-004,32.01.05-007,32.01.01-007,32.01.01-002,32.01.01-004,32.01.01-009,32.01.01-005'
    # kapasitas_hari = '2'

    # jam_mulai = '07:00'
    # jam_selesai = '17:00'

    # selected_obyek_kodes = selected_obyek_str.split(",")

    # # Process itinerary creation here
    # dict_routes, dict_destination, mapping_destination = CalculatePSO().get_routes(hotel_kode=hotel_kode, list_obyek_kode=selected_obyek_kodes)
    # value_time_rating, optimal_routes, destination_cant_visit, total_time_spend, routes_schedule = CalculatePSO().calculate_itinerary(kapasitas_hari=kapasitas_hari, dict_routes=dict_routes, dict_destination=dict_destination, jam_mulai=jam_mulai, jam_selesai=jam_selesai, judul_itinerary=judul_perjalanan)

    
    # hasilitinerary = CalculatePSO().saveItinerary(judul_perjalanan=judul_perjalanan, user_id=user_id,
    #                                     jam_mulai=jam_mulai, jam_selesai=jam_selesai,
    #                                     mapping_destination=mapping_destination,
    #                                     destination_cant_visit=destination_cant_visit, routes_schedule=routes_schedule, score=value_time_rating)
    
    for i in range(1, 11):
        judul_perjalanan = f'7hari36destinasi_{i}'  # ubah nama setiap iterasi
        print(f"{datetime.today()} Iterasi ke-{i} Start: {judul_perjalanan}")
        user_id = 1
        hotel_kode = '32.01.25-002'
        selected_obyek_str =    '32.01.25-006,32.01.26-007,32.01.26-002,32.01.05-004,32.01.05-007,' \
                                '32.01.01-007,32.01.01-002,32.01.01-004,32.01.07-003,32.01.25-009,' \
                                '32.01.07-004,32.01.01-009,32.01.26-008,32.01.26-001,32.01.07-005,' \
                                '32.01.05-001,32.01.25-004,32.01.05-009,32.01.05-005,32.01.01-005,' \
                                '32.01.26-004,32.01.01-001,32.01.26-003,32.01.26-009,32.01.07-010,' \
                                '32.01.25-001,32.01.25-008,32.01.07-002,32.01.07-006,32.01.07-001,' \
                                '32.01.25-003,32.01.01-003,32.01.05-010,32.01.05-003,32.01.07-009,' \
                                '32.01.25-005'
        kapasitas_hari = '7'

        # 32.01.07-003,32.01.25-009,
        # 32.01.07-004,32.01.01-009,32.01.26-008,32.01.26-001,32.01.07-005,
        # 32.01.05-001,32.01.25-004,32.01.05-009,32.01.05-005,32.01.01-005,
        # 32.01.26-004,32.01.01-001,32.01.26-003,32.01.26-009,32.01.07-010,
        # 32.01.25-001,32.01.25-008,32.01.07-002,32.01.07-006,32.01.07-001,
        # 32.01.25-003,32.01.01-003,32.01.05-010,32.01.05-003,32.01.07-009,
        # 32.01.25-005

        jam_mulai = '07:00'
        jam_selesai = '17:00'

        selected_obyek_kodes = selected_obyek_str.split(",")

        # Proses perhitungan itinerary
        dict_routes, dict_destination, mapping_destination = CalculatePSO().get_routes(
            hotel_kode=hotel_kode,
            list_obyek_kode=selected_obyek_kodes
        )

        value_time_rating, optimal_routes, destination_cant_visit, total_time_spend, routes_schedule = CalculatePSO().calculate_itinerary(
            kapasitas_hari=kapasitas_hari,
            dict_routes=dict_routes,
            dict_destination=dict_destination,
            jam_mulai=jam_mulai,
            jam_selesai=jam_selesai,
            judul_itinerary=judul_perjalanan
        )

        hasilitinerary = CalculatePSO().saveItinerary(
            judul_perjalanan=judul_perjalanan,
            user_id=user_id,
            jam_mulai=jam_mulai,
            jam_selesai=jam_selesai,
            mapping_destination=mapping_destination,
            destination_cant_visit=destination_cant_visit,
            routes_schedule=routes_schedule,
            score=value_time_rating
        )

        print(f"{datetime.today()} Iterasi ke-{i} End: {judul_perjalanan}")

if __name__ == "__main__":
    run()
