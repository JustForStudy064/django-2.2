from django.conf.urls import url
from user.views import RegisterView, ActiveView, LoginView,LogoutView, UserOrderView, UserInfoView, AddressView
from django.urls import path, re_path


app_name = 'user'

urlpatterns = [
    # url(r'^register$', views.register, name='register'),
    # url(r'^register_handle$', views.register_handle, name='register_handle'),
    re_path(r'^register$', RegisterView.as_view(), name='register'),
    re_path(r'^active/(?P<token>.*)$', ActiveView.as_view(), name='active'),
    re_path(r'^login$', LoginView.as_view(), name='login'),
    re_path(r'^$', UserInfoView.as_view(), name='user'),
    re_path(r'^order$', UserOrderView.as_view(), name='order'),
    re_path(r'^address$', AddressView.as_view(), name='address'),
    re_path(r'^logout$', LogoutView.as_view(), name='logout')
]
