from django.shortcuts import render
from store.models import Product
from django.views.decorators.cache import cache_control
# Create your views here.

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def home(request):
    products = Product.objects.all().filter(is_available=True)
    context = {
        'products' : products,
    }
    return render(request,'home.html', context)