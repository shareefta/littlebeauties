from django.urls import path, re_path
from . import views
import uuid

urlpatterns = [

    #REGISTRATION
    path('register/', views.register, name="register"),
    # path('otp_verify/<str:uid>/', views.otp_verify, name='otp_verify'),

    #ADMIN
    path('login_admin/', views.login_admin, name="login_admin"),
    path('dashboard_admin', views.dashboard_admin, name='dashboard_admin'),
    path('logout_admin/', views.logout_admin, name="logout_admin"),

    #USER MANAGEMENT
    path('users_list', views.users_list, name="users_list"),
    path('toggle_user_status/<int:user_id>/', views.toggle_user_status, name='toggle_user_status'),


    # CATEGORY MANAGEMENT
    path('category_list', views.category_list, name="category_list"),
    path('category_add', views.category_add, name="category_add"),
    path('category_update/<int:category_id>', views.category_update, name="category_update"),
    path('category_toggle_status/<slug:id>', views.category_toggle_status, name="category_toggle_status"),

    # PRODUCT MANAGEMENT
    path('product_list', views.product_list, name="product_list"),
    path('product_add', views.product_add, name="product_add"),
    path('product_update/<int:product_id>', views.product_update, name="product_update"),
    path('product_toggle_status/<slug:id>', views.product_toggle_status, name="product_toggle_status"),

    # VARIANT MANAGEMENT
    path('variant_list', views.variant_list, name="variant_list"),
    path('variant_add', views.variant_add, name='variant_add'),
    path('variant_update/<int:variant_id>', views.variant_update, name="variant_update"),
    path('variant_delete/<int:variant_id>', views.variant_delete, name="variant_delete"),

    # ORDER MANAGEMENT
    path('order_list', views.order_list, name="order_list"),
    path('change_order_status/<int:order_id>/', views.change_order_status, name='change_order_status'),
    path('cancel_order/<int:order_id>/', views.cancel_order, name='cancel_order'),

    #COUPON MANAGEMENT
    path('coupon_list/', views.coupon_list, name='coupon_list'),
    path('add_coupon_offer/', views.add_coupon_offer, name='add_coupon_offer'),
    path('edit_coupon_offer/<int:coupon_id>/', views.edit_coupon_offer, name='edit_coupon_offer'),
    path('coupon_toggle_status/<int:coupon_id>/', views.coupon_toggle_status, name='coupon_toggle_status'),

    #PRODUCT OFFER MANAGEMENT
    path('product_offer_list', views.product_offer_list, name='product_offer_list'),
    path('add_product_offer', views.add_product_offer, name='add_product_offer'),
    path('add_offer_percentage/<int:product_id>/', views.add_offer_percentage, name='add_offer_percentage'),
    path('edit_product_offer/<int:product_id>/', views.edit_product_offer, name='edit_product_offer'),
    path('delete_product_offer/<int:product_id>/', views.delete_product_offer, name='delete_product_offer'),
    path('offer_toggle_status/<int:product_id>/', views.offer_toggle_status, name='offer_toggle_status'),

    #USER DASHBOARD
    path('login_user',views.login_user, name='login_user'),
    re_path(r'^otp_verify_login/(?P<uid>[0-9a-f-]+)/$', views.otp_verify_login, name='otp_verify_login'),
    # path('otp_verify_login/<uuid:uid>/', views.otp_verify_login, name='otp_verify_login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout_user/', views.logout_user, name="logout_user"),
    path('my_orders/', views.my_orders, name='my_orders'),
    path('my_coupons/', views.my_coupons, name='my_coupons'),
    path('my_profile/', views.my_profile, name='my_profile'),
    path('add_profile/', views.add_profile, name='add_profile'),
    path('edit_profile/', views.edit_profile, name='edit_profile'),
    path('change_password', views.change_password, name='change_password'),
    path('order_detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('user_cancel_order/<int:order_id>/', views.user_cancel_order, name='user_cancel_order'),
    path('address_list/', views.address_list, name='address_list'),
    path('add_address/', views.add_address, name='add_address'),
    path('edit_address/<int:address_id>/', views.edit_address, name='edit_address'),
    path('delete_address/<int:address_id>/', views.delete_address, name='delete_address'),
    path('forgot_password/',views.forgot_password,name="forgot_password"),
    path('add_money_wallet', views.add_money_wallet, name='add_money_wallet'),
]
