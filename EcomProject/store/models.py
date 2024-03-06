from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from category.models import Category
from accounts.models import Account
# Create your models here.

class Product(models.Model):
    product_name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(max_length=500, blank=True)
    price = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Enter a number greater than zero")
    product_image = models.ImageField(upload_to='photos/products')
    stock = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Enter a number greater than zero")
    is_available = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    offer_percentage = models.PositiveIntegerField(default=0, blank=True, null=True)
    offer_price = models.PositiveIntegerField(default=0, blank=True, null=True)
    is_listed_offer = models.BooleanField(default=True)

    def get_url(self):
        return reverse('product_detail',args=[self.category.slug, self.slug])

    def __str__(self):
        return self.product_name

class VariantManager(models.Manager):
    def colors(self):
        return super(VariantManager, self).filter(variant_category = 'color', is_active = True)

    def sizes(self):
        return super(VariantManager, self).filter(variant_category = 'size', is_active = True)

variant_category_choice = (
    ('color', 'color'),
    ('size', 'size'),
    )

class Variant(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    variant_category = models.CharField(max_length=100, choices=variant_category_choice)
    variant_value = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now=True)

    objects = VariantManager()

    def __str__(self):
        return self.variant_value

class WishList(models.Model):
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    product = models.ManyToManyField(Product)
    created_at = models.DateTimeField(auto_now_add=True)