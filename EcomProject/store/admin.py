from django.contrib import admin
from . models import Product, Variant, WishList

# Register your models here.

class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price', 'stock', 'category', 'offer_percentage', 'offer_price', 'modified_date', 'is_available')
    prepopulated_fields = {'slug' : ('product_name',)}

admin.site.register(Product, ProductAdmin)

class VariantAdmin(admin.ModelAdmin):
    list_display = ('product', 'variant_category', 'variant_value', 'is_active')
    list_editable = ('is_active',)
    list_filter = ('product', 'variant_category', 'variant_value')

admin.site.register(Variant, VariantAdmin)
admin.site.register(WishList)