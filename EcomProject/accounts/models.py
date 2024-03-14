from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import User
from django.conf import settings
import uuid

# Create your models here.

class MyAccountManager(BaseUserManager):
    def create_user(self, first_name, last_name, phone_number, email, password=None):
        if not email:
            raise ValueError('User must have an email address')

        user = self.model(
            email = self.normalize_email(email),
            phone_number = phone_number,
            first_name = first_name,
            last_name = last_name
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, first_name, last_name, email, phone_number, password):
        user = self.create_user(
            email = self.normalize_email(email),
            phone_number = phone_number,
            password = password,
            first_name = first_name,
            last_name = last_name
        )

        user.is_admin = True
        user.is_active = True
        user.is_staff = True
        user.is_superadmin = True
        user.save(using=self._db)
        return user


class Account(AbstractBaseUser):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=12, unique=True, default='')
    wallet = models.FloatField(null=True, default=0.0)

    #     Required
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now_add=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superadmin = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone_number']

    objects = MyAccountManager()

    class Meta:
        verbose_name = 'account'
        verbose_name_plural = 'accounts'

    def __str__(self):
        return self.email

    def has_perm(self, perm, obj=None):
        return self.is_admin

    def has_module_perms(self, add_label):
        return True
class Profile(models.Model):
    user = models.OneToOneField(Account, on_delete=models.CASCADE, related_name='profile')
    otp = models.CharField(max_length=100, null=True, blank=True)
    uid = models.CharField(default=f'{uuid.uuid4}',max_length=200)

class UserProfile(models.Model):
    user = models.OneToOneField(Account, on_delete=models.CASCADE)
    phone_number = models.CharField(blank=True, max_length=15)
    address_line_1 = models.CharField(blank=True, max_length=100)
    address_line_2 = models.CharField(blank=True, max_length=100)
    profile_picture = models.ImageField(blank=True, upload_to='userprofile')
    city = models.CharField(max_length=20, blank=True)
    state = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.first_name

    def full_address(self):
        return f'{self.address_line_1} {self.address_line_2}'

class Address(models.Model):
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=20, default='')
    phone_number = models.CharField(max_length=15)
    address_line_1 = models.CharField(max_length=100)
    address_line_2 = models.CharField(blank=True, max_length=100)
    city = models.CharField(max_length=20)
    state = models.CharField(max_length=20)
    country = models.CharField(max_length=20)
    zipcode = models.CharField(max_length=6)

    def __str__(self):
        return self.full_name

