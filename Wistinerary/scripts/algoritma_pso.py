import base64
import copy
import math
import random
from datetime import datetime, time
from itertools import permutations
import traceback
from folium import plugins
from django.utils import timezone
import hashlib
import os
import sys
import folium
import pandas as pd
import django
import requests
from sklearn.cluster import KMeans

# Tambahkan root project ke sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wistinerary.settings")
django.setup()

from app.models import anggota, detailitinerary, hasilitinerary, headeritinerary, jarakobyek, kabupaten, kategoriwisata, kecamatan, obyekwisata, provinsi, pengelola, skipitinerary

import numpy as np
import pandas as pd


class CalculatePSO :
    koefisien_rating = 0.75
    koefisien_waktu = 0.25

    def scaling_popularitas(self, popularitas):
        scaling_popularitas = (1 - ((popularitas-1)/(5-1)) ) * 100

        return scaling_popularitas

    def create_distance_matrix(self, dict_destinasi):
        # Kumpulkan semua label unik
        labels = set()
        for d in dict_destinasi:
            labels.add(d['id_asal'])
            labels.add(d['id_tujuan'])
        labels = sorted(list(set([d['id_asal'] for d in dict_destinasi] + [d['id_tujuan'] for d in dict_destinasi])))
        labels.remove('Hotel')
        labels = ['Hotel'] + labels  # H duluan

        # Buat mapping label ke index matrix
        label_to_index = {label: idx for idx, label in enumerate(labels)}
        n = len(labels)

        # Inisialisasi matriks dengan inf (atau bisa pakai 0 jika semua pasangan pasti tersedia)
        dist_matrix = np.full((n, n), np.inf)

        # Isi nilai diagonal dengan 0 (waktu ke diri sendiri)
        np.fill_diagonal(dist_matrix, 0)

        # Isi waktu dari dict
        for d in dict_destinasi:
            i = label_to_index[d['id_asal']]
            j = label_to_index[d['id_tujuan']]
            dist_matrix[i][j] = d['waktu']

        return dist_matrix, labels

    def time_to_minutes(self, time_str):
        if isinstance(time_str, str):
            h, m = map(int, time_str.split(':'))
            return h * 60 + m
        elif isinstance(time_str, time):
            return time_str.hour * 60 + time_str.minute
        return 0

    def minutes_to_time(self, minutes):
            hours = minutes // 60
            mins = minutes % 60
            return time(hour=hours, minute=mins)

    def decode_and_evaluate(self, permutation, labels, routes_data, destionation_data, num_days, jam_mulai, jam_selesai):
        start_minutes = self.time_to_minutes(jam_mulai)
        end_minutes = self.time_to_minutes(jam_selesai)
        kapasitas = end_minutes - start_minutes  # Total kapasitas waktu per hari
        
        # permutation adalah urutan destinasi_id yang diacak
        routes = []
        # routes_time = []  #List untuk menyimpan waktu setiap rute
        hotel_id = labels[0]
        current_route = [hotel_id]
        current_time_spend = 0
        destination_cant_visit = []
        total_time_spend = 0
        total_rating_scaled = 0

        current_schedule = [] # Jadwal detail untuk rute saat ini
        routes_schedule = []  # Jadwal lengkap per rute dengan jam_mulai dan jam_selesai

        routes_dict = {
            f"{d['id_asal']}-{d['id_tujuan']}": d['waktu']
            for d in routes_data
        }

        destination_dict = {d['id']: {
            'waktu_kunjungan': d['waktu_kunjungan'],
            'popularitas': d.get('popularitas', 0)
        } for d in destionation_data}

        previous_location_id = hotel_id
        current_time_in_day = start_minutes

        for destination_id in permutation:
            destination_info = destination_dict[destination_id]
            destination_time_spend = destination_info['waktu_kunjungan']
            destination_rating_scaled = self.scaling_popularitas(destination_info['popularitas'])

            travel_to_destination = routes_dict.get(f"{previous_location_id}-{destination_id}", 0)
            travel_back_to_hotel = routes_dict.get(f"{destination_id}-{hotel_id}", 0)
            previous_travel_back = routes_dict.get(f"{previous_location_id}-{hotel_id}", 0)

            total_time_if_visit = int(current_time_spend) - int(previous_travel_back) + int(travel_to_destination) + int(destination_time_spend) + int(travel_back_to_hotel)

            if total_time_if_visit <= kapasitas:
                current_route.append(destination_id)
                current_time_spend = int(current_time_spend) - int(previous_travel_back) + int(travel_to_destination) + int(destination_time_spend) + int(travel_back_to_hotel)
                
                # Hitung jam_mulai dan jam_selesai untuk destinasi ini
                if previous_location_id == hotel_id and len(current_schedule) == 0:
                    # Destinasi pertama di hari ini - mulai dari jam_mulai hari
                    jam_berangkat = current_time_in_day
                    jam_tiba = jam_berangkat + int(travel_to_destination)
                else:
                    # Berangkat dari lokasi sebelumnya
                    jam_berangkat = current_schedule[-1]['jam_selesai_minutes']
                    jam_tiba = jam_berangkat + int(travel_to_destination)
                
                jam_selesai_dest = jam_tiba + int(destination_time_spend)
                
                # Simpan jadwal destinasi
                current_schedule.append({
                    'destination_id': destination_id,
                    'from_id': previous_location_id,
                    'jam_mulai_minutes': jam_berangkat,  # ← UBAH: jam berangkat, bukan jam tiba
                    'jam_selesai_minutes': jam_selesai_dest,
                    'jam_mulai': self.minutes_to_time(jam_berangkat),  # ← UBAH
                    'jam_selesai': self.minutes_to_time(jam_selesai_dest),
                    'waktu_kunjungan': destination_time_spend,
                    'waktu_perjalanan': travel_to_destination
                })

                previous_location_id = destination_id
                total_rating_scaled += destination_rating_scaled
            else:
                current_route.append(hotel_id)
                routes.append(current_route)
                # routes_time.append(current_time_spend)

                # Simpan jadwal lengkap hari ini + PERJALANAN KEMBALI KE HOTEL
                if current_schedule:
                    jam_mulai_hari = start_minutes
                    travel_back = int(routes_dict.get(f"{previous_location_id}-{hotel_id}", 0))
                    jam_berangkat_ke_hotel = current_schedule[-1]['jam_selesai_minutes']
                    jam_tiba_hotel = jam_berangkat_ke_hotel + travel_back
                    
                    # Tambahkan perjalanan kembali ke hotel
                    current_schedule.append({
                        'destination_id': hotel_id,
                        'from_id': previous_location_id,
                        'jam_mulai_minutes': jam_berangkat_ke_hotel,
                        'jam_selesai_minutes': jam_tiba_hotel,
                        'jam_mulai': self.minutes_to_time(jam_berangkat_ke_hotel),
                        'jam_selesai': self.minutes_to_time(jam_tiba_hotel),
                        'waktu_kunjungan': 0,
                        'waktu_perjalanan': travel_back
                    })
                    
                    routes_schedule.append({
                        'route': current_route.copy(),
                        'schedule': current_schedule.copy(),
                        'jam_mulai': self.minutes_to_time(jam_mulai_hari),
                        'jam_selesai': self.minutes_to_time(jam_tiba_hotel),
                        'total_time': current_time_spend
                    })

                total_time_spend += int(current_time_spend)

                if len(routes) < num_days:
                    travel_to_destination_new = routes_dict.get(f"{hotel_id}-{destination_id}", 0)
                    new_day_total_time = int(travel_to_destination_new) + int(destination_time_spend) + int(travel_back_to_hotel)

                    if new_day_total_time <= kapasitas:
                        current_route = [hotel_id, destination_id]
                        current_time_spend = new_day_total_time
                        current_schedule = []
                    
                        # Jadwal di hari baru
                        jam_berangkat_baru = start_minutes
                        jam_tiba_baru = jam_berangkat_baru + int(travel_to_destination_new)
                        jam_selesai_baru = jam_tiba_baru + int(destination_time_spend)
                        
                        current_schedule.append({
                            'destination_id': destination_id,
                            'from_id': hotel_id,
                            'jam_mulai_minutes': jam_berangkat_baru,  # ← UBAH: jam berangkat
                            'jam_selesai_minutes': jam_selesai_baru,
                            'jam_mulai': self.minutes_to_time(jam_berangkat_baru),  # ← UBAH
                            'jam_selesai': self.minutes_to_time(jam_selesai_baru),
                            'waktu_kunjungan': destination_time_spend,
                            'waktu_perjalanan': travel_to_destination_new
                        })
                        
                        previous_location_id = destination_id
                        current_time_in_day = start_minutes
                        total_rating_scaled += destination_rating_scaled
                    else:
                        total_time_spend += int(current_time_spend)
                        destination_cant_visit.append(destination_id)
                        current_route = [hotel_id]
                        current_time_spend = 0
                        current_schedule = []
                        previous_location_id = hotel_id
                        current_time_in_day = start_minutes
                else:
                    destination_cant_visit.append(destination_id)
                    for remaining_dest in permutation[permutation.index(destination_id) + 1:]:
                        destination_cant_visit.append(remaining_dest)
                    break

        # Tutup route terakhir + PERJALANAN KEMBALI KE HOTEL
        if len(routes) < num_days and len(current_route) > 1:
            total_time_spend += int(current_time_spend)
            current_route.append(hotel_id)
            routes.append(current_route)
            # routes_time.append(current_time_spend)
            
            # Simpan jadwal hari terakhir + perjalanan kembali
            if current_schedule:
                jam_mulai_hari = start_minutes
                travel_back = int(routes_dict.get(f"{previous_location_id}-{hotel_id}", 0))
                jam_berangkat_ke_hotel = current_schedule[-1]['jam_selesai_minutes']
                jam_tiba_hotel = jam_berangkat_ke_hotel + travel_back
                
                # Tambahkan perjalanan kembali ke hotel
                current_schedule.append({
                    'destination_id': hotel_id,
                    'from_id': previous_location_id,
                    'jam_mulai_minutes': jam_berangkat_ke_hotel,
                    'jam_selesai_minutes': jam_tiba_hotel,
                    'jam_mulai': self.minutes_to_time(jam_berangkat_ke_hotel),
                    'jam_selesai': self.minutes_to_time(jam_tiba_hotel),
                    'waktu_kunjungan': 0,
                    'waktu_perjalanan': travel_back
                })
                
                routes_schedule.append({
                    'route': current_route.copy(),
                    'schedule': current_schedule.copy(),
                    'jam_mulai': self.minutes_to_time(jam_mulai_hari),
                    'jam_selesai': self.minutes_to_time(jam_tiba_hotel),
                    'total_time': current_time_spend
                })

        pbest_value = (total_time_spend * CalculatePSO.koefisien_waktu) + (total_rating_scaled * CalculatePSO.koefisien_rating)

        # return pbest_value, routes, destination_cant_visit, total_time_spend, total_rating_scaled, routes_time, routes_schedule
        return pbest_value, routes, destination_cant_visit, total_time_spend, total_rating_scaled, routes_schedule

    def calculate_pso (self, routes_data, num_particle, destination_data, max_iteration, c1, c2, num_days, skala_awal, skala_akhir, jam_mulai, jam_selesai, judul_itinerary):
        # excel_rute_desintasi = pd.DataFrame(routes_data)
        # excel_destinasi = pd.DataFrame(destination_data)

        # Buat matrix dan dapatkan urutan label (misal: ['H', 'A', 'B', 'C', 'D'])
        # labels adalah id destinasi id (H untuk hotel)
        distance_matrix, labels = self.create_distance_matrix(routes_data)
        num_destination_to_visit = len(labels) - 1  # karena H tidak dikunjungi

        print(f"{datetime.today()} Create particle")
        #ini yang kepake nanti
        list_particle = [] #atau swarm (kumpulan particle)
        for i in range(num_particle):
            
            # # Pilih acak urutan label destinasi (tanpa 'H')
            position = random.sample(labels[1:], num_destination_to_visit) #list urutan destinasi acak

            value_time_rating, routes, destination_cant_visit, total_time_spend, total_rating_scaled, routes_schedule = self.decode_and_evaluate(
                permutation=position, labels=labels,
                routes_data=routes_data, destionation_data=destination_data,
                num_days=num_days, jam_mulai=jam_mulai, jam_selesai=jam_selesai
            )

            particle = {
                'position': copy.deepcopy(position),
                'pbest_position': copy.deepcopy(position),
                'rute': routes,
                'pbest_fitness': value_time_rating,
                'current_fitness': value_time_rating,
                'destination_cant_visit': destination_cant_visit,
                'total_rating_scaled': total_rating_scaled,
                'routes_schedule': routes_schedule
            }
            list_particle.append(particle)
        
        #hardcode
        # list_position = [
        #     ['D', 'C', 'B', 'A'],  # posisi partikel 1
        #     ['C', 'A', 'D', 'B']  # posisi partikel 2
        # ]
        
        # list_particle = []
        
        # for i in range(num_particle):
        #     position = list_position[i]  # ambil posisi sesuai urutan
        
        #     value_time_rating, routes, destination_cant_visit, total_time_spend, total_rating_scaled, routes_schedule = self.decode_and_evaluate(
        #         permutation=position, labels=labels,
        #         routes_data=routes_data, destionation_data=destination_data,
        #         num_days=num_days, jam_mulai=jam_mulai, jam_selesai=jam_selesai
        #     )
        
        #     particle = {
        #         'position': copy.deepcopy(position),
        #         'pbest_position': copy.deepcopy(position),
        #         'rute': routes,
        #         'pbest_fitness': value_time_rating,
        #         'current_fitness': value_time_rating,
        #         'destination_cant_visit': destination_cant_visit,
        #         'total_rating_scaled': total_rating_scaled,
        #         'routes_schedule': routes_schedule
        #     }
        #     list_particle.append(particle)

        # list_particle_snapshot = copy.deepcopy(list_particle)
        # excel_list_partikel = pd.DataFrame(list_particle_snapshot)
        print(f"{datetime.today()} End")

        # print(f"{datetime.today()} Start All Permutation")
        # #semua kemungkinan permutasi
        # list_all_particle = []
        # list_position = []
        # for data in list_particle:
        #     position = data.get('position')
        #     list_position.append(position)

        # all_permutations = list(permutations(list_position[0]))  # semua urutan unik

        # for perm in all_permutations:
        #     position = list(perm)

        #     value_time_rating, routes, destination_cant_visit, total_time_spend, total_rating_scaled, routes_schedule = self.decode_and_evaluate(
        #         permutation=position, labels=labels,
        #         routes_data=routes_data, destionation_data=destination_data,
        #         num_days=num_days, jam_mulai=jam_mulai, jam_selesai=jam_selesai
        #     )

        #     particle = {
        #         'position': position,
        #         'pbest_position': position.copy(),
        #         'rute': routes,
        #         # 'waktu' : routes_time,
        #         'pbest_fitness': value_time_rating,
        #         'current_fitness': value_time_rating,
        #         'destination_cant_visit': destination_cant_visit,
        #         # 'total_time_spend' : total_time_spend,
        #         'total_rating_scaled' : total_rating_scaled,
        #         'routes_schedule' : routes_schedule
        #     }
        #     list_all_particle.append(particle)

        # excel_list_all_partikel = pd.DataFrame(list_all_particle)
        # print(f"{datetime.today()} End All Permutation")

        # Initialize global best
        best_particle = min(list_particle, key=lambda p: p['pbest_fitness'])
        gbest_position = best_particle.get('pbest_position')
        gbest_fitness = best_particle.get('pbest_fitness')
        gbest_routes = best_particle.get('rute')
        gbest_cant_visit = best_particle.get('destination_cant_visit')

        log_perubahan = []

        print(f"{datetime.today()} Iterasi loop pbest gbest")
        for iteration in range(max_iteration):
            skala = skala_awal - ((skala_awal - skala_akhir) * (iteration / max_iteration))

            for particle in list_particle:
                last_position = copy.deepcopy(particle['position'])
                last_pbest = copy.deepcopy(particle['pbest_position'])
                last_value = copy.deepcopy(particle['current_fitness'])
                last_num_cant_visit = len(particle.get('destination_cant_visit', []))
                
                # Simpan gbest lama juga
                gbest_position_lama = copy.deepcopy(gbest_position)
                last_gbest_cant_visit = len(gbest_cant_visit) if gbest_cant_visit else 0

                # === Pendekatan pbest ===
                for _ in range(int(c1 * random.random() * len(particle['position']) * skala)):
                    idx1, idx2 = random.sample(range(len(particle['position'])), 2)
                    if particle['position'][idx1] != particle['pbest_position'][idx1] or \
                            particle['position'][idx2] != particle['pbest_position'][idx2]:
                        particle['position'][idx1], particle['position'][idx2] = (
                            particle['position'][idx2], particle['position'][idx1]
                        )

                # === Pendekatan gbest ===
                for _ in range(int(c2 * random.random() * len(particle['position']) * skala)):
                    idx1, idx2 = random.sample(range(len(particle['position'])), 2)
                    if particle['position'][idx1] != gbest_position[idx1] or \
                            particle['position'][idx2] != gbest_position[idx2]:
                        particle['position'][idx1], particle['position'][idx2] = (
                            particle['position'][idx2], particle['position'][idx1]
                        )

                # === Hitung ulang fitness
                value_time_rating, routes, destination_cant_visit, total_time_spend, total_rating_scaled, routes_schedule = self.decode_and_evaluate(
                    permutation=particle['position'], labels=labels,
                    routes_data=routes_data, destionation_data=destination_data,
                    num_days=num_days, jam_mulai=jam_mulai, jam_selesai=jam_selesai
                )
                particle['current_fitness'] = value_time_rating
                new_num_cant_visit = len(destination_cant_visit)

                # === Update pbest ===
                is_pbest_updated = False
                if (new_num_cant_visit < last_num_cant_visit) or \
                (new_num_cant_visit == last_num_cant_visit and value_time_rating < particle['pbest_fitness']):
                    is_pbest_updated = True
                    particle['pbest_fitness'] = value_time_rating
                    particle['pbest_position'] = copy.deepcopy(particle['position'])
                    particle['rute'] = routes
                    particle['waktu'] = total_time_spend
                    particle['total_rating_scaled'] = total_rating_scaled
                    particle['destination_cant_visit'] = destination_cant_visit

                # === Update gbest ===
                is_gbest_updated = False
                if (new_num_cant_visit < last_gbest_cant_visit) or \
                (new_num_cant_visit == last_gbest_cant_visit and value_time_rating < gbest_fitness):
                    is_gbest_updated = True
                    gbest_fitness = value_time_rating
                    gbest_position = copy.deepcopy(particle['position'])
                    gbest_routes = routes
                    gbest_cant_visit = destination_cant_visit

        #         # LOGGING
        #         log_perubahan.append({
        #             'Iterasi': iteration + 1,
        #             'Nomor Partikel': list_particle.index(particle) + 1,
                    
        #             # Data SEBELUM swap/update
        #             'Urutan Pbest Lama': '-'.join(last_pbest),
        #             'Posisi Sebelum Swap': '-'.join(last_position),
        #             'Value Pbest Lama': last_value,
                    
        #             # Data SETELAH swap
        #             'Posisi Setelah Swap': '-'.join(new_position),
        #             'Nilai posisi swap' : value_time_rating,
        #             'Rute posisi swap' : routes,
                    
        #             # Data pbest baru
        #             'Urutan Pbest Baru': '-'.join(particle['pbest_position']),
        #             'Rute Pbest': particle.get('rute', routes),
        #             'Value Pbest Baru': particle['pbest_fitness'],
        #             'Status Update Pbest': is_pbest_updated,
                    
        #             # Data gbest
        #             'Urutan Gbest Lama': '-'.join(gbest_position_lama),
        #             'Urutan Gbest': '-'.join(gbest_position),
        #             'Rute Gbest': gbest_routes,
        #             'Value Gbest': gbest_fitness,
        #             'Cant Visit Gbest': gbest_cant_visit,
        #             'Status Update Gbest': is_gbest_updated,
        #         })

        # excel_list_log_perubahan = pd.DataFrame(log_perubahan)
        print(f"{datetime.today()} End")

        print(f"{datetime.today()} Start Optimal")
        value_time_rating, optimal_routes, destination_cant_visit, total_time_spend, total_rating_scaled, routes_schedule = self.decode_and_evaluate(
            permutation=gbest_position,
            labels=labels,
            routes_data=routes_data,
            destionation_data=destination_data,
            num_days=num_days, jam_mulai=jam_mulai, jam_selesai=jam_selesai
        )

        # # Siapkan dictionary hasil
        # hasil_optimal = {
        #     'Jam Mulai' : jam_mulai,
        #     'Jam Selesai' : jam_selesai,
        #     'Kapasitas Hari' : num_days,
        #     'Total Waktu' : total_time_spend,
        #     'Koefesien Waktu' : CalculatePSO.koefisien_waktu,
        #     'Total Rating Scaled' : total_rating_scaled,
        #     'Koefesien Rating': CalculatePSO.koefisien_rating,
        #     'Total Value Optimal': value_time_rating,
        #     'Rute Terbaik': optimal_routes,
        #     # 'Waktu Rute' : routes_time,
        #     'Destinasi tidak dikunjungi': destination_cant_visit,
        #     'routes_schedule': routes_schedule
        # }
        # excel_hasil = pd.DataFrame([hasil_optimal])
        print(f"{datetime.today()} End Optimal")

        # print(f"{datetime.today()} Start Excel")
        # timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        # with pd.ExcelWriter(f'{judul_itinerary}_{timestamp}.xlsx', engine='openpyxl') as writer:
        #     excel_destinasi.to_excel(writer, sheet_name='Destinasi', index=False)
        #     excel_rute_desintasi.to_excel(writer, sheet_name='Rute', index=False)
        #     excel_list_partikel.to_excel(writer, sheet_name='List Partikel', index=False)
        #     excel_list_log_perubahan.to_excel(writer, sheet_name='Log Perubahan', index=False)
        #     # excel_list_all_partikel.to_excel(writer, sheet_name='All Permutasi', index=False)
        #     excel_hasil.to_excel(writer, sheet_name='Hasil Optimal', index=False)

        # print(f"{datetime.today()} End Excel")
        return value_time_rating, optimal_routes, destination_cant_visit, total_time_spend, routes_schedule

    def calculate_pso_excel (self, routes_data, num_particle, destination_data, max_iteration, c1, c2, num_days, skala_awal, skala_akhir, jam_mulai, jam_selesai, judul_itinerary):
        excel_rute_desintasi = pd.DataFrame(routes_data)
        excel_destinasi = pd.DataFrame(destination_data)

        # Buat matrix dan dapatkan urutan label (misal: ['H', 'A', 'B', 'C', 'D'])
        # labels adalah id destinasi id (H untuk hotel)
        distance_matrix, labels = self.create_distance_matrix(routes_data)
        num_destination_to_visit = len(labels) - 1  # karena H tidak dikunjungi

        print(f"{datetime.today()} Create particle")
        #ini yang kepake nanti
        list_particle = [] #atau swarm (kumpulan particle)
        for i in range(num_particle):
            
            # # Pilih acak urutan label destinasi (tanpa 'H')
            position = random.sample(labels[1:], num_destination_to_visit) #list urutan destinasi acak

            value_time_rating, routes, destination_cant_visit, total_time_spend, total_rating_scaled, routes_schedule = self.decode_and_evaluate(
                permutation=position, labels=labels,
                routes_data=routes_data, destionation_data=destination_data,
                num_days=num_days, jam_mulai=jam_mulai, jam_selesai=jam_selesai
            )

            particle = {
                'position': copy.deepcopy(position),
                'pbest_position': copy.deepcopy(position),
                'rute': routes,
                'pbest_fitness': value_time_rating,
                'current_fitness': value_time_rating,
                'destination_cant_visit': destination_cant_visit,
                'total_rating_scaled': total_rating_scaled,
                'routes_schedule': routes_schedule
            }
            list_particle.append(particle)
        
        #hardcode
        # list_position = [
        #     ['D', 'C', 'B', 'A'],  # posisi partikel 1
        #     ['C', 'A', 'D', 'B']  # posisi partikel 2
        # ]
        
        # list_particle = []
        
        # for i in range(num_particle):
        #     position = list_position[i]  # ambil posisi sesuai urutan
        
        #     value_time_rating, routes, destination_cant_visit, total_time_spend, total_rating_scaled, routes_schedule = self.decode_and_evaluate(
        #         permutation=position, labels=labels,
        #         routes_data=routes_data, destionation_data=destination_data,
        #         num_days=num_days, jam_mulai=jam_mulai, jam_selesai=jam_selesai
        #     )
        
        #     particle = {
        #         'position': copy.deepcopy(position),
        #         'pbest_position': copy.deepcopy(position),
        #         'rute': routes,
        #         'pbest_fitness': value_time_rating,
        #         'current_fitness': value_time_rating,
        #         'destination_cant_visit': destination_cant_visit,
        #         'total_rating_scaled': total_rating_scaled,
        #         'routes_schedule': routes_schedule
        #     }
        #     list_particle.append(particle)

        list_particle_snapshot = copy.deepcopy(list_particle)
        excel_list_partikel = pd.DataFrame(list_particle_snapshot)
        print(f"{datetime.today()} End")

        # print(f"{datetime.today()} Start All Permutation")
        # #semua kemungkinan permutasi
        # list_all_particle = []
        # list_position = []
        # for data in list_particle:
        #     position = data.get('position')
        #     list_position.append(position)

        # all_permutations = list(permutations(list_position[0]))  # semua urutan unik

        # for perm in all_permutations:
        #     position = list(perm)

        #     value_time_rating, routes, destination_cant_visit, total_time_spend, total_rating_scaled, routes_schedule = self.decode_and_evaluate(
        #         permutation=position, labels=labels,
        #         routes_data=routes_data, destionation_data=destination_data,
        #         num_days=num_days, jam_mulai=jam_mulai, jam_selesai=jam_selesai
        #     )

        #     particle = {
        #         'position': position,
        #         'pbest_position': position.copy(),
        #         'rute': routes,
        #         # 'waktu' : routes_time,
        #         'pbest_fitness': value_time_rating,
        #         'current_fitness': value_time_rating,
        #         'destination_cant_visit': destination_cant_visit,
        #         # 'total_time_spend' : total_time_spend,
        #         'total_rating_scaled' : total_rating_scaled,
        #         'routes_schedule' : routes_schedule
        #     }
        #     list_all_particle.append(particle)

        # excel_list_all_partikel = pd.DataFrame(list_all_particle)
        # print(f"{datetime.today()} End All Permutation")

        # Initialize global best
        best_particle = min(list_particle, key=lambda p: p['pbest_fitness'])
        gbest_position = best_particle.get('pbest_position')
        gbest_fitness = best_particle.get('pbest_fitness')
        gbest_routes = best_particle.get('rute')
        gbest_cant_visit = best_particle.get('destination_cant_visit')

        log_perubahan = []

        print(f"{datetime.today()} Iterasi loop pbest gbest")
        for iteration in range(max_iteration):
            skala = skala_awal - ((skala_awal - skala_akhir) * (iteration / max_iteration))

            for particle in list_particle:
                # 🔥 SIMPAN POSISI SEBELUM OPERASI APAPUN (DEEP COPY!)
                last_position = copy.deepcopy(particle['position'])  # ← PENTING!
                last_pbest = copy.deepcopy(particle['pbest_position'])  # ← TAMBAHAN
                last_value = copy.deepcopy(particle['current_fitness'])
                last_num_cant_visit = len(particle.get('destination_cant_visit', []))
                
                # Simpan gbest lama juga
                gbest_position_lama = copy.deepcopy(gbest_position)
                last_gbest_cant_visit = len(gbest_cant_visit) if gbest_cant_visit else 0

                # === Pendekatan pbest ===
                for _ in range(int(c1 * random.random() * len(particle['position']) * skala)):
                    idx1, idx2 = random.sample(range(len(particle['position'])), 2)
                    if particle['position'][idx1] != particle['pbest_position'][idx1] or \
                            particle['position'][idx2] != particle['pbest_position'][idx2]:
                        particle['position'][idx1], particle['position'][idx2] = (
                            particle['position'][idx2], particle['position'][idx1]
                        )

                # === Pendekatan gbest ===
                for _ in range(int(c2 * random.random() * len(particle['position']) * skala)):
                    idx1, idx2 = random.sample(range(len(particle['position'])), 2)
                    if particle['position'][idx1] != gbest_position[idx1] or \
                            particle['position'][idx2] != gbest_position[idx2]:
                        particle['position'][idx1], particle['position'][idx2] = (
                            particle['position'][idx2], particle['position'][idx1]
                        )

                # Simpan posisi SETELAH swap untuk logging
                new_position = copy.deepcopy(particle['position'])  # ← DEEP COPY!

                # === Hitung ulang fitness
                value_time_rating, routes, destination_cant_visit, total_time_spend, total_rating_scaled, routes_schedule = self.decode_and_evaluate(
                    permutation=particle['position'], labels=labels,
                    routes_data=routes_data, destionation_data=destination_data,
                    num_days=num_days, jam_mulai=jam_mulai, jam_selesai=jam_selesai
                )
                particle['current_fitness'] = value_time_rating
                new_num_cant_visit = len(destination_cant_visit)

                # === Update pbest ===
                is_pbest_updated = False
                if (new_num_cant_visit < last_num_cant_visit) or \
                (new_num_cant_visit == last_num_cant_visit and value_time_rating < particle['pbest_fitness']):
                    is_pbest_updated = True
                    particle['pbest_fitness'] = value_time_rating
                    particle['pbest_position'] = copy.deepcopy(particle['position'])  # ← DEEP COPY!
                    particle['rute'] = routes
                    particle['waktu'] = total_time_spend
                    particle['total_rating_scaled'] = total_rating_scaled
                    particle['destination_cant_visit'] = destination_cant_visit

                # === Update gbest ===
                is_gbest_updated = False
                if (new_num_cant_visit < last_gbest_cant_visit) or \
                (new_num_cant_visit == last_gbest_cant_visit and value_time_rating < gbest_fitness):
                    is_gbest_updated = True
                    gbest_fitness = value_time_rating
                    gbest_position = copy.deepcopy(particle['position'])  # ← DEEP COPY!
                    gbest_routes = routes
                    gbest_cant_visit = destination_cant_visit

                # LOGGING
                log_perubahan.append({
                    'Iterasi': iteration + 1,
                    'Nomor Partikel': list_particle.index(particle) + 1,
                    
                    # Data SEBELUM swap/update
                    'Urutan Pbest Lama': '-'.join(last_pbest),
                    'Posisi Sebelum Swap': '-'.join(last_position),
                    'Value Pbest Lama': last_value,
                    
                    # Data SETELAH swap
                    'Posisi Setelah Swap': '-'.join(new_position),
                    'Nilai posisi swap' : value_time_rating,
                    'Rute posisi swap' : routes,
                    
                    # Data pbest baru
                    'Urutan Pbest Baru': '-'.join(particle['pbest_position']),
                    'Rute Pbest': particle.get('rute', routes),
                    'Value Pbest Baru': particle['pbest_fitness'],
                    'Status Update Pbest': is_pbest_updated,
                    
                    # Data gbest
                    'Urutan Gbest Lama': '-'.join(gbest_position_lama),
                    'Urutan Gbest': '-'.join(gbest_position),
                    'Rute Gbest': gbest_routes,
                    'Value Gbest': gbest_fitness,
                    'Cant Visit Gbest': gbest_cant_visit,
                    'Status Update Gbest': is_gbest_updated,
                })

        excel_list_log_perubahan = pd.DataFrame(log_perubahan)
        print(f"{datetime.today()} End")

        print(f"{datetime.today()} Start Optimal")
        value_time_rating, optimal_routes, destination_cant_visit, total_time_spend, total_rating_scaled, routes_schedule = self.decode_and_evaluate(
            permutation=gbest_position,
            labels=labels,
            routes_data=routes_data,
            destionation_data=destination_data,
            num_days=num_days, jam_mulai=jam_mulai, jam_selesai=jam_selesai
        )

        # Siapkan dictionary hasil
        hasil_optimal = {
            'Jam Mulai' : jam_mulai,
            'Jam Selesai' : jam_selesai,
            'Kapasitas Hari' : num_days,
            'Total Waktu' : total_time_spend,
            'Koefesien Waktu' : CalculatePSO.koefisien_waktu,
            'Total Rating Scaled' : total_rating_scaled,
            'Koefesien Rating': CalculatePSO.koefisien_rating,
            'Total Value Optimal': value_time_rating,
            'Rute Terbaik': optimal_routes,
            # 'Waktu Rute' : routes_time,
            'Destinasi tidak dikunjungi': destination_cant_visit,
            'routes_schedule': routes_schedule
        }
        excel_hasil = pd.DataFrame([hasil_optimal])
        print(f"{datetime.today()} End Optimal")

        print(f"{datetime.today()} Start Excel")
        timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
        with pd.ExcelWriter(f'{judul_itinerary}_{timestamp}.xlsx', engine='openpyxl') as writer:
            excel_destinasi.to_excel(writer, sheet_name='Destinasi', index=False)
            excel_rute_desintasi.to_excel(writer, sheet_name='Rute', index=False)
            excel_list_partikel.to_excel(writer, sheet_name='List Partikel', index=False)
            excel_list_log_perubahan.to_excel(writer, sheet_name='Log Perubahan', index=False)
            # excel_list_all_partikel.to_excel(writer, sheet_name='All Permutasi', index=False)
            excel_hasil.to_excel(writer, sheet_name='Hasil Optimal', index=False)

        print(f"{datetime.today()} End Excel")
        return value_time_rating, optimal_routes, destination_cant_visit, total_time_spend, routes_schedule

    def calculate_itinerary (self, kapasitas_hari, dict_routes, dict_destination, jam_mulai, jam_selesai, judul_itinerary):
        try:
            num_day = int(kapasitas_hari) #jumlah hari

            # PSO parameters - perlu diuji-coba untuk beberapa nilai yang berbeda
            num_particles = 50 #percobaan rute sebelom pbest gbest
            max_iterations = 500

            c1 = 2.0  # Cognitive coefficient
            c2 = 2.0  # Social coefficient
            # Parameter skala dinamis
            skala_awal = 0.5
            skala_akhir = 0.5

            #c1 untuk komponen pribadi, nilai kecenderungan partikel untuk kembali ke solusi terbaik diri sendiri (pbest)
            #c2 untuk komponen sosial, nilai kecenderungan partikel untuk mengikuti solusi terbaik (gbest)

            #kalo c1 lebi besar dari c2 berarti partikel akan cenderung eksplore
            #kalo c2 lebi besar dari c1 berarti partikel akan mengejar gbest lebi agresif
            #kalo seimbang berarti seimbang antara eksplore pribadi dan sosial

            #beberapa penelitian menyarankan c1+c2 = 4 untuk performa stabil
            print(f"{datetime.today()} Before itinerary")
            value_time_rating, optimal_routes, optimal_particle, total_time_spend, routes_schedule = self.calculate_pso(routes_data=dict_routes, num_particle=num_particles,
                                    destination_data=dict_destination, max_iteration=max_iterations, c1=c1, c2=c2,
                                    num_days=num_day,skala_awal=skala_awal,skala_akhir=skala_akhir, jam_mulai=jam_mulai, jam_selesai=jam_selesai, judul_itinerary=judul_itinerary)
            print(f"{datetime.today()} After itinerary")

            # print('=========== Optimal ==============')
            # print(f'optimal time : {optimal_time_spend}')
            # print(f'optimal route : {optimal_routes}')
            # print(f'destinasi yang tidak dapat dikunjungi : {optimal_particle}')
            # print()
            return value_time_rating, optimal_routes, optimal_particle, total_time_spend, routes_schedule
        except Exception as e:
            print(traceback.format_exc())
            print(f"Error creating itinerary: {e}")
    
    @staticmethod
    def get_routes(hotel_kode, list_obyek_kode):
        try:
            # ambil semua kode yang terlibat
            all_kodes = [hotel_kode] + list_obyek_kode

            # ambil semua kombinasi rute antar lokasi
            jarak_queryset = jarakobyek.objects.filter(
                obyekKODEasal__in=all_kodes,
                obyekKODEtujuan__in=all_kodes
            ).values('obyekKODEasal', 'obyekKODEtujuan', 'obyektempuh')

            dict_routes = list(jarak_queryset)

            # ambil data destinasi (selain hotel)
            obyek_queryset = obyekwisata.objects.filter(
                obyekKODE__in=list_obyek_kode
            ).values('obyekKODE', 'obyekWAKTUKUNJUNG', 'obyekPOPULARITAS', 'obyekLONGITUDE', 'obyekLATITUDE', 'obyekNAMA')

            # mapping otomatis
            kode_map = {'Hotel': hotel_kode}
            for i, kode in enumerate(list_obyek_kode):
                kode_map[chr(65 + i)] = kode  # A, B, C, D, E
                # kode ASCII (angka) menjadi karakter (huruf, simbol, dll)
                # 65 = A
            # buat reverse map untuk mengganti kode ke huruf di hasil query
            reverse_map = {v: k for k, v in kode_map.items()}

            # ubah hasil dict_routes jadi versi singkat
            dict_routes = [
                {
                    'id_asal': reverse_map[item['obyekKODEasal']],
                    'id_tujuan': reverse_map[item['obyekKODEtujuan']],
                    'waktu': item['obyektempuh']
                }
                for item in jarak_queryset
            ]

            # ubah dict_destination juga
            dict_destination = [
                {
                    'id': reverse_map[obj['obyekKODE']],
                    'obyekKODE' : obj.get('obyekKODE'),
                    'nama' : obj.get('obyekNAMA'),
                    'waktu_kunjungan': obj['obyekWAKTUKUNJUNG'],
                    'popularitas': obj['obyekPOPULARITAS'],
                    'latitude': obj.get('obyekLATITUDE'),
                    'longitude': obj.get('obyekLONGITUDE')
                }
                for obj in obyek_queryset
            ]

            return dict_routes, dict_destination, kode_map
        except Exception as e:
            print(traceback.format_exc())
            print(f"Error creating itinerary: {e}")

    def saveItinerary(self, jam_mulai, jam_selesai, hari_input, mapping_destination, destination_cant_visit, user_id, judul_perjalanan, routes_schedule, score):
        try:
            jam_mulai_minutes = CalculatePSO().time_to_minutes(jam_mulai)
            jam_mulai_obj = CalculatePSO().minutes_to_time(jam_mulai_minutes)

            jam_selesai_minutes = CalculatePSO().time_to_minutes(jam_selesai)
            jam_selesai_obj = CalculatePSO().minutes_to_time(jam_selesai_minutes)

            date_now = timezone.now().date()
            akun_user = anggota.objects.filter(anggotaKODE=user_id).first()
            hasil_itinerary = hasilitinerary(
                anggotaKODE = akun_user,
                judul_itinerary = judul_perjalanan,
                jam_mulai = jam_mulai_obj,
                jam_selesai = jam_selesai_obj,
                hari_input=hari_input,
                score = score,
                datecreated = date_now
            )
            hasil_itinerary.save()

            # 2. Simpan setiap hari ke headeritinerary
            for day_index, day_schedule in enumerate(routes_schedule, start=1):
                header = headeritinerary.objects.create(
                    hari=day_index,
                    hasilKODE=hasil_itinerary,
                    jam_mulai=day_schedule['jam_mulai'],
                    jam_selesai=day_schedule['jam_selesai']
                )
                
                # 3. Simpan detail setiap destinasi ke detailitinerary
                for urutan, detail in enumerate(day_schedule['schedule'], start=1):
                    destination_id = detail['destination_id']
                    from_id = detail['from_id']
                    
                    # Cek apakah destinasi ini di-skip
                    if destination_id in destination_cant_visit or from_id in destination_cant_visit:
                        continue
                    
                    # Get kode obyek wisata dari mapping
                    obyek_kode_asal = mapping_destination.get(from_id)
                    obyek_kode_tujuan = mapping_destination.get(destination_id)
                    
                    # Skip jika tidak ada mapping
                    if not obyek_kode_asal or not obyek_kode_tujuan:
                        continue
                    
                    # Get object obyekwisata dari database
                    try:
                        obyek_asal = obyekwisata.objects.get(obyekKODE=obyek_kode_asal)
                        obyek_tujuan = obyekwisata.objects.get(obyekKODE=obyek_kode_tujuan)
                        
                        detailitinerary.objects.create(
                            obyekKODEasal=obyek_asal,
                            obyekKODEtujuan=obyek_tujuan,
                            headerKODE=header,
                            urutan=urutan,
                            jam_mulai=detail['jam_mulai'],
                            jam_selesai=detail['jam_selesai']
                        )
                    except obyekwisata.DoesNotExist:
                        print(f"Warning: Obyek wisata tidak ditemukan: {obyek_kode_asal} atau {obyek_kode_tujuan}")
                        continue
            
            # 4. Simpan destinasi yang tidak bisa dikunjungi ke skipitinerary
            for destination_id in destination_cant_visit:
                obyek_kode = mapping_destination.get(destination_id)
                
                if obyek_kode:
                    try:
                        obyek = obyekwisata.objects.get(obyekKODE=obyek_kode)
                        skipitinerary.objects.create(
                            obyekKODE=obyek,
                            hasilKODE=hasil_itinerary
                        )
                    except obyekwisata.DoesNotExist:
                        print(f"Warning: Obyek wisata tidak ditemukan untuk skip: {obyek_kode}")
                        continue
            
            return hasil_itinerary

        except Exception as e:
            print(traceback.format_exc())
            print(f"Error saving itinerary: {e}")
    
    def create_map_data(self, hasilKODE):
        itinerary = hasilitinerary.objects.filter(hasilKODE=hasilKODE).first()
        skip_itinerary = skipitinerary.objects.filter(hasilKODE=itinerary.hasilKODE)
        header_itinerary = headeritinerary.objects.filter(hasilKODE=itinerary.hasilKODE)
        list_header = list(header_itinerary)

        dict_map = {
            'judul': itinerary.judul_itinerary,
            'tanggal': itinerary.datecreated,
            'skip_destination': list(skip_itinerary),
            'rute': [],
            'all_coordinates': [],
            'jumlah_destinasi': 0
        }

        # Set untuk menyimpan obyek unik
        obyek_unik = set()

        for data in list_header:
            headerKODE = data.headerKODE
            hari = data.hari
            jam_mulai = data.jam_mulai
            jam_selesai = data.jam_selesai

            dict_header = {
                'hari': hari,
                'jam_mulai': jam_mulai,
                'jam_selesai': jam_selesai,
                'rute': [],
                'start_location': None
            }

            detail_itinerary = detailitinerary.objects.filter(headerKODE=headerKODE).order_by('urutan')
            list_detail = list(detail_itinerary)

            # Ambil titik awal (obyek_asal pertama)
            if list_detail and list_detail[0].obyekKODEasal:
                dict_header['start_location'] = list_detail[0].obyekKODEasal

                lat_start = float(list_detail[0].obyekKODEasal.obyekLATITUDE)
                long_start = float(list_detail[0].obyekKODEasal.obyekLONGITUDE)
                dict_map['all_coordinates'].append([lat_start, long_start])

                # Tambahkan ke set unik
                obyek_unik.add(list_detail[0].obyekKODEasal)

            for detail in list_detail:
                dict_detail = {
                    'urutan': detail.urutan,
                    'obyek_asal': detail.obyekKODEasal if detail.obyekKODEasal else None,
                    'obyek_tujuan': detail.obyekKODEtujuan if detail.obyekKODEtujuan else None,
                    'jam_mulai': detail.jam_mulai,
                    'jam_selesai': detail.jam_selesai,
                }
                dict_header['rute'].append(dict_detail)

                # Tambahkan obyek unik (asal & tujuan)
                if detail.obyekKODEasal:
                    obyek_unik.add(detail.obyekKODEasal)
                if detail.obyekKODEtujuan:
                    obyek_unik.add(detail.obyekKODEtujuan)

                # Ambil koordinat dari obyek_tujuan
                if detail.obyekKODEtujuan:
                    lat_koordinat_tujuan = float(detail.obyekKODEtujuan.obyekLATITUDE)
                    long_koordinat_tujuan = float(detail.obyekKODEtujuan.obyekLONGITUDE)
                    dict_map['all_coordinates'].append([lat_koordinat_tujuan, long_koordinat_tujuan])

            dict_map['rute'].append(dict_header)

        # Hitung jumlah destinasi unik
        dict_map['jumlah_destinasi'] = len(obyek_unik)

        # Buat map dengan folium
        map = self.create_map(dict_map=dict_map)

        return dict_map, map

    @staticmethod
    def get_osrm_route(start_coord, end_coord):
        """
        Mendapatkan rute dari OSRM API
        start_coord: [lat, lng]
        end_coord: [lat, lng]
        Returns: list of [lat, lng] coordinates
        """
        try:
            # OSRM menggunakan format lng,lat (bukan lat,lng)
            url = f"http://router.project-osrm.org/route/v1/driving/{start_coord[1]},{start_coord[0]};{end_coord[1]},{end_coord[0]}"
            params = {
                'overview': 'full',
                'geometries': 'geojson'
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data['code'] == 'Ok' and data['routes']:
                    # Ambil koordinat dari geometry
                    coordinates = data['routes'][0]['geometry']['coordinates']
                    # Convert dari [lng, lat] ke [lat, lng]
                    return [[coord[1], coord[0]] for coord in coordinates]
        except Exception as e:
            print(f"Error getting OSRM route: {e}")
        
        # Fallback ke garis lurus jika gagal
        return [start_coord, end_coord]

    def create_map(self, dict_map):
        all_coordinates = dict_map.get('all_coordinates')

        if all_coordinates:
            center_lat = sum([coord[0] for coord in all_coordinates]) / len(all_coordinates)
            center_lng = sum([coord[1] for coord in all_coordinates]) / len(all_coordinates)
        else:
            center_lat, center_lng = -6.2088, 106.8456  # Default Jakarta
        
        map = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=13,
            tiles='OpenStreetMap'
        )

        day_colors = ["#0062FF", "#00FFAA", "#FFA200", "#FF0000", "#4C00FF", "#FF0080", "#00FFE1"]

        # Feature groups untuk setiap hari (untuk toggle)
        feature_groups = []

        for day_idx, day_data in enumerate(dict_map['rute']):
            color = day_colors[day_idx % len(day_colors)]
            
            # Create feature group untuk hari ini
            fg = folium.FeatureGroup(name=f"Hari {day_data['hari']}", show=True)

            # List koordinat untuk routing
            route_coords = []
            marker_number = 1  # Counter untuk nomor marker
            
            # Cek apakah ada destinasi yang kembali ke start location
            start_location = day_data.get('start_location')
            start_lat = float(start_location.obyekLATITUDE) if start_location else None
            start_lng = float(start_location.obyekLONGITUDE) if start_location else None
            
            # Cek destinasi terakhir apakah sama dengan start location
            is_circular_route = False
            if day_data['rute'] and start_location:
                last_dest = day_data['rute'][-1]['obyek_tujuan']
                if last_dest:
                    last_lat = float(last_dest.obyekLATITUDE)
                    last_lng = float(last_dest.obyekLONGITUDE)
                    # Cek apakah koordinat sama (dengan toleransi kecil)
                    if abs(last_lat - start_lat) < 0.0001 and abs(last_lng - start_lng) < 0.0001:
                        is_circular_route = True
            
            # Marker untuk titik awal dengan NOMOR 1
            if start_location:
                lat = start_lat
                lng = start_lng
                route_coords.append([lat, lng])
                
                # Popup untuk titik awal (dengan info tambahan jika circular route)
                popup_html = f"""
                <div style="min-width: 250px; font-family: Arial, sans-serif;">
                    <div style="background-color: {color}; color: white; padding: 10px; margin: -10px -10px 10px -10px; border-radius: 5px 5px 0 0;">
                        <h4 style="margin: 0; font-size: 16px;">
                            <span style="background-color: white; color: {color}; padding: 2px 8px; border-radius: 50%; font-weight: bold; margin-right: 5px;">
                                1
                            </span>
                            {start_location.obyekNAMA}
                        </h4>
                    </div>
                    <div style="padding: 5px 0;">
                        <p style="margin: 5px 0; font-size: 13px;">
                            📍 <strong>Titik Awal {"& Akhir" if is_circular_route else ""}</strong>
                        </p>
                        <div style="background-color: #E8F5E9; padding: 8px; border-radius: 5px; margin: 8px 0;">
                            <p style="margin: 0; font-size: 12px; color: #2E7D32; font-weight: bold;">
                                🏁 Mulai Perjalanan
                            </p>
                            <p style="margin: 5px 0 0 0; font-size: 13px; font-weight: bold;">
                                {day_data['jam_mulai'].strftime('%H:%M')}
                            </p>
                        </div>
                """
                
                # Tambahkan info jam selesai jika circular route
                if is_circular_route:
                    popup_html += f"""
                        <div style="background-color: #FFEBEE; padding: 8px; border-radius: 5px; margin: 8px 0;">
                            <p style="margin: 0; font-size: 12px; color: #C62828; font-weight: bold;">
                                🏁 Kembali ke Titik Awal
                            </p>
                            <p style="margin: 5px 0 0 0; font-size: 13px; font-weight: bold;">
                                {day_data['jam_selesai'].strftime('%H:%M')}
                            </p>
                        </div>
                    """
                
                # Icon dengan NOMOR 1
                icon_html = f"""
                <div style="
                    background-color: {color};
                    color: white;
                    width: 35px;
                    height: 35px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    font-size: 16px;
                    border: 3px solid white;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                ">
                    1
                </div>
                """
                
                tooltip_text = f"{start_location.obyekNAMA} (Titik Awal"
                if is_circular_route:
                    tooltip_text += " & Akhir)"
                else:
                    tooltip_text += ")"
                
                folium.Marker(
                    location=[lat, lng],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=tooltip_text,
                    icon=folium.DivIcon(html=icon_html)
                ).add_to(fg)
                
                marker_number += 1  # Next marker akan nomor 2
            
            # Add markers untuk setiap destinasi (obyek_tujuan)
            # SKIP destinasi terakhir jika sama dengan start location
            destinations_to_process = day_data['rute'][:-1] if is_circular_route else day_data['rute']
            
            for rute_detail in destinations_to_process:
                obyek = rute_detail['obyek_tujuan']
                
                if not obyek:
                    continue
                
                lat = float(obyek.obyekLATITUDE)
                lng = float(obyek.obyekLONGITUDE)
                route_coords.append([lat, lng])
                
                # Format waktu
                jam_mulai_str = rute_detail['jam_mulai'].strftime('%H:%M') if rute_detail['jam_mulai'] else '-'
                jam_selesai_str = rute_detail['jam_selesai'].strftime('%H:%M') if rute_detail['jam_selesai'] else '-'
                
                # Popup content
                popup_html = f"""
                <div style="min-width: 250px; font-family: Arial, sans-serif;">
                    <div style="background-color: {color}; color: white; padding: 10px; margin: -10px -10px 10px -10px; border-radius: 5px 5px 0 0;">
                        <h4 style="margin: 0; font-size: 16px;">
                            <span style="background-color: white; color: {color}; padding: 2px 8px; border-radius: 50%; font-weight: bold; margin-right: 5px;">
                                {marker_number}
                            </span>
                            {obyek.obyekNAMA}
                        </h4>
                    </div>
                    <div style="padding: 5px 0;">
                        <p style="margin: 5px 0; font-size: 13px;">
                            📍 <strong>{obyek.kategoriKODE.kategoriwisataNAMA}</strong>
                        </p>
                        <div style="background-color: #E3F2FD; padding: 8px; border-radius: 5px; margin: 8px 0;">
                            <p style="margin: 0; font-size: 12px; color: #1976D2; font-weight: bold;">
                                🕐 Waktu Kunjungan
                            </p>
                            <p style="margin: 5px 0 0 0; font-size: 13px; font-weight: bold;">
                                {jam_mulai_str} - {jam_selesai_str}
                            </p>
                        </div>
                """
                
                # Add jam buka/tutup jika ada
                if obyek.obyekJAMBUKA and obyek.obyekJAMTUTUP:
                    jam_buka_str = obyek.obyekJAMBUKA.strftime('%H:%M')
                    jam_tutup_str = obyek.obyekJAMTUTUP.strftime('%H:%M')
                    popup_html += f"""
                        <p style="margin: 5px 0; font-size: 12px; color: #666;">
                            Jam Operasional: {jam_buka_str} - {jam_tutup_str}
                        </p>
                    """
                
                # Add info asal
                if rute_detail['obyek_asal']:
                    popup_html += f"""
                        <p style="margin: 5px 0; font-size: 11px; color: #999;">
                            📍 Dari: {rute_detail['obyek_asal'].obyekNAMA}
                        </p>
                    """
                
                popup_html += f"""
                        <p style="margin: 8px 0 0 0; font-size: 11px; color: #999; border-top: 1px solid #eee; padding-top: 5px;">
                            Hari ke-{day_data['hari']} • Destinasi ke-{marker_number}
                        </p>
                    </div>
                </div>
                """
                
                # Create custom marker icon dengan nomor urut
                icon_html = f"""
                <div style="
                    background-color: {color};
                    color: white;
                    width: 35px;
                    height: 35px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    font-size: 16px;
                    border: 3px solid white;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                ">
                    {marker_number}
                </div>
                """
                
                # Add marker
                folium.Marker(
                    location=[lat, lng],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{obyek.obyekNAMA} ({jam_mulai_str} - {jam_selesai_str})",
                    icon=folium.DivIcon(html=icon_html)
                ).add_to(fg)
                
                marker_number += 1
            
            # Jika circular route, tambahkan koordinat start location di akhir untuk routing
            if is_circular_route and start_location:
                route_coords.append([start_lat, start_lng])
            
            # OSRM ROUTING - Buat garis mengikuti jalan
            if len(route_coords) > 1:
                # Untuk setiap segmen rute, dapatkan koordinat detail dari OSRM
                for i in range(len(route_coords) - 1):
                    start_coord = route_coords[i]
                    end_coord = route_coords[i + 1]
                    
                    # Dapatkan rute detail dari OSRM
                    detailed_route = self.get_osrm_route(start_coord, end_coord)
                    
                    # Cek apakah ini segmen terakhir yang kembali ke start (circular route)
                    is_return_segment = (i == len(route_coords) - 2 and is_circular_route)
                    
                    # Gambar polyline mengikuti jalan
                    # Gunakan style berbeda untuk segmen kembali ke start
                    folium.PolyLine(
                        locations=detailed_route,
                        color=color,
                        weight=5,
                        opacity=0.6 if is_return_segment else 0.8,
                        dash_array='10, 5' if is_return_segment else None,  # Garis putus-putus untuk return
                    ).add_to(fg)
            
            fg.add_to(map)
            feature_groups.append(fg)
        
        # Add markers untuk skip destinations (jika ada)
        if dict_map['skip_destination']:
            skip_fg = folium.FeatureGroup(name="❌ Destinasi Tidak Dikunjungi", show=True)
            
            for skip_obj in dict_map['skip_destination']:
                obyek = skip_obj.obyekKODE
                lat = float(obyek.obyekLATITUDE)
                lng = float(obyek.obyekLONGITUDE)
                
                popup_html = f"""
                <div style="min-width: 200px; font-family: Arial, sans-serif;">
                    <div style="background-color: #EF4444; color: white; padding: 10px; margin: -10px -10px 10px -10px; border-radius: 5px 5px 0 0;">
                        <h4 style="margin: 0; font-size: 16px;">❌ {obyek.obyekNAMA}</h4>
                    </div>
                    <div style="padding: 5px 0;">
                        <p style="margin: 5px 0; font-size: 13px;">📍 {obyek.kategoriKODE.kategoriwisataNAMA}</p>
                        <p style="margin: 5px 0; font-size: 12px; color: #EF4444; font-weight: bold;">
                            Tidak dapat dikunjungi
                        </p>
                    </div>
                </div>
                """
                
                folium.Marker(
                    location=[lat, lng],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"❌ {obyek.obyekNAMA}",
                    icon=folium.Icon(color='red', icon='times', prefix='fa')
                ).add_to(skip_fg)
            
            skip_fg.add_to(map)
        
        # Add layer control untuk toggle hari
        folium.LayerControl(collapsed=False).add_to(map)
        
        # Fit bounds ke semua markers
        if all_coordinates:
            map.fit_bounds(all_coordinates)
        
        return map
    
    def create_map_data_basic(self, hasilKODE):
        """Load data dasar tanpa generate map (cepat)"""
        itinerary = hasilitinerary.objects.filter(hasilKODE=hasilKODE).first()
        skip_itinerary = skipitinerary.objects.filter(hasilKODE=itinerary.hasilKODE)
        header_itinerary = headeritinerary.objects.filter(hasilKODE=itinerary.hasilKODE)
        list_header = list(header_itinerary)

        hari_input = itinerary.hari_input or None
        warning = None
        if hari_input:
            if hari_input > len(list_header) :
                warning = f'Perjalanan anda hanya membutuhkan {len(list_header)} hari dari {hari_input} hari yang anda inginkan'

        dict_map = {
            'judul': itinerary.judul_itinerary,
            'tanggal': itinerary.datecreated,
            'skip_destination': list(skip_itinerary),
            'rute': [],
            'all_coordinates': [],
            'jumlah_destinasi': 0,
            'warning' : warning
        }

        obyek_unik = set()

        for data in list_header:
            headerKODE = data.headerKODE
            hari = data.hari
            jam_mulai = data.jam_mulai
            jam_selesai = data.jam_selesai

            dict_header = {
                'hari': hari,
                'jam_mulai': jam_mulai,
                'jam_selesai': jam_selesai,
                'rute': [],
                'start_location': None
            }

            detail_itinerary = detailitinerary.objects.filter(headerKODE=headerKODE).order_by('urutan')
            list_detail = list(detail_itinerary)

            if list_detail and list_detail[0].obyekKODEasal:
                dict_header['start_location'] = list_detail[0].obyekKODEasal
                obyek_unik.add(list_detail[0].obyekKODEasal)

            for detail in list_detail:
                dict_detail = {
                    'urutan': detail.urutan,
                    'obyek_asal': detail.obyekKODEasal if detail.obyekKODEasal else None,
                    'obyek_tujuan': detail.obyekKODEtujuan if detail.obyekKODEtujuan else None,
                    'jam_mulai': detail.jam_mulai,
                    'jam_selesai': detail.jam_selesai,
                }
                dict_header['rute'].append(dict_detail)

                if detail.obyekKODEasal:
                    obyek_unik.add(detail.obyekKODEasal)
                if detail.obyekKODEtujuan:
                    obyek_unik.add(detail.obyekKODEtujuan)

            dict_map['rute'].append(dict_header)

        dict_map['jumlah_destinasi'] = len(obyek_unik)

        # print("Semua obyek unik:", obyek_unik)
        # print("Jumlah obyek unik:", len(obyek_unik))


        return dict_map

    def create_all_destinations_map(self):
        """
        Membuat map yang menampilkan semua objek wisata dengan warna berbeda per kategori
        """
        # Query semua objek wisata yang memiliki koordinat
        all_destinations = obyekwisata.objects.filter(
            obyekLATITUDE__isnull=False,
            obyekLONGITUDE__isnull=False
        ).select_related('kategoriKODE')
        
        # Hitung center map
        if all_destinations.exists():
            lats = [float(obj.obyekLATITUDE) for obj in all_destinations]
            lngs = [float(obj.obyekLONGITUDE) for obj in all_destinations]
            center_lat = sum(lats) / len(lats)
            center_lng = sum(lngs) / len(lngs)
        else:
            center_lat, center_lng = -6.2088, 106.8456  # Default Jakarta
        
        # Buat map
        map = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Warna untuk setiap kategori
        category_colors = {
            'default': '#808080',  # Abu-abu untuk default
        }
        
        # List warna yang akan digunakan
        colors_list = [
            '#0062FF', '#00FFAA', '#FFA200', '#FF0000', 
            '#4C00FF', '#FF0080', '#00FFE1', '#FFD700',
            '#32CD32', '#FF1493', '#00CED1', '#FF6347'
        ]
        
        # Group destinations berdasarkan kategori
        category_groups = {}
        for obj in all_destinations:
            kategori_nama = obj.kategoriKODE.kategoriwisataNAMA if obj.kategoriKODE else 'Tanpa Kategori'
            
            if kategori_nama not in category_groups:
                category_groups[kategori_nama] = []
            
            category_groups[kategori_nama].append(obj)
            
            # Assign warna untuk kategori baru
            if kategori_nama not in category_colors:
                color_index = len(category_colors) - 1  # -1 karena ada 'default'
                category_colors[kategori_nama] = colors_list[color_index % len(colors_list)]
        
        # Buat feature group untuk setiap kategori
        for kategori_nama, destinations in category_groups.items():
            color = category_colors.get(kategori_nama, category_colors['default'])
            
            fg = folium.FeatureGroup(name=f"{kategori_nama} ({len(destinations)})", show=True)
            
            for obj in destinations:
                lat = float(obj.obyekLATITUDE)
                lng = float(obj.obyekLONGITUDE)
                
                # Format jam buka/tutup
                jam_buka_str = obj.obyekJAMBUKA.strftime('%H:%M') if obj.obyekJAMBUKA else '-'
                jam_tutup_str = obj.obyekJAMTUTUP.strftime('%H:%M') if obj.obyekJAMTUTUP else '-'
                
                # Popup content
                popup_html = f"""
                <div style="min-width: 250px; font-family: Arial, sans-serif;">
                    <div style="background-color: {color}; color: white; padding: 10px; margin: -10px -10px 10px -10px; border-radius: 5px 5px 0 0;">
                        <h4 style="margin: 0; font-size: 16px;">{obj.obyekNAMA}</h4>
                    </div>
                    <div style="padding: 5px 0;">
                        <p style="margin: 5px 0; font-size: 13px;">
                            📍 <strong>{kategori_nama}</strong>
                        </p>
                """
                
                # Tambah alamat jika ada
                if obj.obyekALAMAT:
                    popup_html += f"""
                        <p style="margin: 5px 0; font-size: 12px; color: #666;">
                            📌 {obj.obyekALAMAT}
                        </p>
                    """
                
                # Tambah jam operasional
                popup_html += f"""
                    <div style="background-color: #E3F2FD; padding: 8px; border-radius: 5px; margin: 8px 0;">
                        <p style="margin: 0; font-size: 12px; color: #1976D2; font-weight: bold;">
                            🕐 Jam Operasional
                        </p>
                        <p style="margin: 5px 0 0 0; font-size: 13px; font-weight: bold;">
                            {jam_buka_str} - {jam_tutup_str}
                        </p>
                    </div>
                """
                
                # Tambah informasi lainnya
                if obj.obyekWAKTUKUNJUNG:
                    popup_html += f"""
                        <p style="margin: 5px 0; font-size: 12px; color: #666;">
                            ⏱️ Waktu Kunjung: {obj.obyekWAKTUKUNJUNG} menit
                        </p>
                    """
                
                if obj.obyekPOPULARITAS:
                    popup_html += f"""
                        <p style="margin: 5px 0; font-size: 12px; color: #666;">
                            ⭐ Popularitas: {obj.obyekPOPULARITAS}/10
                        </p>
                    """
                
                # Tambah definisi/deskripsi jika ada
                if obj.obyekDEFINISI:
                    definisi_short = obj.obyekDEFINISI[:150] + '...' if len(obj.obyekDEFINISI) > 150 else obj.obyekDEFINISI
                    popup_html += f"""
                        <p style="margin: 8px 0; font-size: 11px; color: #555; font-style: italic;">
                            {definisi_short}
                        </p>
                    """
                
                popup_html += """
                    </div>
                </div>
                """
                
                # Create custom marker icon
                icon_html = f"""
                <div style="
                    background-color: {color};
                    color: white;
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-weight: bold;
                    font-size: 18px;
                    border: 3px solid white;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.3);
                ">
                    📍
                </div>
                """
                
                # Add marker
                folium.Marker(
                    location=[lat, lng],
                    popup=folium.Popup(popup_html, max_width=300),
                    tooltip=f"{obj.obyekNAMA}",
                    icon=folium.DivIcon(html=icon_html)
                ).add_to(fg)
            
            fg.add_to(map)
        
        # Add layer control untuk toggle kategori
        folium.LayerControl(collapsed=False).add_to(map)
        
        # Fit bounds ke semua markers
        if all_destinations.exists():
            bounds = [[float(obj.obyekLATITUDE), float(obj.obyekLONGITUDE)] for obj in all_destinations]
            map.fit_bounds(bounds)
        
        return map