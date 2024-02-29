from django.urls import path
from . import views


app_name = 'orders'

urlpatterns = [
    path('add_address_checkout', views.add_address_checkout, name='add_address_checkout'),

    path('apply_coupon/<int:order_id>/<int:coupon_id>/', views.apply_coupon, name='apply_coupon'),

    path('place_order/', views.place_order, name='place_order'),
    path('make_payments/<int:order_id>/', views.make_payments, name='make_payments'),
    path('order_confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),

    path('paypal_payment_success/<int:order_id>/', views.paypal_payment_success, name='paypal_payment_success'),
    path('paypal_payment_failed/<int:order_id>/', views.paypal_payment_failed, name='paypal_payment_failed'),

    path('order_detail_admin/<int:order_id>/', views.order_detail_admin, name='order_detail_admin'),

    path('sales_report/', views.sales_report, name='sales_report'),
    path('weekly_sales_report/', views.weekly_sales_report, name='weekly_sales_report'),
    path('monthly_sales_report/', views.monthly_sales_report, name='monthly_sales_report'),
    path('yearly_sales_report/', views.yearly_sales_report, name='yearly_sales_report'),
    path('custom_sales_report/', views.custom_sales_report, name='custom_sales_report'),

    path('sales_report_pdf/', views.sales_report_pdf, name='sales_report_pdf'),
    path('weekly_report_pdf/', views.weekly_report_pdf, name='weekly_report_pdf'),
    path('monthly_report_pdf/', views.monthly_report_pdf, name='monthly_report_pdf'),
    path('yearly_report_pdf/', views.yearly_report_pdf, name='yearly_report_pdf'),
    path('custom_report_pdf/<str:starting_date>/<str:ending_date>/', views.custom_report_pdf, name='custom_report_pdf'),

]