from django.urls import path
from . import views
urlpatterns = [
    path('add',views.cartadd,name='add'),
    path('',views.cartinfo,name='show'),
    path('update',views.cartupdate,name='update'),
    path('delete',views.cartdelete,name='delete')
]
