from django import forms
from .models import Order


class ChangeStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']


class SalesReportForm(forms.Form):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Start Date'
    )
    end_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='End Date'
    )
