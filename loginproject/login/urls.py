from django.conf.urls import url
from .views import *

# # FBV模式
# urlpatterns = [
#     url(r'^index/', index,name='index'),
#     url(r'^login/', login,name='login'),
#     url(r'^register/', register,name='register'),
#     url(r'^logout/', logout,name='logout'),
#     url(r'^confirm/$', user_confirm,name='confirm'),
#     url(r'^content/',  content,name='content'),
# ]

# CBV模式
urlpatterns = [
    url(r'^index/', IndexView.as_view(),name='index'),
    url(r'^login/', LoginView.as_view(),name='login'),
    url(r'^register/', RegisterView.as_view(),name='register'),
    url(r'^logout/', LogoutView.as_view(),name='logout'),
    url(r'^confirm/$', UserConfirmView.as_view(),name='confirm'),
    url(r'^content/',  ContentView.as_view(),name='content'),
]