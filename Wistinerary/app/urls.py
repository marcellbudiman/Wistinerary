from django.urls import path
from app import views

urlpatterns = [
    path("", views.HomePage.GetHomeView, name="home"),
    path("error/", views.ErrorPage.GetErrorPage, name="error"),
    path("login/", views.LoginPage.GetLoginView, name="login"),
    path("signup/", views.SignupPage.GetSignupView, name="signup"),
    path("logout/", views.LoginPage.Logout, name="logout"),

    path("admindashboard/", views.AdminPage.GetDashboardView, name="admindashboard"),

    path("tambahprovinsi/", views.AdminPage.GetTambahProvinsiView, name="tambahprovinsi"),
    path("editprovinsi/<str:provinsiKODE>/", views.AdminPage.GetEditProvinsiView, name="editprovinsi"),
    path("deleteprovinsi/<str:provinsiKODE>/", views.AdminPage.GetDeleteProvinsiView, name="deleteprovinsi"),

    path('tambahkabupaten/', views.AdminPage.GetTambahKabupatenView, name='tambahkabupaten'),
    path('editkabupaten/<str:kabupatenKODE>/', views.AdminPage.GetEditKabupatenView, name='editkabupaten'),
    path('deletekabupaten/<str:kabupatenKODE>/', views.AdminPage.GetDeleteKabupatenView, name='deletekabupaten'),

    path('tambahkecamatan/', views.AdminPage.GetTambahKecamatanView, name='tambahkecamatan'),
    path('editkecamatan/<str:kecamatanKODE>/', views.AdminPage.GetEditKecamatanView, name='editkecamatan'),
    path('deletekecamatan/<str:kecamatanKODE>/', views.AdminPage.GetDeleteKecamatanView, name='deletekecamatan'),
    
    path('tambahkategoriberita/', views.AdminPage.GetTambahKategoriberitaView, name='tambahkategoriberita'),
    path('editkategoriberita/<str:kategoriberitaKODE>/', views.AdminPage.GetEditKategoriberitaView, name='editkategoriberita'),
    path('deletekategoriberita/<str:kategoriberitaKODE>/', views.AdminPage.GetDeleteKategoriberitaView, name='deletekategoriberita'),

    path('tambahkategoriwisata/', views.AdminPage.GetTambahKategoriwisataView, name='tambahkategoriwisata'),
    path('editkategoriwisata/<str:kategoriwisataKODE>/', views.AdminPage.GetEditKategoriwisataView, name='editkategoriwisata'),
    path('deletekategoriwisata/<str:kategoriwisataKODE>/', views.AdminPage.GetDeleteKategoriwisataView, name='deletekategoriwisata'),

    path('tambahkegiatan/', views.AdminPage.GetTambahKegiatanView, name='tambahkegiatan'),
    path('editkegiatan/<str:eventKODE>/', views.AdminPage.GetEditKegiatanView, name='editkegiatan'),
    path('deletekegiatan/<str:eventKODE>/', views.AdminPage.GetDeleteKegiatanView, name='deletekegiatan'),

    path('tambahobyekwisata/', views.AdminPage.GetTambahObyekWisataView, name='tambahobyekwisata'),
    path('syncobyekwisata/', views.AdminPage.SyncObyekWisata, name='sync_excel'),
    path('editobyekwisata/<str:obyekKODE>/', views.AdminPage.GetEditObyekWisataView, name='editobyekwisata'),
    path('deleteobyekwisata/<str:obyekKODE>/', views.AdminPage.GetDeleteObyekWisataView, name='deleteobyekwisata'),

    path('tambahberita/', views.AdminPage.GetTambahBeritaView, name='tambahberita'),
    path('editberita/<str:beritaKODE>/', views.AdminPage.GetEditBeritaView, name='editberita'),
    path('deleteberita/<str:beritaKODE>/', views.AdminPage.GetDeleteBeritaView, name='deleteberita'),

    path('jarakobyek/', views.AdminPage.GetTambahJarakObyekView, name='tambahjarakobyek'),
    path('jarakobyek/edit/<int:ruteKODE>/', views.AdminPage.GetEditJarakObyekView, name='editjarakobyek'),
    path('jarakobyek/delete/<int:ruteKODE>/', views.AdminPage.GetDeleteJarakObyekView, name='deletejarakobyek'),

    path("detaildestinasi/<str:obyekKODE>/", views.HomePage.GetDetailDestinasiView, name="detaildestinasi"),
    path("detailkegiatan/<str:eventKODE>/", views.HomePage.GetDetailKegiatanView, name="detailkegiatan"),
    path("detailberita/<str:beritaKODE>/", views.HomePage.GetDetailBeritaView, name="detailberita"),

    path('itineraryform/', views.ItineraryPage.GetItineraryFormPageView, name='itineraryform'),
    path('itinerarydetail/<int:hasilKODE>/', views.ItineraryPage.GetItineraryMapView, name='itinerarydetail'),
    path('api/itinerarydetail/map/<int:hasilKODE>/', views.ItineraryPage.GetItineraryMapDataView, name='itinerarymapdata'),
    path('itineraryhistory/', views.ItineraryPage.GetItineraryHistoryView, name='itineraryhistory'),

     # Halaman map
    path('map/all-destinations/', views.ItineraryPage.GetAllDestinationsMapView, name='map_all_destinations'),

]