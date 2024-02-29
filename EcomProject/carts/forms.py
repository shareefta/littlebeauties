from django import forms
from .models import Coupons

class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupons
        fields = ('coupon_code', 'description', 'minimum_amount', 'discount', 'valid_from', 'valid_to')

        widgets = {
            'valid_from': forms.DateInput(attrs={'type': 'date'}),
            'valid_to': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(CouponForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'