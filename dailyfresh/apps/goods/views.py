from django.shortcuts import render
from .models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner,GoodsSKU
from order.models import OrderGoods
from django_redis import get_redis_connection
from django.core.cache import cache
from django.http import HttpResponse,HttpResponseRedirect
from django.core.paginator import Paginator
# Create your views here.
def index(request):#显示首页
    #尝试从缓存中获取数据
    context=cache.get('index_page_data')
    if context is None:
        print('设置缓存')

        #获取商品信息
        types=GoodsType.objects.all()
        #获取首页轮播信息

        goods_banners=IndexGoodsBanner.objects.all().order_by('index')
        #获取首页促销信息
        promotion_banners=IndexPromotionBanner.objects.all().order_by('index')



        #获取首页分类展示信息
        for type in types:
            image_banners=IndexTypeGoodsBanner.objects.filter(type=type,display_type=1).order_by('index')
            title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')
            #动态给对象type增加属性
            type.image_banners=image_banners
            type.title_banners=title_banners



        context = {'types': types,
                   'goods_banners': goods_banners,
                   'promotion_banners': promotion_banners,}

        #设置缓存 key value time
        cache.set('index_page_data',context,3600)




    #获取用户购物车中上商品的数目
    user=request.user
    if user.is_authenticated:
        conn=get_redis_connection('default')
        cart_key=f"cart_{user.id}"
        #获取购物车商品数目
        cart_count=conn.hlen(cart_key)
    else:
        cart_count=0

    #组织上下文
    context.update(cart_count=cart_count)
    # context={'types':types,
    #          'goods_banners':goods_banners,
    #          'promotion_banners':promotion_banners,
    #          'cart_count':cart_count
    #          }
    return render(request,'goods/index.html',context)


#/goods/detail/商品id
def detail(request,goods_id):
    try:
        sku=GoodsSKU.objects.get(id=goods_id)
    except:
        #商品不存在
        return HttpResponseRedirect('/goods')

    #获取商品的分类信息
    types=GoodsType.objects.all()

    #获取评论信息
    sku_orders=OrderGoods.objects.filter(sku=sku).exclude(comment='')
    #获取新品信息
    new_skus=GoodsSKU.objects.filter(type=sku.type).order_by('-creat_time')[:2]

    #获取同一SPU的其他商品
    same_spu_skus=GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

    # 获取用户购物车中上商品的数目
    user = request.user
    if user.is_authenticated:
        conn = get_redis_connection('default')
        cart_key = f"cart_{user.id}"
        # 获取购物车商品数目
        cart_count = conn.hlen(cart_key)

        #添加历史浏览记录
        conn=get_redis_connection('default')
        history_key=f"history_{user.id}"
        conn.lrem(history_key,0,goods_id)#移除可能存的goods_id记录
        conn.lpush(history_key,goods_id)#在列表左边重新插入浏览过的goods_id
        conn.ltrim(history_key,0,4)#闭区间，只要列表前五的长度，毕竟只显示五个记录
    else:
        cart_count = 0



    context={'sku':sku,
             'types':types,
             'sku_orders':sku_orders,
             'new_skus':new_skus,
             'same_spu_skus':same_spu_skus,
             'cart_count':cart_count
             }
    return render(request,'goods/detail.html',context)

#需要传入种类信息  页码 排序方式
#/list/种类id/页码/排序方式
def listgoods(request,type_id,page):#列表页
    try:
        type=GoodsType.objects.get(id=type_id)
    except:
        return HttpResponseRedirect('/goods')

    types = GoodsType.objects.all()  # 商品类别信息
    #获取排序方式
    #如果sort 为default 按id排序吗，如果等于price按价格排序，如果等于hot，按人气排序（销量）
    sort=request.GET.get('sort')

    if sort=='price':
        skus = GoodsSKU.objects.filter(type=type).order_by('price')  # 商品
    elif sort=='hot':
        skus = GoodsSKU.objects.filter(type=type).order_by('-sales')  # 商品
    else:
        sort='default'
        skus = GoodsSKU.objects.filter(type=type).order_by('-id')  # 商品

    #分页
    paginator=Paginator(skus,1)
    #获取第page页的内容
    try:
        page=int(page)
    except:
        page=1

    if page>paginator.num_pages:
        page=1

    skus_page=paginator.page(page)#获取page页的内容

    #页码控制
    #1.总页数小于5页，全部显示
    #2.当前页前三页，显示1-5页
    #3.如果是后三页，显示后5页
    #4.其他情况，当前页和前后各两页 一共五页
    num_pages=paginator.num_pages
    if num_pages<5:
        pages=range(1,num_pages+1)
    elif page<=3:
        pages=range(1,6)
    elif page>=num_pages-2:
        pages=range(num_pages-4,num_pages+1)
    else:
        pages=range(page-2,page+3)




    new_skus = GoodsSKU.objects.filter(type=type).order_by('-creat_time')[:2]#新品信息

    #购物车数目
    user = request.user
    if user.is_authenticated:
        conn = get_redis_connection('default')
        cart_key = f"cart_{user.id}"
        # 获取购物车商品数目
        cart_count = conn.hlen(cart_key)


    #组织模板
    context={
        'type':type,
        'types':types,
        'skus_page':skus_page,
        'new_skus':new_skus,
        'cart_count':cart_count,
        'pages':pages,
        'sort':sort,
    }

    return render(request,'goods/list.html',context)
