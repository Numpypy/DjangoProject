from django.urls import path,re_path
from . import views
urlpatterns = [
    path('',views.index,name='goods'),
    re_path('detail/(?P<goods_id>\d+)',views.detail,name='detail'),#详情页
    re_path('list/(?P<type_id>\d+)/(?P<page>\d+)$',views.listgoods,name='list'),#列表页

]
