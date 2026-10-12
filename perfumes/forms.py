from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Perfume

class PerfumeForm(forms.ModelForm):
    class Meta:
        model = Perfume
        fields = ['name', 'price', 'stock', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Perfume Name', 'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'min': 0, 'step': '0.01', 'class': 'form-control'}),
            'stock': forms.NumberInput(attrs={'min': 0, 'class': 'form-control'}),
        }

    def clean_price(self):
        price = self.cleaned_data['price']
        if price < 0:
            raise forms.ValidationError('Price cannot be negative.')
        return price


class RegistrationForm(UserCreationForm):
    """Use Django's username uniqueness and password validation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'
