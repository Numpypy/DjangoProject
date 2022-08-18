from django.shortcuts import render
from django.http import HttpResponseRedirect,JsonResponse
from goods.models import GoodsSKU
from django_redis import get_redis_connection
from django.contrib.auth.decorators import login_required

# Create your views here.

def cartadd(request):

    if request.method=='POST':
        #接收数据
        user=request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        sku_id=request.POST.get('sku_id')
        count=request.POST.get('count')


        #校验数据
        if not all([sku_id,count]):
            return JsonResponse({'res':1,'errmsg':'数据不完整'})
        try:
            count=int(count)
        except:
            #数目出错
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})
        #校验商品是否存在
        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})



        #业务处理
         #检验该商品是否在redis已有数据，有则加，没则新建数据
        conn=get_redis_connection('default')
        cart_key=f"cart_{user.id}"
        cart_count=conn.hget(cart_key,sku_id)
        if cart_count:
            count=int(cart_count)+count
        #设置值

        #检验库存
        if count>sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        conn.hset(cart_key,sku_id,count)

        #获取用户已有的购物车条目数
        total_count=conn.hlen(cart_key)

        #应答
        return JsonResponse({'res':'5','message':'添加成功','total_count':total_count})



@login_required
def cartinfo(request):#购物车页面
    if request.method=='GET':
        #获取用户信息
        user=request.user
        #获取购物车商品信息
        conn=get_redis_connection('default')
        cart_key=f"cart_{user.id}"
        cart_dict=conn.hgetall(cart_key)
        skus=[]
        total_count=0 #总数目
        total_price=0 #总价格
        #遍历获取商品信息
        for sku_id,count in cart_dict.items():
            sku=GoodsSKU.objects.get(id=sku_id)
            amount=sku.price*int(count) #小计
            sku.amount=amount #为sku对象增添属性
            sku.count=int(count)
            skus.append(sku)
            total_count+=int(count)
            total_price+=amount

        context={'skus':skus,'total_count':total_count,'total_price':total_price}



        return render(request,'cart/cart.html',context)

#更新购物车记录、、cart/update
def cartupdate(request):
    if request.method=='POST':
        user=request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 校验数据
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})
        try:
            count = int(count)
        except:
            # 数目出错
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})
        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        #业务处理
        conn=get_redis_connection('default')
        cart_key=f"cart_{user.id}"

        #校验库存
        if count>sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        #更新数据
        conn.hset(cart_key,sku_id,count)

        #计算购物车总件数
        vals=conn.hvals(cart_key)
        total_count=0
        for i in vals:
            total_count+=int(i)



        return JsonResponse({'res': 5,'total_count':total_count,'msg': '更新成功'})



def cartdelete(request):
    if request.method=='POST':
        user=request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        sku_id = request.POST.get('sku_id')
        # 校验数据
        if not all([sku_id]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

        conn=get_redis_connection('default')
        cart_key=f"cart_{user.id}"
        conn.hdel(cart_key,sku_id)

        # 计算购物车总件数
        vals = conn.hvals(cart_key)
        total_count = 0
        for i in vals:
            total_count += int(i)

        return JsonResponse({'res': 3,'total_count':total_count,'msg': '删除成功'})