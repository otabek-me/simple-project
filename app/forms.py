from django import forms

from .models import Detail, Furniture, FurnitureDetail


class FurnitureForm(forms.ModelForm):
    class Meta:
        model = Furniture
        fields = ['name', 'craft_fee_rate', 'master_fee_rate', 'owner_fee_rate']
        labels = {
            'name': 'Mebel nomi',
            'craft_fee_rate': 'Detal ustama (%)',
            'master_fee_rate': 'Usta haqi (%)',
            'owner_fee_rate': 'Sizning foyda (%)',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Mebel nomi', 'class': 'field-input'}),
            'craft_fee_rate': forms.NumberInput(attrs={'class': 'field-input', 'step': '1', 'min': '0', 'max': '99999999', 'inputmode': 'numeric', 'pattern': '[0-9]*'}),
            'master_fee_rate': forms.NumberInput(attrs={'class': 'field-input', 'step': '1', 'min': '0', 'max': '99999999', 'inputmode': 'numeric', 'pattern': '[0-9]*'}),
            'owner_fee_rate': forms.NumberInput(attrs={'class': 'field-input', 'step': '1', 'min': '0', 'max': '99999999', 'inputmode': 'numeric', 'pattern': '[0-9]*'}),
        }


class DetailChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} — {obj.price}"


class FurnitureDetailForm(forms.ModelForm):
    detail = DetailChoiceField(
        queryset=Detail.objects.all(),
        label='Detal',
        empty_label='- Detal tanlang -',
        widget=forms.Select(attrs={'class': 'field-input detail-select'}),
    )

    class Meta:
        model = FurnitureDetail
        fields = ['detail', 'quantity']
        labels = {
            'detail': 'Detal',
            'quantity': 'Soni',
        }
        widgets = {
            'quantity': forms.NumberInput(attrs={'placeholder': 'Soni', 'class': 'field-input quantity-input', 'min': '1', 'step': '1'}),
        }


class DetailForm(forms.ModelForm):
    class Meta:
        model = Detail
        fields = ['name', 'price']
        labels = {
            'name': 'Detal nomi',
            'price': 'Narxi',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Detal nomi', 'class': 'field-input'}),
            'price': forms.NumberInput(attrs={'placeholder': 'Narxi', 'class': 'field-input', 'step': '1', 'min': '0', 'inputmode': 'numeric', 'pattern': '[0-9]*'}),
        }


class BaseDetailFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(
            form.cleaned_data and not form.cleaned_data.get('DELETE', False)
            for form in self.forms
        ):
            return
        raise forms.ValidationError('Kamida bitta detal kiriting.')
