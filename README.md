# Wistinerary
Aplikasi Rekomendasi Rute Perjalanan
1. Ekstrak folder Wistinerary.zip yang didapatkan langsung dari perancang.
2. Melakukan instalasi Visual Studio Code yang dapat dilakukan dengan mengunjungi laman resmi https://code.visualstudio.com/ .
3. Melakukan instalasi MySQL Workbench melalui laman resmi https://dev.mysql.com.
4. Membuat skema database dengan nama wistinerary dan melakukan import data dengan file SQL yang didapatkan dari perancang.
5. Melakukan instalasi Python melalui laman resmi https://www.python.org.
6.Buka folder Wistinerary dengan Visual Studi Code dan lakukan instalasi library yang dibutuhkan pada terminal dengan cara
    a. pip install pandas
    b. pip install numpy
    c. pip install openpyxl
    d. pip install django
    e. pip install mysqlclient
7. Pada terminal jalankan command “py manage.py migrate”. Command ini bertujuan untuk membuat tabel pada skema database
8. Pada terminal jalankan “py manage.py runserver”. Command ini bertujuan untuk menjalankan server dan akan menghasilkan link lokal untuk menjalankan aplikasi
9. Jalankan tautan lokal yang diberikan (http://127.0.0.1:8000/) pada browser