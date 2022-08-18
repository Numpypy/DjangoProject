from django.contrib import admin
from .models import GoodsType,IndexPromotionBanner,IndexGoodsBanner,IndexTypeGoodsBanner,GoodsSKU,Goods
from django.core.cache import cache

# Register your models here.
class BaseModelAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        #重写save_model方法新增功能来更新静态页面的获取
        super().save_model(request,obj,form,change)#此行是让父类原本的功能不受影响

        #然后让celery重新生成静态页面
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        super().delete_model(request,obj) #此处同理上

        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()
        cache.delete('index_page_data')



class IndexPromotionBannerAdmin(BaseModelAdmin):
    pass
class IndexGoodsBannerAdmin(BaseModelAdmin):
    pass
class GoodsTypeAdmin(BaseModelAdmin):
    pass
class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
    pass
class GoodsSKUAdmin(BaseModelAdmin):
    pass
class GoodsAdmin(BaseModelAdmin):
    pass


admin.site.register(GoodsType,GoodsTypeAdmin)
admin.site.register(IndexPromotionBanner,IndexPromotionBannerAdmin)
admin.site.register(IndexTypeGoodsBanner,IndexTypeGoodsBannerAdmin)
admin.site.register(IndexGoodsBanner,IndexGoodsBannerAdmin)
admin.site.register(GoodsSKU,GoodsSKUAdmin)
admin.site.register(Goods,GoodsAdmin)