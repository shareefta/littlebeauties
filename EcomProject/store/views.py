from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, WishList
from category.models import Category
from carts.views import _cart_id
from carts.models import Cart, CartItem
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.http import JsonResponse


def store(request, category_slug=None):
    categories = None
    products = None


    if category_slug != None:
        categories = get_object_or_404(Category, slug=category_slug)
        products = Product.objects.filter(category=categories, is_available=True)
        paginator = Paginator(products, 6)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        product_count = products.count()

        for item in products:
            discount_price = (item.offer_percentage * item.price)/100
            item.offer_price = item.price - discount_price
            item.save()

    else:
        products = Product.objects.all().filter(is_available=True).order_by('id')
        paginator = Paginator(products, 6)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        product_count = products.count()

        for item in products:
            discount_price = (item.offer_percentage * item.price)/100
            item.offer_price = item.price - discount_price
            item.save()

    context = {
        'products': paged_products,
        'product_count': product_count,
    }
    return render(request, 'store/store.html', context)


def product_detail(request, category_slug, product_slug):
    try:
        single_product = Product.objects.get(category__slug=category_slug, slug=product_slug)
        discount_price = (single_product.offer_percentage * single_product.price) / 100
        single_product.offer_price = single_product.price - discount_price
        single_product.save()

        in_cart = CartItem.objects.filter(cart__cart_id = _cart_id(request), product = single_product).exists()

        is_wish_list_item = False
        wishlist = WishList.objects.filter(user=request.user)
        for wish_list_item in wishlist:
            for product in wish_list_item.product.all():
                if single_product.id == product.id:
                    is_wish_list_item = True
                    break
    except Exception as e:
        raise e

    context = {
        'single_product': single_product,
        'in_cart' : in_cart,
        'is_wish_list_item': is_wish_list_item,
    }
    return render(request, 'store/product_detail.html', context)

def search(request):
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.order_by('-created_date').filter(Q(description__icontains=keyword) | Q(product_name__icontains=keyword))
            product_count = products.count()
    context = {
        'products' : products,
        'product_count' : product_count
    }
    return render(request, 'store/store.html', context)

@login_required(login_url='login_user')
def wishlist(request):
    # Fetch the wishlist items for the current user
    wishlist = WishList.objects.filter(user=request.user)
    context = {'wishlist': wishlist}
    return render(request, 'store/wishlist.html', context)

@login_required(login_url='login_user')
def add_to_wishlist(request, product_id):
    current_user = request.user
    single_product = get_object_or_404(Product, id=product_id)

    # Check if the product is already in the wishlist for the user
    if WishList.objects.filter(user=current_user, product=single_product).exists():
        return JsonResponse({'status': 'already_in_wishlist', 'single_product_id': single_product.id})
    else:
        # If not, add the product to the user's wishlist
        wishlist_item, created = WishList.objects.get_or_create(user=current_user)
        wishlist_item.product.add(single_product)

        return JsonResponse({'status': 'added_to_wishlist', 'single_product_id': single_product.id})

def delete_wishlist_item(request, wishlist_id, product_id):
    wishlist_item = get_object_or_404(WishList, id=wishlist_id)
    product = get_object_or_404(Product, id=product_id)

    # Remove the specific product from the wishlist
    wishlist_item.product.remove(product)

    return redirect('wishlist')
