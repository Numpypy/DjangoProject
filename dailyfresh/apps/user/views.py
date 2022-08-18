import jwt
from django.shortcuts import render
from django.http import HttpResponse,HttpResponseRedirect
import re
# Create your views here.
from .models import User,Address
from django.conf import settings
from django.core.mail import send_mail
from celery_tasks.tasks import send_register_active_email
from django.contrib.auth import authenticate,login as logins,logout as logouts
from django.contrib.auth.decorators import login_required
from django_redis import get_redis_connection
from goods.models import GoodsSKU
from order.models import  OrderInfo,OrderGoods
from django.core.paginator import Paginator


def register(request):#显示注册页面
    if request.method=='GET':
        return render(request,'user/register.html')



    
    elif request.method=='POST':
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 数据校验
        if not all([username, password, email]):
            return render(request, 'user/register.html', {'errmsg': '数据不完整'})
        if not re.match('^[a-zA-Z0-9_.-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.(com|cn|net)$', email):
            return render(request, 'user/register.html', {'errmsg': '邮箱格式不正确'})
        if allow != 'on':
            return render(request, 'user/register.html', {'errmsg': '请同意协议'})
        try:
            user = User.objects.get(username=username)
        except:
            user = None
        if user:
            return render(request, 'user/register.html', {'errmsg': '用户名已存在'})
        else:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.is_active = 0
            user.save()

            #加密
        key=settings.SECRET_KEY
        data={'confirm':user.id}
        header = {'alg': 'HS256'}
        token=jwt.encode(headers=header,payload=data,key=key)
        token = token.decode() #转换为非bytes字符串 默认参数为'uft8'

        # subject='天天生鲜欢迎信息'
        # meseage=f"<h1>{user.username},欢迎你成为天天生鲜注册会员</h1>请点击下方链接激活您的账户<br><a href='http://127.0.0.1:8000/user/active/{token}'>http://127.0.0.1:8000/user/active/{token}</a>"
        # reciver=[email]
        #
        # send_mail(subject=subject,message='',html_message=meseage,from_email='1627757578@qq.com',recipient_list=reciver)

        send_register_active_email.delay(email,username,token)
            
        return HttpResponseRedirect('/goods')


def active(request,token):
    #解密
    try:
        info = jwt.decode(token, settings.SECRET_KEY)
        user_id=info['confirm']
        use=User.objects.get(id=user_id)
        use.is_active=1
        use.save()
        return HttpResponseRedirect('/user/login')
    except:
        return HttpResponse('激活失败')


def login(request):
    if request.method=='GET':

        #判断是否记住了用户名
        if 'username' in request.COOKIES:
            username=request.COOKIES.get('username')
            checked='checked'
        else:
            username=''
            checked=''
        return render(request,'user/login.html',locals())
    elif request.method=='POST':
        username=request.POST['username']
        password=request.POST['pwd']
        if not all([username,password]):
            return render(request,'user/login.html',{'errmsg':'数据不完整'})

        user=authenticate(username=username,password=password)
        if user is not None:
            if user.is_active:
                logins(request, user)
                # 登录后要跳转的地址
                next_url = request.GET.get('next', '/goods')
                response=HttpResponseRedirect(next_url)


                #判断是否记住用户名
                remember=request.POST.get('remember')
                if remember=='on':
                    response.set_cookie('username',username,7*24*3600)
                else:
                    response.delete_cookie('username')
                return response


                # return HttpResponseRedirect('/goods')
            else:
                return render(request, 'user/login.html', {'errmsg': '账户未激活'})


        else:
            return render(request, 'user/login.html', {'errmsg': '用户名或密码错误'})

def logout(request):
    #清除session
    logouts(request)
    return HttpResponseRedirect('/goods/')






@login_required
def userinfo(request):
    result='info'
    user =request.user
    address=Address.objects.get_default_address(user)
    #用户个人信息，历史浏览记录
    # from redis import StrictRedis

    con=get_redis_connection('default')

    history_key=f"history_{user.id}"
    #获取最近五个id
    sku_ids=con.lrange(history_key,0,4)
    #从数据库中查具体信息
    goods_li=[]
    for id in sku_ids:
        goods=GoodsSKU.objects.get(id=id)
        goods_li.append(goods)

    context={'page':result,'address':address,'goods_li':goods_li}



    return render(request,'user/user_center_info.html',context)





@login_required
def userorder(request,page):
    if request.method=='GET':
        result='order'
        user=request.user
        #获取订单信息
        orders=OrderInfo.objects.filter(user=user)

        #遍历获取订单商品信息
        for order in orders:
            order_skus=OrderGoods.objects.filter(order_id=order.order_id)#根据order_id来查
            #遍历计算小计
            for order_sku in order_skus:
                amount=order_sku.price*order_sku.count
                order_sku.amount=amount#动态增加属性

            order.order_skus=order_skus#动态增加属性保存订单商品信息
            pay_status = OrderInfo.PRDER_STATUS[str(order.order_status)]
            order.pay_status=pay_status

        # 分页 同goods/view中的
        paginator=Paginator(orders,1)#每页显示一个订单

        try:
            page = int(page)
        except:
            page = 1

        if page > paginator.num_pages:
            page = 1

        order_page = paginator.page(page)  # 获取page页的内容

        # 页码控制
        # 1.总页数小于5页，全部显示
        # 2.当前页前三页，显示1-5页
        # 3.如果是后三页，显示后5页
        # 4.其他情况，当前页和前后各两页 一共五页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif page >= num_pages - 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)



        #组织上下文
        context={'order_page':order_page,
                 'pages':pages,
                 'page':result
                 }




        return render(request, 'user/user_center_order.html',context)

# @login_required
# def userorder(request):
#     result = 'order'
#     return render(request, 'user/user_center_order.html', {'page':result})
@login_required
def usersite(request):
    result='site'

    if request.method=='GET':
        user = request.user
        # 默认收货地址
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except:
        #     address = None
        address = Address.objects.get_default_address(user)


        return render(request, 'user/user_center_site.html',{'page':result,'address':address})
    elif request.method=='POST':
        receiver=request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')
        #校验数据
        if not all([receiver,phone,zip_code,addr]):
            return render(request,'user/user_center_site.html',{'errmsg':'数据不完整'})
        #校验手机号
        if not re.match('^1(3[0-9]|4[01456879]|5[0-35-9]|6[2567]|7[0-8]|8[0-9]|9[0-35-9])\d{8}$',phone):
            return render(request, 'user/user_center_site.html', {'errmsg': '手机号码格式不正确'})
        #地址添加 有默认地址则不变，没有则添加的作为默认地址

        user=request.user
        # try:
        #     address=Address.objects.get(user=user,is_default=True)
        # except:
        #     address=None
        address=Address.objects.get_default_address(user)
        if address:
            is_default=False
        else:
            is_default=True

        #添加地址
        Address.objects.create(user=user,receiver=receiver,addr=addr,zip_code=zip_code,phone=phone,is_default=is_default)

        #返回应答
        return HttpResponseRedirect('/user/site')



