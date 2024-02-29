from django.contrib import admin
from .models import Payment, Order, OrderProduct, ShippingAddress
from django.db.models import Sum
from django.utils import timezone
# Register your models here.

class SalesReportMixin:
    def get_weekly_sales(self, queryset):
        today = timezone.now()
        week_start = today - timezone.timedelta(days=today.weekday())
        week_end = week_start + timezone.timedelta(days=6)

        return queryset.filter(created_at__range=[week_start, week_end]).aggregate(total=Sum('order_total'))['total'] or 0

    def get_monthly_sales(self, queryset):
        today = timezone.now()
        month_start = today.replace(day=1)
        month_end = month_start + timezone.timedelta(days=32)
        month_end = month_end.replace(day=1)

        return queryset.filter(created_at__range=[month_start, month_end]).aggregate(total=Sum('order_total'))['total'] or 0

    def get_yearly_sales(self, queryset):
        today = timezone.now()
        year_start = today.replace(month=1, day=1)
        year_end = year_start.replace(year=year_start.year + 1)

        return queryset.filter(created_at__range=[year_start, year_end]).aggregate(total=Sum('order_total'))['total'] or 0


class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    readonly_fields = ('payment', 'user', 'product', 'quantity', 'product_price', 'ordered')
    extra = 0

class OrderAdmin(admin.ModelAdmin, SalesReportMixin):
    list_display = ['order_number', 'order_total', 'tax', 'status', 'is_ordered', 'created_at']
    list_filter = ['status', 'is_ordered']
    # search_fields = ['order_number', 'first_name', 'last_name', 'phone', 'email']
    list_per_page = 20
    inlines = [OrderProductInline]
    search_fields = ['user__username', 'id']

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['weekly_sales'] = self.get_weekly_sales(Order.objects.filter(status='Accepted'))
        extra_context['monthly_sales'] = self.get_monthly_sales(Order.objects.filter(status='Accepted'))
        extra_context['yearly_sales'] = self.get_yearly_sales(Order.objects.filter(status='Accepted'))
        return super().changelist_view(request, extra_context=extra_context)



class PaymentAdmin(admin.ModelAdmin, SalesReportMixin):

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['weekly_sales'] = self.get_weekly_sales(Payment.objects.all())
        extra_context['monthly_sales'] = self.get_monthly_sales(Payment.objects.all())
        extra_context['yearly_sales'] = self.get_yearly_sales(Payment.objects.all())
        return super().changelist_view(request, extra_context=extra_context)

class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'phone_number', 'address_line_1', 'address_line_2', 'city', 'state', 'country', 'zipcode']

admin.site.register(Order, OrderAdmin)
admin.site.register(OrderProduct)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(ShippingAddress, ShippingAddressAdmin)
