from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from store.models import Product, Variant
from .models import Cart, CartItem, UserCoupons, Coupons
from accounts.models import Address
from accounts.forms import AddressForm
from orders.models import Order
from django.contrib.auth.decorators import login_required

from django.http import HttpResponse

# Create your views here.

def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart

def cart(request, total=0, quantity=0, cart_items=None):
    try:
        tax = 0
        grand_total = 0
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        total_discount = 0

        for cart_item in cart_items:
            if cart_item.product.offer_percentage > 0:
                discount_price = (cart_item.product.offer_percentage * cart_item.product.price) / 100
                total_discount += discount_price * cart_item.quantity
                cart_item.product.offer_price = cart_item.product.price - discount_price
                total += (cart_item.product.offer_price * cart_item.quantity)
                quantity += cart_item.quantity
            else:
                total += (cart_item.product.price * cart_item.quantity)
                quantity += cart_item.quantity
        #Total amount befor discount
        net_total = total + total_discount
        tax = (2 * total)/100
        #Total amount after discount
        grand_total = total + tax

    except ObjectDoesNotExist:
        pass

    context = {
        'net_total' : net_total,
        'total_discount' : total_discount,
        'total' : total,
        'quantity' : quantity,
        'cart_items' : cart_items,
        'tax' : tax,
        'grand_total' : grand_total,
    }
    return render(request, 'store/cart.html', context)

def add_cart(request, product_id):
    current_user = request.user
    product = Product.objects.get(id=product_id)
    # If the user is authenticated:
    if current_user.is_authenticated:
        product_variant = []
        if request.method == 'POST':
            for item in request.POST:
                key = item
                value = request.POST[key]
                try:
                    variant = Variant.objects.get(product=product, variant_category__iexact=key,
                                                  variant_value__iexact=value)
                    product_variant.append(variant)
                except:
                    pass
        is_cart_item_exists = CartItem.objects.filter(product=product, user=current_user).exists()
        if is_cart_item_exists:
            cart_item = CartItem.objects.filter(product=product, user=current_user)
            ex_variant_list = []
            id = []
            for item in cart_item:
                existing_variant = item.variant.all()
                ex_variant_list.append(list(existing_variant))
                id.append(item.id)

            if product_variant in ex_variant_list:
                index = ex_variant_list.index(product_variant)
                item_id = id[index]
                item = CartItem.objects.get(product=product, id=item_id)
                item.quantity += 1
                item.save()
            else:
                item = CartItem.objects.create(product=product, quantity=1, user=current_user)
                if len(product_variant) > 0:
                    item.variant.clear()
                    item.variant.add(*product_variant)
                item.save()
        else:
            cart_item = CartItem.objects.create(
                product = product,
                quantity = 1,
                user = current_user,
            )
            if len(product_variant) > 0:
                cart_item.variant.clear()
                for item in product_variant:
                    cart_item.variant.add(item)
            cart_item.save()
        return redirect('cart')
    # If the user is not authenticated:
    else:
        product_variant = []
        if request.method == 'POST':
            for item in request.POST:
                key = item
                value = request.POST[key]
                try:
                    variant = Variant.objects.get(product = product, variant_category__iexact = key, variant_value__iexact = value)
                    product_variant.append(variant)
                except:
                    pass
        try:
            cart = Cart.objects.get(cart_id=_cart_id(request))
        except Cart.DoesNotExist:
            cart = Cart.objects.create(cart_id = _cart_id(request))

        is_cart_item_exists = CartItem.objects.filter(product=product, cart=cart).exists()
        if is_cart_item_exists:
            cart_item = CartItem.objects.filter(product=product, cart=cart)
            ex_variant_list = []
            id = []
            for item in cart_item:
                existing_variant = item.variant.all()
                ex_variant_list.append(list(existing_variant))
                id.append(item.id)

            if product_variant in ex_variant_list:
                index = ex_variant_list.index(product_variant)
                item_id = id[index]
                item = CartItem.objects.get(product=product, id=item_id)
                item.quantity += 1
                item.save()
            else:
                item = CartItem.objects.create(product=product, quantity=1, cart=cart)
                if len(product_variant) > 0:
                    item.variant.clear()
                    item.variant.add(*product_variant)
                item.save()
        else:
            cart_item = CartItem.objects.create(
                product = product,
                quantity = 1,
                cart = cart,
            )
            if len(product_variant) > 0:
                cart_item.variant.clear()
                for item in product_variant:
                    cart_item.variant.add(item)
            cart_item.save()
        return redirect('cart')

def remove_cart(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    except:
        pass
    return redirect('cart')

def remove_cart_item(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    if request.user.is_authenticated:
        cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)
    else:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
    cart_item.delete()
    return redirect('cart')

@login_required(login_url='login_user')
def checkout(request, total=0, quantity=0, cart_items=None):
    try:
        tax = 0
        grand_total = 0
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        total_discount = 0

        for cart_item in cart_items:
            if cart_item.product.offer_percentage > 0:
                discount_price = (cart_item.product.offer_percentage * cart_item.product.price) / 100
                total_discount += discount_price * cart_item.quantity
                cart_item.product.offer_price = cart_item.product.price - discount_price
                total += (cart_item.product.offer_price * cart_item.quantity)
                quantity += cart_item.quantity
            else:
                total += (cart_item.product.price * cart_item.quantity)
                quantity += cart_item.quantity
        #Total amount befor discount
        net_total = total + total_discount
        tax = (2 * total)/100
        #Total amount after discount
        grand_total = total + tax

    except ObjectDoesNotExist:
        pass

    current_user = request.user
    user_addresses = Address.objects.filter(user=current_user)



    if request.method == 'POST':
        # User selected an existing address
        selected_address_id = request.POST.get('selected_address', None)
        if selected_address_id:
            address = get_object_or_404(Address, id=selected_address_id)
        else:
            messages.error(request, "Please add at least one address before placing an order.")
            return redirect('orders:add_address_checkout')

        # Create the order object and associate it with the selected or new address
        data = Order()
        data.user = current_user
        data.address = address
        data.save()

    context = {
        'net_total': net_total,
        'total': total,
        'total_discount': total_discount,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
        'user_addresses': user_addresses,
    }
    return render(request, 'store/checkout.html', context)