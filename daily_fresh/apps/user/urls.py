from django.conf.urls import url
from user.views import RegisterView, ActiveView,LoginView
from django.urls import path,re_path
app_name = 'user'

urlpatterns = [
    # url(r'^register$', views.register, name='register'),
    # url(r'^register_handle$', views.register_handle, name='register_handle'),
    re_path(r'^register$', RegisterView.as_view(), name='register'),
    re_path(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),
    re_path(r'^login$', LoginView.as_view(), name='login')
]
