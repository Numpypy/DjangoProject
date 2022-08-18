from django.urls import path,re_path
from . import views

urlpatterns = [
    path('place',views.orderplace,name='place'),#提交订单页面
    path('commit',views.ordercommit,name='commit'), #订单创建
    path('pay',views.orderpay,name='pay'),#订单支付,
    path('check',views.ordercheck,name='check'),#查询订单支付是否成功
    re_path('comment/(?P<order_id>.+)$',views.ordercomment,name='comment')#评论

]
