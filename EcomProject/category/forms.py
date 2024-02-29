from django import forms
from django.core.validators import MinLengthValidator

from .models import Category


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['category_name', 'slug', 'description', 'category_image']

    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        self.fields['category_name'].widget.attrs['placeholder'] = 'Enter Category Name'
        self.fields['slug'].widget.attrs['placeholder'] = 'Slug'
        self.fields['description'].widget.attrs['placeholder'] = 'Enter Description'
        self.fields['category_image'].widget.attrs['placeholder'] = 'Upload Image'

        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'
            self.fields[field].validators.append(MinLengthValidator(limit_value=1))

    def clean(self):
        cleaned_data = super(CategoryForm, self).clean()
