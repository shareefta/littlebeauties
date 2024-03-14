import secrets

from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.crypto import get_random_string
from django.urls import reverse

from .forms import *
from .models import *
from category.models import Category
from category.forms import CategoryForm
from store.models import Product, Variant
from store.forms import ProductForm, VariantForm, ProductOfferForm
from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.cache import cache_control, never_cache
from .helper import MessageHandler
import random
from django.contrib.auth import login, logout
from carts.views import _cart_id
from carts.models import Cart, CartItem, Coupons, UserCoupons
from orders.models import Order, OrderProduct, ShippingAddress
from orders.forms import ChangeStatusForm
import requests

from carts.forms import CouponForm
import datetime


# Create your views here.
def is_admin(user):
    return user.is_authenticated and user.is_staff


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            phone_number = form.cleaned_data["phone_number"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            # Create an Account instance
            user = Account.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                email=email,
                password=password,
            )
            user.save()

            # Create a Profile instance
            profile = Profile.objects.create(user=user)
            profile.save()

            # # user activation
            # otp = ''.join(secrets.choice('0123456789') for _ in range(4))
            # profile = Profile.objects.create(user=user, otp=f'{otp}')
            # profile.save()
            # user_details = {
            #     'uid': profile.uid,
            #     'phone_number': profile.user.phone_number,
            #
            # }
            # request.session['user_details'] = user_details
            # messagehandler = MessageHandler(request.POST['phone_number'],otp).send_otp_via_message()
            # red = redirect(reverse('otp_verify', args=[str(profile.uid)]))
            # # red = redirect(f'otp/{profile.uid}/')
            # red.set_cookie("can_otp_enter", True, max_age=60)
            # return red
            messages.success(request, "Registration Successful.")
            return redirect("login_user")
    else:
        form = RegistrationForm()
    context = {"form": form}
    return render(request, "accounts/register.html", context)


# user registration_otp_verify
# @cache_control(no_cache=True, must_revalidate=True, no_store=True)
# @never_cache
# def otp_verify(request, uid):
#     if request.method == "POST":
#         otp = request.POST.get('otp')
#         try:
#             profile = Profile.objects.filter(uid=uid).first()
#         except Profile.DoesNotExist:
#             return HttpResponse("Profile not found", status=404)
#         if request.COOKIES.get('can_otp_enter') != None:
#             if otp == profile.otp:
#                 if profile.user is not None:
#                     profile.user.session = {'profile.user.id': profile.user.id}
#                     profile.user.is_active = True
#                     profile.user.save()
#                     request.session['key3'] = 3
#                     messages.success(request, 'Your Account has been activated.You can log in now')
#                     return redirect("login")
#                 return redirect('register')
#             messages.error(request, 'You have entered wrong OTP.Try again')
#             return redirect(request.path)
#         messages.error(request, '60 seconds over.Try again')
#         return redirect(request.path)
#     return render(request, "accounts/otp-verify-login.html", {'uid': uid})


# user login
@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@never_cache
def login_user(request):
    if request.method == "POST":
        email = request.POST.get("email")
        phone_number = request.POST.get("phone_number")
        # Check if a profile with the given phone number exists
        user = Account.objects.filter(email=email).first()
        if not user:
            messages.error(request, "User does not exist.")
            return redirect("login_user")
        if not user.is_active:
            messages.error(
                request,
                "Your account has been temporarily blocked. Please contact support for further assistance.",
            )
            return redirect("login_user")
        profile = Profile.objects.get(user=user)
        auth.login(request, profile.user)
        profile.user.session = {"profile.user.id": profile.user.id}
        profile.user.save()
        profile = {"id": profile.id, "first_name": profile.user.first_name}
        context = {"profile": profile}
        request.session["profile"] = profile
        return render(request, "home.html", context)
        # otp = ''.join(secrets.choice('0123456789') for _ in range(4))
        # profile.otp = otp
        # profile.save()
        # user_details = {
        #     'profile_email': profile.user.email,
        #     'phone_number': profile.user.phone_number,
        # }
        # request.session['user_details'] = user_details
        # messagehandler = MessageHandler(profile.user.phone_number, otp).send_otp_via_message()
        # uid = str(uuid.uuid4())
        # red = redirect('otp_verify_login', uid=uid)
        # red.set_cookie("can_otp_enter", True, max_age=60)
        # return red
    return render(request, "accounts/login_user.html")


def otp_verify_login(request, uid):
    uid = str(uid)
    if request.method == "POST":
        try:
            profile = Profile.objects.get(otp=request.POST["otp"])
            if request.COOKIES.get("can_otp_enter") != None:
                if profile.user is not None:
                    try:
                        cart = Cart.objects.get(cart_id=_cart_id(request))
                        is_cart_item_exists = CartItem.objects.filter(
                            cart=cart
                        ).exists()
                        if is_cart_item_exists:
                            cart_items = CartItem.objects.filter(cart=cart)
                            # Getting the product variants by cart id
                            product_variant = []
                            for cart_item in cart_items:
                                variant = cart_item.variant.all()
                                product_variant.append(list(variant))

                            # Get the cart items from the user to access his product variants
                            cart_items = CartItem.objects.filter(user=profile.user)
                            ex_variant_list = []
                            id = []
                            for cart_item in cart_items:
                                existing_variant = cart_item.variant.all()
                                ex_variant_list.append(list(existing_variant))
                                id.append(cart_item.id)

                            for p_variant in product_variant:
                                if p_variant in ex_variant_list:
                                    index = ex_variant_list.index(p_variant)
                                    item_id = id[index]
                                    item = CartItem.objects.get(id=item_id)
                                    item.quantity += 1
                                    item.user = profile.user
                                    item.save()
                                else:
                                    cart_items = CartItem.objects.filter(cart=cart)
                                    for cart_item in cart_items:
                                        cart_item.user = profile.user
                                        cart_item.save()
                    except:
                        pass
                    auth.login(request, profile.user)
                    profile.user.session = {"profile.user.id": profile.user.id}
                    profile.user.save()
                    profile = {"id": profile.id, "first_name": profile.user.first_name}
                    context = {"profile": profile}
                    request.session["profile"] = profile
                    return render(request, "home.html", {"profile": profile})
                return redirect("login_user")
            messages.error(request, "60 seconds over.Try again")
            return redirect("login_user")
        except:
            messages.error(request, "You have entered wrong OTP.Try again")
    return render(request, "accounts/otp-verify-login.html", {"uid": uid})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_user")
def logout_user(request):
    auth.logout(request)
    messages.success(request, "Lougout Successful")
    return redirect("login_user")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def login_admin(request):
    if request.method == "POST":
        email = request.POST["email"]
        password = request.POST["password"]

        user = auth.authenticate(email=email, password=password)

        if user is not None:
            auth.login(request, user)
            return redirect("dashboard_admin")
        else:
            messages.error(request, "Invalid Credentials")
            return redirect("login_admin")
    return render(request, "accounts/login.html")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def logout_admin(request):
    auth.logout(request)
    messages.success(request, "Lougout Successful")
    return redirect("login_admin")
    pass


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_user")
def dashboard(request):
    orders = Order.objects.order_by("-created_at").filter(
        user_id=request.user.id, is_ordered=True
    )
    orders_count = orders.count()
    context = {
        "orders_count": orders_count,
    }
    return render(request, "accounts/dashboard.html", context)


from datetime import date
from django.utils import timezone
from datetime import datetime, timedelta


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def dashboard_admin(request):
    # Calculate the start and end of the current year
    current_date = datetime.now()
    start_of_year = current_date.replace(month=1, day=1)
    end_of_year = start_of_year.replace(year=start_of_year.year + 1) - timedelta(days=1)

    # Filter OrderProduct objects for the current year
    orders = Order.objects.filter(
        created_at__range=[start_of_year, end_of_year]
    ).order_by("-created_at")
    # Finding Total Order Count:
    orders_count = orders.count()

    # Calculate the sum of order amount for the current year
    total_order_amount = (
        orders.aggregate(total_order_amount=Sum("order_total"))["total_order_amount"]
        or 0
    )

    # Fetching number of Active Users:
    users = Profile.objects.filter(user__is_active=True)
    users_count = users.count()

    # Fetching number of Categories:
    categories = Category.objects.all()
    categories_count = categories.count()

    # Fetching number of Products:
    products = Product.objects.all()
    products_count = products.count()

    # Fetching number of Coupons:
    coupons = Coupons.objects.all()
    coupons_count = coupons.count()

    context = {
        "start_of_year": start_of_year,
        "end_of_year": end_of_year,
        "orders": orders,
        "total_order_amount": total_order_amount,
        "orders_count": orders_count,
        "users_count": users_count,
        "categories_count": categories_count,
        "products_count": products_count,
        "coupons_count": coupons_count,
    }
    return render(request, "admin/dashboard_admin.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def category_list(request):
    category_list = Category.objects.all()
    return render(request, "admin/category_list.html", {"category_list": category_list})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def category_add(request):
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category_name = form.cleaned_data["category_name"]
            slug = form.cleaned_data["slug"]
            description = form.cleaned_data["description"]
            category_image = form.cleaned_data["category_image"]

            category = Category.objects.create(
                category_name=category_name,
                slug=slug,
                description=description,
                category_image=category_image,
            )
            category.save()
            messages.success(request, "Category Added Successfully.")
            return redirect("category_list")
    else:
        form = CategoryForm()
    context = {"form": form}
    return render(request, "admin/category_create.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def category_update(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            form.save()
            return redirect("category_list")
    else:
        form = CategoryForm(instance=category)
    context = {"form": form, "category_id": category_id, "category": category}

    return render(request, "admin/category_update.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def category_toggle_status(request, id):
    category = get_object_or_404(Category, id=id)

    # Toggle the status (listed/unlisted)
    category.is_listed = not category.is_listed
    category.save()

    return redirect("category_list")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def product_list(request):
    product_list = Product.objects.all()
    return render(request, "admin/product_list.html", {"product_list": product_list})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def product_add(request):
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product_name = form.cleaned_data["product_name"]
            slug = form.cleaned_data["slug"]
            description = form.cleaned_data["description"]
            price = form.cleaned_data["price"]
            stock = form.cleaned_data["stock"]
            category = form.cleaned_data["category"]
            product_image = form.cleaned_data["product_image"]

            product = Product.objects.create(
                product_name=product_name,
                slug=slug,
                description=description,
                price=price,
                stock=stock,
                category=category,
                product_image=product_image,
            )
            product.save()
            messages.success(request, "Product Added Successfully.")
            return redirect("product_list")
    else:
        form = ProductForm()
    context = {"form": form}
    return render(request, "admin/product_create.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def product_update(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            return redirect("product_list")
    else:
        form = ProductForm(instance=product)
    context = {"form": form, "product_id": product_id, "product": product}

    return render(request, "admin/product_update.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def product_toggle_status(request, id):
    product = get_object_or_404(Product, id=id)

    # Toggle the status (listed/unlisted)
    product.is_available = not product.is_available
    product.save()
    return redirect("product_list")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def variant_list(request):
    variant_list = Variant.objects.all()
    return render(request, "admin/variant_list.html", {"variant_list": variant_list})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def variant_add(request):
    if request.method == "POST":
        form = VariantForm(request.POST)
        if form.is_valid():
            product = form.cleaned_data["product"]
            variant_category = form.cleaned_data["variant_category"]
            variant_value = form.cleaned_data["variant_value"]

            variant = Variant.objects.create(
                product=product,
                variant_category=variant_category,
                variant_value=variant_value,
            )
            variant.save()
            messages.success(request, "Variant Added Successfully.")
            return redirect("variant_list")
    else:
        form = VariantForm()
    context = {"form": form}
    return render(request, "admin/variant_create.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def variant_update(request, variant_id):
    variant = get_object_or_404(Variant, pk=variant_id)

    if request.method == "POST":
        form = VariantForm(request.POST, instance=variant)
        if form.is_valid():
            form.save()
            return redirect("variant_list")
    else:
        form = VariantForm(instance=variant)
    return render(
        request, "admin/variant_update.html", {"form": form, "variant_id": variant_id}
    )


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def variant_delete(request, variant_id):
    variant_to_delete = Variant.objects.filter(id=variant_id)
    variant_to_delete.delete()

    return redirect("variant_list")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def users_list(request):
    profiles = Profile.objects.all()
    return render(request, "admin/users_list.html", {"profiles": profiles})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(is_admin, login_url="login_admin")
@login_required(login_url="login_admin")
def toggle_user_status(request, user_id):
    user = get_object_or_404(Account, id=user_id)
    user.is_active = not user.is_active
    user.save()
    return redirect("users_list")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def order_list(request):
    orders = Order.objects.all().order_by("-created_at")
    return render(request, "admin/order-list.html", {"orders": orders})


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def cancel_order(request, order_id):
    order_to_cancel = Order.objects.get(id=order_id)
    order_to_cancel.status = "Cancelled"
    order_to_cancel.is_cancelled = True
    order_to_cancel.save()

    # Add the amount of order total to user's wallet
    order = get_object_or_404(Order, id=order_id)
    user = order.user
    user.wallet += order.order_total
    user.save()

    # Increase product stock for each item in the canceled order
    for order_product in order_to_cancel.products.all():
        product = order_product.product
        product.stock += order_product.quantity
        product.save()

    return redirect("order_list")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(is_admin, login_url="login_admin")
@login_required(login_url="login_admin")
def change_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    old_status = order.status
    if request.method == "POST":
        form = ChangeStatusForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            new_status = form.cleaned_data["status"]
            if new_status == "Cancelled" or old_status == "Order Confirmed":
                user = order.user
                user.wallet += order.order_total
                user.save()
            elif new_status == "Return Received" or old_status == "Cancelled":
                user = order.user
                user.wallet += order.order_total
                user.save()

            # Update product stock based on the new status
            update_product_stock(order, old_status, new_status)
            return redirect("order_list")
    else:
        form = ChangeStatusForm(instance=order)
    return render(
        request, "admin/change-order-status.html", {"form": form, "order_id": order_id}
    )


def update_product_stock(order, old_status, new_status):
    # Function to update product stock based on order status change
    if old_status == "Order Confirmed" and new_status == "Cancelled":
        # Order status changed from New to Cancelled, increase product stock
        for order_product in order.products.all():
            increase_stock(order_product.product, order_product.quantity)

    elif old_status == "Cancelled" and new_status == "Order Confirmed":
        # Order status changed from Cancelled to Accepted, decrease product stock
        for order_product in order.products.all():
            decrease_stock(order_product.product, order_product.quantity)

    elif new_status == "Return Received":
        # Order status changed from New to Cancelled, increase product stock
        for order_product in order.products.all():
            increase_stock(order_product.product, order_product.quantity)


def increase_stock(product, quantity):
    # Function to increase product stock
    product.stock += quantity
    product.save()


def decrease_stock(product, quantity):
    # Function to decrease product stock
    if product.stock >= quantity:
        product.stock -= quantity
        product.save()


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def coupon_list(request):
    coupons = Coupons.objects.all()

    context = {"coupons": coupons}
    return render(request, "admin/coupon-list.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def add_coupon_offer(request):
    if request.method == "POST":
        form = CouponForm(request.POST)
        if form.is_valid():
            coupon_code = form.cleaned_data["coupon_code"]
            description = form.cleaned_data["description"]
            minimum_amount = form.cleaned_data["minimum_amount"]
            discount = form.cleaned_data["discount"]
            valid_from = form.cleaned_data["valid_from"]
            valid_to = form.cleaned_data["valid_to"]
            coupon = Coupons.objects.create(
                coupon_code=coupon_code,
                description=description,
                minimum_amount=minimum_amount,
                discount=discount,
                valid_from=valid_from,
                valid_to=valid_to,
            )
            coupon.save()
            messages.success(request, "Coupon Added Successfully.")
            return redirect("coupon_list")
    else:
        form = CouponForm()
    context = {"form": form}
    return render(request, "admin/add-coupon-offer.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def edit_coupon_offer(request, coupon_id):
    coupon = get_object_or_404(Coupons, pk=coupon_id)
    if request.method == "POST":
        form = CouponForm(request.POST, instance=coupon)
        if form.is_valid():
            form.save()
            messages.success(request, "Coupon updated Successfully.")
            return redirect("coupon_list")
    else:
        form = CouponForm(instance=coupon)
    return render(
        request,
        "admin/coupon-offer-update.html",
        {"form": form, "coupon_id": coupon_id},
    )


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def coupon_toggle_status(request, coupon_id):
    coupon = get_object_or_404(Coupons, pk=coupon_id)
    coupon.is_listed = not coupon.is_listed
    coupon.save()
    return redirect("coupon_list")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def product_offer_list(request):
    products = Product.objects.filter(is_available=True)

    offer_produtcts = []
    for product in products:
        if product.offer_percentage > 0:
            offer_product = product
            offer_produtcts.append(offer_product)

    context = {"offer_products": offer_produtcts}

    return render(request, "admin/product-offer-list.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def add_product_offer(request):
    products = Product.objects.filter(offer_percentage=0)
    context = {"products": products}
    return render(request, "admin/list-products-add-offer.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def add_offer_percentage(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.method == "POST":
        form = ProductOfferForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product offer added Successfully.")
            return redirect("product_offer_list")
    else:
        form = ProductOfferForm(instance=product)
    return render(
        request,
        "admin/add-product-offer.html",
        {"form": form, "product_id": product_id},
    )


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def edit_product_offer(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.method == "POST":
        form = ProductOfferForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "offer updated Successfully.")
            return redirect("product_offer_list")
    else:
        form = ProductOfferForm(instance=product)
    return render(
        request,
        "admin/add-product-offer.html",
        {"form": form, "product_id": product_id},
    )


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def delete_product_offer(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    product.offer_percentage = 0
    product.save()
    return redirect("product_offer_list")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_admin")
@user_passes_test(is_admin, login_url="login_admin")
def offer_toggle_status(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    product.is_listed_offer = not product.is_listed_offer
    product.save()
    return redirect("product_offer_list")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_user")
def user_cancel_order(request, order_id):
    order_to_cancel = Order.objects.get(id=order_id)
    order_to_cancel.status = "Cancelled"
    order_to_cancel.is_cancelled = True
    order_to_cancel.save()

    # Add the amount of order total to user's wallet
    order = get_object_or_404(Order, id=order_id)
    user = order.user
    user.wallet += order.order_total
    user.save()

    # Increase product stock for each item in the canceled order
    for order_product in order_to_cancel.products.all():
        product = order_product.product
        product.stock += order_product.quantity
        product.save()

    return redirect("my_orders")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_user")
def my_orders(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by(
        "-created_at"
    )
    context = {"orders": orders}
    return render(request, "accounts/my-orders.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_user")
def my_profile(request):
    user = request.user
    userprofile = UserProfile.objects.filter(user=request.user).first()
    if userprofile:
        user_data = get_object_or_404(Account, id=user.id)
        profile_data = get_object_or_404(UserProfile, user=user)

        context = {
            "user_data": user_data,
            "profile_data": profile_data,
            "userprofile": userprofile,
        }
        return render(request, "accounts/my-profile.html", context)
    else:
        user_data = get_object_or_404(Account, id=user.id)

        context = {"user_data": user_data, "userprofile": userprofile}
        return render(request, "accounts/my-profile.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_user")
def add_profile(request):
    userprofile = UserProfile()
    if request.method == "POST":
        profile_form = UserProfileForm(
            request.POST, request.FILES, instance=userprofile
        )
        if profile_form.is_valid():
            profile = profile_form.save(commit=False)
            profile.user = request.user
            profile.save()
            messages.success(request, "Your Profile Added Successfully")
            return redirect("my_profile")
    else:
        profile_form = UserProfileForm(instance=userprofile)
    context = {
        "profile_form": profile_form,
        "userprofile": userprofile,
    }
    return render(request, "accounts/add-profile.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_user")
def edit_profile(request):
    userprofile = UserProfile.objects.filter(user=request.user).first()
    if userprofile:
        if request.method == "POST":
            user_form = UserForm(request.POST, instance=request.user)
            profile_form = UserProfileForm(
                request.POST, request.FILES, instance=userprofile
            )
            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                messages.success(request, "Your Profile Updated Successfully")
                return redirect("my_profile")
        else:
            user_form = UserForm(instance=request.user)
            profile_form = UserProfileForm(instance=userprofile)
        context = {
            "user_form": user_form,
            "profile_form": profile_form,
            "userprofile": userprofile,
        }
        return render(request, "accounts/edit-profile.html", context)
    else:
        context = {
            "user_form": UserForm,
            "profile_form": UserProfileForm,
            "userprofile": userprofile,
        }
        return render(request, "accounts/add-profile.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_user")
def change_password(request):
    if request.method == "POST":
        current_password = request.POST["current_password"]
        new_password = request.POST["new_password"]
        confirm_password = request.POST["confirm_password"]
        user = Account.objects.get(email__exact=request.user.email)

        if new_password == confirm_password:
            success = user.check_password(current_password)
            if success:
                user.set_password(new_password)
                messages.success(request, "Password Updated Successfully")
                auth.logout(request)
                # messages.success(request, 'Lougout Successful')
                return redirect("login_user")
            else:
                messages.error(request, "Enter Valid Current Password")
                return redirect("change_password")
        else:
            messages.error(request, "Password Does Not Match")
            return redirect("change_password")
    return render(request, "accounts/change-password.html")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_user")
def order_detail(request, order_id):
    order_detail = OrderProduct.objects.filter(order__order_number=order_id)
    order = Order.objects.get(order_number=order_id)
    shipping_address = ShippingAddress.objects.get(order__order_number=order_id)

    total_product = []
    subtotal = 0
    total_product_discount = 0

    for item in order_detail:
        product_total = item.product_price * item.quantity
        subtotal += product_total
        total_product.append({"item": item, "total": product_total})
        total_product_discount += item.product_discount

    context = {
        "order_detail": total_product,
        "order": order,
        "subtotal": subtotal,
        "total": subtotal + order.tax,
        "total_product_discount": total_product_discount,
        "total_discount": order.coupon_discount + total_product_discount,
        "shipping_address": shipping_address,
    }
    return render(request, "accounts/order-detail.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_user")
def my_coupons(request):
    if request.user.is_authenticated:
        coupons = Coupons.objects.all()
        user = request.user
        current_time = timezone.localtime(timezone.now())

        coupon_statuses = []

        for coupon in coupons:
            if coupon.valid_from <= current_time <= coupon.valid_to:
                is_used = UserCoupons.objects.filter(
                    coupon=coupon, user=user, is_used=True
                ).exists()
                coupon_statuses.append("Used" if is_used else "Active")
            else:
                coupon.is_expired = True
                coupon.save()
                coupon_statuses.append("Expired")

        coupon_data = zip(coupons, coupon_statuses)

        context = {"coupon_data": coupon_data}
        return render(request, "accounts/my-coupons.html", context)
    else:
        return redirect("login_user")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_user")
def address_list(request):
    address = Address.objects.filter(user=request.user)
    context = {
        "address": address,
    }
    return render(request, "accounts/address-list.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_user")
def add_address(request):
    if request.method == "POST":
        form = AddressForm(request.POST)
        if form.is_valid():
            # Get the current user
            current_user = request.user

            # Extract data from the form
            full_name = form.cleaned_data["full_name"]
            phone_number = form.cleaned_data["phone_number"]
            address_line_1 = form.cleaned_data["address_line_1"]
            address_line_2 = form.cleaned_data["address_line_2"]
            city = form.cleaned_data["city"]
            state = form.cleaned_data["state"]
            country = form.cleaned_data["country"]
            zipcode = form.cleaned_data["zipcode"]

            # Create and save the address with the current user
            address = Address.objects.create(
                user=current_user,
                full_name=full_name,
                phone_number=phone_number,
                address_line_1=address_line_1,
                address_line_2=address_line_2,
                city=city,
                state=state,
                country=country,
                zipcode=zipcode,
            )
            messages.success(request, "Address Added Successfully.")
            return redirect("address_list")
    else:
        form = AddressForm()

    context = {"form": form}
    return render(request, "accounts/add-address.html", context)


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_user")
def edit_address(request, address_id):
    address = get_object_or_404(Address, id=address_id)

    if request.method == "POST":
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            return redirect("address_list")
    else:
        form = AddressForm(instance=address)
    return render(
        request, "accounts/edit-address.html", {"form": form, "address_id": address_id}
    )


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_user")
def delete_address(request, address_id):
    address_to_delete = get_object_or_404(Address, id=address_id)
    address_to_delete.delete()
    return redirect("address_list")


def forgot_password(request):
    if request.method == "POST":
        first_name = request.POST["first_name"]
        email = request.POST["email"]
        phone_number = request.POST["phone_number"]
        try:
            user = Account.objects.get(email=email)
            # phone_number = Profile.objects.get(phone_number=phone_number)
        except:
            return HttpResponse("User doesnt exist")

        otp = get_random_string(8, "0123456789")
        messagehandler = MessageHandler(user.phone_number, otp).send_otp_via_message()
        user.set_password(otp)
        user.save()
        logout(request)
        messages.success(
            request, "The new password has been sent to your mobile number."
        )
        return redirect("login_user")

    return render(request, "accounts/forgot-password-user.html")


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url="login_user")
def add_money_wallet(request):
    if request.method == "POST":
        amount = float(request.POST.get("amount", 0))
        user = request.user
        user.wallet += amount
        user.save()
        messages.success(request, "Money added Successfully")
        return redirect(request.path)
    return render(request, "accounts/my-wallet.html")
