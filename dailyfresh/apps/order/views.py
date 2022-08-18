from django.shortcuts import render
from django.http import HttpResponseRedirect,HttpResponse,JsonResponse
from goods.models import GoodsSKU
from user.models import Address
from django_redis import get_redis_connection
from django.contrib.auth.decorators import login_required
from .models import OrderInfo,OrderGoods
from datetime import datetime
from django.db import transaction
from alipay import AliPay
from django.conf import settings
import os
from .models import  OrderInfo,OrderGoods
from django.urls import reverse

# Create your views here.
#/order/place
@login_required
def orderplace(request):#提交订单页面
    if request.method=='POST':
        #获取参数
        sku_ids=request.POST.getlist('sku_ids')
        user=request.user
        #检验参数
        if not sku_ids:
            return HttpResponseRedirect('/cart')

        conn=get_redis_connection('default')
        cart_key=f"cart_{user.id}"
        skus=[]
        total_count=0 #总件数总价格
        total_price=0
        #获取用户要购买的商品
        for sku_id in sku_ids:
            sku=GoodsSKU.objects.get(id=sku_id)

            #获取数量
            count=conn.hget(cart_key,sku_id)
            #计算小计

            amount=int(count)*int(sku.price)

            #增添属性，方便去模板传递使用
            sku.count=int(count)
            sku.amount=amount
            skus.append(sku)
            total_count+=int(count)
            total_price+=int(amount)

    #运费在实际开发的子系统10
        transit_price=10

        total_pay=transit_price+total_price #实付款

        #获取地址
        addrs=Address.objects.filter(user=user)


        #组织上下文
        sku_ids=','.join(sku_ids)
        context={'skus': skus,
                 'transit_price':transit_price,
                 'total_price':transit_price,
                 'total_count':total_count,
                 'addrs':addrs,
                 'total_pay':total_pay,
                 'sku_ids':sku_ids
                 }
        return render(request,'order/place_order.html',context)
    elif request.method=='GET':
        return render(request,'order/place_order.html')

#前端传的参数 地址 支付方式 商品
# @transaction.atomic
# def ordercommit(request):   #悲观锁方案
#     if request.method=='POST':
#         user=request.user
#         if not user.is_authenticated:#未登录
#             return JsonResponse({'res':0,'errmsg':'用户未登录'})
#
#         #接收参数
#         addr_id=request.POST.get('addr_id')
#         pay_method=request.POST.get('pay_method')
#         sku_ids=request.POST.get('sku_ids')
#
#         if not all([addr_id,pay_method,sku_ids]):
#             return JsonResponse({'res': 1, 'errmsg': '参数不完整'})
#         #校验支付方式
#         if pay_method not in OrderInfo.PAY_METHOD.keys():
#             return JsonResponse({'res': 2, 'errmsg': '非法支付方式'})
#
#         #检验地址
#         try:
#             addr=Address.objects.get(id=addr_id)
#         except:
#             return JsonResponse({'res': 3, 'errmsg': '地址非法'})
#
#         # todo:创建订单核心业务
#         #组织参数
#         order_id=datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)
#         transit_price=10
#         total_count=0
#         total_price=0
#
#
#         #todo 设置事务保存点
#         save_id=transaction.savepoint()
#
#         try:
#             # todo:向df_order_info中添加一条记录
#             order=OrderInfo.objects.create(order_id=order_id,
#                                            user=user,addr=addr,
#                                            pay_method=pay_method,
#                                            total_price=total_price,
#                                            total_count=total_count,
#                                            transit_price=transit_price
#                                            )
#
#
#             #todo:用户订单中有几个商品就要向df_order_goods表中加入几条记录
#             conn=get_redis_connection('default')
#             cart_key=f"cart_{user.id}"
#             sku_ids=sku_ids.split(',')
#             for sku_id in sku_ids:#获取商品信息
#                 try:
#                     sku=GoodsSKU.objects.select_for_update().get(id=sku_id)  #todo:悲观锁！！！！！
#                 except:
#                     transaction.savepoint_rollback(save_id)
#                     return JsonResponse({'res': 4, 'errmsg': '商品不存在'})
#
#                 #redis获取商品数量
#                 count=conn.hget(cart_key,sku_id)
#
#
#                 #todo:mysql事务操作
#                 #todo:判断商品的库存(考虑用户同时下单的情况)
#                 if int(count)>sku.stock:
#                     transaction.savepoint_rollback(save_id)
#                     return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})
#
#                 #向表中加记录
#                 OrderGoods.objects.create(order=order,
#                                           sku=sku,
#                                           count=count,
#                                           price=sku.price
#                                           )
#                 #更新库存销量
#                 sku.stock-=int(count)
#                 sku.sales+=int(count)
#                 sku.save()
#
#                 #todo:累加计算订单商品的总数量总价格
#                 amount=sku.price*int(count)
#                 total_price+=amount
#                 total_count+=int(count)
#
#             #todo:更新订单信息表中的商品的总数量总价格
#             order.total_count=total_count
#             order.total_price=total_price
#             order.save()
#         except:
#             transaction.savepoint_rollback(save_id)
#             return JsonResponse({'res':7,'errmsg':'下单失败'})
#
#         #todo 没有问题提交事务
#         transaction.savepoint()
#
#
#         #todo:清除购物车记录redis
#         conn.hdel(cart_key,*sku_ids)
#
#         #返回应答
#         return JsonResponse({'res': 5, 'errmsg': '创建成功'})


@transaction.atomic
def ordercommit(request):   #乐观锁方案
    if request.method=='POST':
        user=request.user
        if not user.is_authenticated:#未登录
            return JsonResponse({'res':0,'errmsg':'用户未登录'})

        #接收参数
        addr_id=request.POST.get('addr_id')
        pay_method=request.POST.get('pay_method')
        sku_ids=request.POST.get('sku_ids')

        if not all([addr_id,pay_method,sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})
        #校验支付方式
        if pay_method not in OrderInfo.PAY_METHOD.keys():
            return JsonResponse({'res': 2, 'errmsg': '非法支付方式'})

        #检验地址
        try:
            addr=Address.objects.get(id=addr_id)
        except:
            return JsonResponse({'res': 3, 'errmsg': '地址非法'})

        # todo:创建订单核心业务
        #组织参数
        order_id=datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)
        transit_price=10
        total_count=0
        total_price=0


        #todo 设置事务保存点
        save_id=transaction.savepoint()

        try:
            # todo:向df_order_info中添加一条记录
            order=OrderInfo.objects.create(order_id=order_id,
                                           user=user,addr=addr,
                                           pay_method=pay_method,
                                           total_price=total_price,
                                           total_count=total_count,
                                           transit_price=transit_price
                                           )


            #todo:用户订单中有几个商品就要向df_order_goods表中加入几条记录
            conn=get_redis_connection('default')
            cart_key=f"cart_{user.id}"
            sku_ids=sku_ids.split(',')
            for sku_id in sku_ids:#获取商品信息
                for i in range(3):#尝试三次
                    try:
                        sku=GoodsSKU.objects.get(id=sku_id)
                    except:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                    #redis获取商品数量
                    count=conn.hget(cart_key,sku_id)


                    #todo:mysql事务操作
                    #todo:判断商品的库存(考虑用户同时下单的情况)
                    if int(count)>sku.stock:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                    #更新库存销量 todo:这个更新方法取消采用乐观锁
                    # sku.stock-=int(count)
                    # sku.sales+=int(count)
                    # sku.save()

                    #todo 乐观锁！！！！！
                    orgin_stock=sku.stock
                    orgin_sales=sku.sales
                    new_stock=orgin_stock-int(count)
                    newsales=orgin_sales+int(count)

                    # print(f"user:{user.id},stock:{sku.stock},times:{i}")  todo 做测试的代码
                    # import time
                    # time.sleep(10)

                    #update df_order_goods set stock=new_stock,sales=new_sales
                    #where id=sku_id,stock=orgin_stock,sales=orgin_sales
                    res=GoodsSKU.objects.filter(id=sku_id,stock=orgin_stock).update(stock=new_stock,sales=newsales)
                    if res==0:#失败
                        if i==2:#尝试的第三次都没有成功
                            return JsonResponse({'res': 8, 'errmsg': '下单失败'})
                            transaction.savepoint_rollback(save_id)#回滚
                        continue


                    #向表中加记录
                    OrderGoods.objects.create(order=order,
                                              sku=sku,
                                              count=count,
                                              price=sku.price
                                              )


                    #todo:累加计算订单商品的总数量总价格
                    amount=sku.price*int(count)
                    total_price+=amount
                    total_count+=int(count)

                    #todo 跳出循环
                    break

            #todo:更新订单信息表中的商品的总数量总价格
            order.total_count=total_count
            order.total_price=total_price
            order.save()
        except:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res':7,'errmsg':'下单失败'})

        #todo 没有问题提交事务
        transaction.savepoint()


        #todo:清除购物车记录redis
        conn.hdel(cart_key,*sku_ids)

        #返回应答
        return JsonResponse({'res': 5, 'errmsg': '创建成功'})


#/order/pay
def orderpay(request):#订单支付
    if request.method=='POST':
        #用户是否登录
        user=request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        #接收参数
        order_id=request.POST.get('order_id')
        #校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效订单id'})
        try:
            order=OrderInfo.objects.get(order_id=order_id,user=user,pay_method=3,order_status=1)
        except:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        #业务处理 使用Python sdk调用支付接口


        alipay = AliPay(
            appid="2021000121645617",  # 订单id
            app_notify_url=None,  # 默认回调url
            app_private_key_string=open(os.path.join(settings.BASE_DIR, "apps/order/app_private_key.pem")).read(),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=open(os.path.join(settings.BASE_DIR, "apps/order/alipay_public_key.pem")).read(),
            sign_type="RSA2",  # RSA 或者 RSA2, 签名
            debug=True,  # 默认False, 沙箱模式需改为True
        )
        #调用支付接口
        # 调用支付接口
        # 电脑网站支付，需要跳转到沙箱环境https://openapi.alipaydev.com/gateway.do? + order_string
        # 电脑网站支付，需要跳转到正式环境https://openapi.alipay.com/gateway.do? + order_string

        total_pay = order.total_price + order.transit_price
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,  # 订单id
            # total_amount支持json，但是decimal数据不能直接序列化成json，所以转换成字符串即可
            total_amount=str(total_pay),  # 支付总金额
            subject="天天生鲜{}".format(order_id),  # 支付界面主题
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        #返回应答
        pay_url='https://openapi.alipaydev.com/gateway.do?' + order_string
        # pay_url = 'https://www.baidu.com'
        return JsonResponse({'res': 3, 'pay_url': pay_url})


#/order/check
def ordercheck(request):
    if request.method=='POST':
        #查询支付结果
        # 用户是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        order_id = request.POST.get('order_id')
        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效订单id'})
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, pay_method=3, order_status=1)
        except:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 业务处理 使用Python sdk调用支付接口
        #初始化
        alipay = AliPay(
            appid="2021000121645617",  # 订单id
            app_notify_url=None,  # 默认回调url
            app_private_key_string=open(os.path.join(settings.BASE_DIR, "apps/order/app_private_key.pem")).read(),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=open(os.path.join(settings.BASE_DIR, "apps/order/alipay_public_key.pem")).read(),
            sign_type="RSA2",  # RSA 或者 RSA2, 签名
            debug=True,  # 默认False, 沙箱模式需改为True
        )

        # response = {
        #     "alipay_trade_query_response": {
        #         "trade_no": "2017032121001004070200176844",
        #         "code": "10000",
        #         "invoice_amount": "20.00",
        #         "open_id": "20880072506750308812798160715407",
        #         "fund_bill_list": [
        #             {
        #                 "amount": "20.00",
        #                 "fund_channel": "ALIPAYACCOUNT"
        #             }
        #         ],
        #         "buyer_logon_id": "csq***@sandbox.com",
        #         "send_pay_date": "2017-03-21 13:29:17",
        #         "receipt_amount": "20.00",
        #         "out_trade_no": "out_trade_no15",
        #         "buyer_pay_amount": "20.00",
        #         "buyer_user_id": "2088102169481075",
        #         "msg": "Success",
        #         "point_amount": "0.00",
        #         "trade_status": "TRADE_SUCCESS",
        #         "total_amount": "20.00"
        #     }
        while True:
            response = alipay.api_alipay_trade_query(order_id)
            code=response.get('code')
            trade_status=response.get('trade_status')
            if code=='10000' and trade_status=='TRADE_SUCCESS':
                #支付成功
                #获取支付宝交易号
                trade_no=response.get('trade_no')
                #更新订单状态
                order.trade_no=trade_no
                order.order_status=4 #待评价
                order.save()
                pay_status = OrderInfo.PRDER_STATUS[str(order.order_status)]
                order.pay_status = pay_status

                #返回结果
                return JsonResponse({'res': 3, 'errmsg': '支付成功'})

            #等待买家付款或者业务处理失败（40004）一会就会成功
            elif code=='20000' or code=='40004' or (code=='10000' and trade_status=='WAIT_BUYER_PAY'):

                import time
                time.sleep(5)
                continue
            else:
                #支付出错
                print(code)
                return JsonResponse({'res': 4, 'errmsg': '支付出错'})

#/order/comment
def ordercomment(request,order_id):
    if request.method=='GET':
        user=request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        if not order_id:
            return HttpResponseRedirect(reverse('order',args=(1,)))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return HttpResponseRedirect(reverse("order",args=(1,)))

        # 根据订单的状态获取订单的状态标题
        order.status_name = OrderInfo.PRDER_STATUS[str(int(order.order_status))]

        # 获取订单商品信息
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            # 计算商品的小计
            amount = order_sku.count * order_sku.price
            # 动态给order_sku增加属性amount,保存商品小计
            order_sku.amount = amount
        # 动态给order增加属性order_skus, 保存订单商品信息
        order.order_skus = order_skus

        return render(request,'order/order_comment.html',{'order':order})

    elif request.method=='POST':
        user=request.user
        if not order_id:
            return HttpResponseRedirect(reverse('order', args=(1,)))
        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return HttpResponseRedirect(reverse("order", args=(1,)))

        #获取评论条数
        total_count=int(request.POST.get('total_count'))
        #循环获取商品评论内容
        for i in range(1,total_count+1):
            sku_id=request.POST.get(f"sku_{i}")
            coutent=request.POST.get(f"content_{i}")
            try:
                order_goods=OrderGoods.objects.get(sku_id=sku_id,order=order)
            except:
                continue

            order_goods.comment=coutent
            order_goods.save()

        order.order_status=5 #已完成
        order.save()

        return HttpResponseRedirect(reverse('order',args=[1]))


