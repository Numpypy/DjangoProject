from django.urls import path,re_path
from . import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    path('register',views.register,name='register'),
    # path('register_handle',views.register_handle),
    re_path(r'^active/(?P<token>.*)$',views.active),
    path('login/',views.login,name='login'),
    path('',views.userinfo,name='user'),#用户中心信息页
    # path('order',views.userorder,name='order'),
    re_path(r'^order/(?P<page>\d+)$',views.userorder,name='order'),#用户中心订单页
    path('site',views.usersite,name='site'),#用户中心地址页
    path('logout/',views.logout,name='logout')
]
