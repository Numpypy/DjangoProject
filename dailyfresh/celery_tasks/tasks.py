#使用celery
import os

import jwt
from celery import Celery, app
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render
from django.template import loader,RequestContext






# import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
# django.setup()

from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner


app=Celery('celery_tasks.tasks',broker='redis://:123456@192.168.43.31:6379/8')
import time
@app.task
def send_register_active_email(to_email,username,token):#发送邮件


    subject = '天天生鲜欢迎信息'
    meseage = f"<h1>{username},欢迎你成为天天生鲜注册会员</h1>请点击下方链接激活您的账户<br><a href='http://127.0.0.1:8000/user/active/{token}'>http://127.0.0.1:8000/user/active/{token}</a>"
    reciver = [to_email]
    # reciver = ['1627757578@qq.com']

    send_mail(subject=subject, message='', html_message=meseage, from_email='1627757578@qq.com', recipient_list=reciver)
    time.sleep(5)



@app.task
def generate_static_index_html():
    """产生首页静态页面"""

    # 获取商品的种类信息
    types = GoodsType.objects.all()

    # 获取首页轮播商品信息
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')

    # 获取首页促销活动信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

    # 获取首页分类商品展示信息
    for typ in types:  # GoodsType
        # 获取type种类首页分类商品的图片展示信息
        image_banners = IndexTypeGoodsBanner.objects.filter(type=typ, display_type=1).order_by('index')
        # 获取type种类首页分类商品的文字展示信息
        title_banners = IndexTypeGoodsBanner.objects.filter(type=typ, display_type=0).order_by('index')

        # 动态给type增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
        typ.image_banners = image_banners
        typ.title_banners = title_banners

    # 组织模板上下文
    context = {'types': types,
               'goods_banners': goods_banners,
               'promotion_banners': promotion_banners}

    # 使用模板
    # 1.加载模板文件,返回模板对象
    temp = loader.get_template('static_index.html')
    # 2.模板渲染
    static_index_html = temp.render(context)

    # 生成首页对应静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w', encoding='utf-8') as f:
        f.write(static_index_html)