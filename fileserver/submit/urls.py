from django.urls import path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload, name='upload'),
    path('list/', views.measurements_list, name='measurements_list'),
    path('ddetails/<int:fsid>/', views.datadetail, name='datadetail'),
    path('fdetails/<int:fsid>/', views.formdetail, name='formdetail'),
    path('maintenance/', views.maintenance, name='maintenance'),
    path('deleteproject/<int:pid>/', views.delete_project, name='deleteproject'),
    path('dfilesend/<int:fsid>/', views.senddatafile, name='datafilesend'),
    path('ffilesend/<int:fsid>/', views.sendformfile, name='formfilesend'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('statuschange/', views.statuschange, name='statuschange'),
    path('dataget/', views.dataget, name='dataget'),
    path('submissions/', views.get_submissions, name='submissions'),
    path('submission/<int:mid>/', views.get_submission, name='submission_uid'),
    path('field/<int:mid>/', views.get_field_data_id, name='field_id'),
    path('dataseries/<int:mid>/<int:series_num>/',views.get_data_series, name='series'),
]
