from apps.goods import views
from django.urls import path,re_path
app_name = 'goods'

urlpatterns = [
    re_path(r'^index$', views.index, name='index')
]
