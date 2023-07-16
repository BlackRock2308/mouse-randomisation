from django.urls import path
from . import views


urlpatterns = [
  
    path('', views.home, name = "home"),
    path('display/', views.display, name = 'display'),
    path('choice/', views.choix_souris, name = 'choice'),
    path('groupe/', views.choix_groupe_souris, name = 'groupe'),
    path('random_group/', views.creating_random_group_view, name='random_group'),
    path('resultat_choix/', views.pdf_report_create, name='create_pdf'),
    path('deleted_souris/', views.deleted_souris_view, name='deleted_souris'),
    path('eliminated_souris/', views.pdf_report_create_deleted_souris, name='create_pdf_elimaned'),
    
]