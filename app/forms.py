from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm as DjangoAuthenticationForm
from django.contrib.auth.forms import PasswordChangeForm as DjangoPasswordChangeForm
from django.core.exceptions import ValidationError
from decimal import Decimal

from .models import Detail, Furniture, FurnitureDetail, Client, Sale, SaleItem, Payment


def _clean_whole_number(value, field_error):
    """Pul/foiz maydonlari faqat butun son bo'lishini talab qiladi."""
    if value is not None and value % 1 != 0:
        raise forms.ValidationError(field_error)
    return value


def _translate_password_error(message):
    translations = {
        'This password is too short. It must contain at least 8 characters.': 'Parol juda qisqa. Kamida 8 ta belgidan iborat bo‘lishi kerak.',
        'This password is too common.': 'Parol juda oddiy.',
        'This password is entirely numeric.': 'Parol faqat raqamlardan iborat.',
        'The password is too similar to the username.': 'Parol foydalanuvchi nomiga juda o‘xshash.',
        'This password is too similar to the username.': 'Parol foydalanuvchi nomiga juda o‘xshash.',
    }
    return translations.get(message, message)


class UzbekAuthenticationForm(DjangoAuthenticationForm):
    error_messages = {
        **DjangoAuthenticationForm.error_messages,
        'invalid_login': 'Foydalanuvchi nomi yoki parol noto‘g‘ri.',
        'inactive': 'Bu foydalanuvchi faol emas.',
    }


class UzbekPasswordChangeForm(DjangoPasswordChangeForm):
    error_messages = {
        **DjangoPasswordChangeForm.error_messages,
        'password_incorrect': 'Eski parol noto‘g‘ri.',
        'password_mismatch': 'Yangi parollar mos kelmadi.',
    }

    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        if password:
            try:
                password_validation.validate_password(password, self.user)
            except ValidationError as exc:
                raise forms.ValidationError([
                    _translate_password_error(message) for message in exc.messages
                ]) from exc
        return password


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
        error_messages = {
            'name': {
                'required': 'Mebel nomini kiriting.',
                'max_length': 'Mebel nomi 120 ta belgidan oshmasligi kerak.',
            },
            'craft_fee_rate': {
                'invalid': 'Iltimos, to‘g‘ri foiz kiriting.',
                'min_value': 'Foiz 0 dan kichik bo‘lishi mumkin emas.',
            },
            'master_fee_rate': {
                'invalid': 'Iltimos, to‘g‘ri foiz kiriting.',
                'min_value': 'Foiz 0 dan kichik bo‘lishi mumkin emas.',
            },
            'owner_fee_rate': {
                'invalid': 'Iltimos, to‘g‘ri foiz kiriting.',
                'min_value': 'Foiz 0 dan kichik bo‘lishi mumkin emas.',
            },
        }

    def clean_craft_fee_rate(self):
        return _clean_whole_number(
            self.cleaned_data.get('craft_fee_rate'),
            'Foiz butun son bo‘lishi kerak (masalan: 2).',
        )

    def clean_master_fee_rate(self):
        return _clean_whole_number(
            self.cleaned_data.get('master_fee_rate'),
            'Foiz butun son bo‘lishi kerak (masalan: 5).',
        )

    def clean_owner_fee_rate(self):
        return _clean_whole_number(
            self.cleaned_data.get('owner_fee_rate'),
            'Foiz butun son bo‘lishi kerak (masalan: 10).',
        )


class DetailSelect(forms.Select):
    """Har bir option ga data-price qo'shadi — JS hisob matn parse qilmasin."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value and hasattr(value, 'instance') and value.instance is not None:
            option['attrs']['data-price'] = str(value.instance.price)
        return option


class DetailChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.name} — {obj.price}"


class FurnitureDetailForm(forms.ModelForm):
    detail = DetailChoiceField(
        queryset=Detail.objects.all(),
        label='Detal',
        empty_label='- Detal tanlang -',
        widget=DetailSelect(attrs={'class': 'field-input detail-select'}),
        error_messages={
            'required': 'Detalni tanlang.',
            'invalid_choice': 'Noto‘g‘ri detal tanlandi.',
        },
    )

    class Meta:
        model = FurnitureDetail
        fields = ['detail', 'quantity']
        labels = {
            'detail': 'Detal',
            'quantity': 'Soni',
        }
        widgets = {
            'quantity': forms.NumberInput(attrs={'placeholder': 'Soni (mas: 2.5)', 'class': 'field-input quantity-input', 'min': '0.01', 'step': '0.01'}),
        }
        error_messages = {
            'quantity': {
                'required': 'Soni maydonini to‘ldiring.',
                'invalid': 'Iltimos, to‘g‘ri son kiriting (masalan: 2.5).',
                'min_value': 'Soni 0.01 dan kichik bo‘lishi mumkin emas.',
            },
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
            'price': forms.TextInput(attrs={'placeholder': 'Narxi', 'class': 'field-input money-input', 'inputmode': 'decimal'}),
        }
        error_messages = {
            'name': {
                'required': 'Detal nomini kiriting.',
                'max_length': 'Detal nomi 120 ta belgidan oshmasligi kerak.',
            },
            'price': {
                'required': 'Narxni kiriting.',
                'invalid': 'Iltimos, to‘g‘ri narx kiriting.',
                'min_value': 'Narx 0 dan kichik bo‘lishi mumkin emas.',
            },
        }

    def clean_price(self):
        return _clean_whole_number(
            self.cleaned_data.get('price'),
            'Narx butun son bo‘lishi kerak (masalan: 150000).',
        )


class BaseDetailFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(
            form.cleaned_data and not form.cleaned_data.get('DELETE', False)
            for form in self.forms
        ):
            return
        raise forms.ValidationError('Kamida bitta detal kiriting.')


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['name', 'phone', 'address', 'notes']
        labels = {
            'name': 'Ism',
            'phone': 'Telefon',
            'address': 'Manzil',
            'notes': 'Izoh',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Klient ismi', 'class': 'field-input', 'required': True}),
            'phone': forms.TextInput(attrs={'placeholder': '+998 xx xxx xx xx', 'class': 'field-input'}),
            'address': forms.Textarea(attrs={'placeholder': 'Manzil', 'class': 'field-input', 'rows': 2}),
            'notes': forms.Textarea(attrs={'placeholder': 'Izoh', 'class': 'field-input', 'rows': 2}),
        }


class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ['furniture', 'quantity', 'price_at_sale', 'cost_at_sale']
        labels = {
            'furniture': 'Mebel',
            'quantity': 'Soni',
            'price_at_sale': 'Narxi',
            'cost_at_sale': 'Tannarx',
        }
        widgets = {
            'furniture': forms.Select(attrs={'class': 'field-input furniture-select'}),
            'quantity': forms.NumberInput(attrs={'class': 'field-input quantity-input', 'min': '0.01', 'step': '1', 'value': 1}),
            'price_at_sale': forms.TextInput(attrs={'class': 'field-input price-input money-input', 'inputmode': 'decimal'}),
            'cost_at_sale': forms.TextInput(attrs={'class': 'field-input cost-input money-input', 'inputmode': 'decimal'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Faqat zahirada bor mebellarni ko'rsatish
        self.fields['furniture'].queryset = Furniture.objects.filter(quantity__gt=0).order_by('name')
        self.fields['furniture'].empty_label = '- Mebel tanlang -'
        # Mebel nomiga zahiradagi sonini qo'shish
        self.fields['furniture'].label_from_instance = lambda obj: f"{obj.name} ({obj.quantity} ta)"


class BaseSaleItemFormSet(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(
            form.cleaned_data and not form.cleaned_data.get('DELETE', False)
            for form in self.forms
        ):
            return
        raise forms.ValidationError('Kamida bitta mebel qo\'shing.')


class SaleForm(forms.ModelForm):
    new_client_name = forms.CharField(
        required=False,
        label='Yangi klient',
        widget=forms.TextInput(attrs={'placeholder': 'Yangi klient ismi', 'class': 'field-input'}),
    )
    new_client_phone = forms.CharField(
        required=False,
        label='Telefon',
        widget=forms.TextInput(attrs={'placeholder': '+998 xx xxx xx xx', 'class': 'field-input'}),
    )

    class Meta:
        model = Sale
        fields = ['client', 'payment_type', 'notes']
        labels = {
            'client': 'Klient',
            'payment_type': "To'lov turi",
            'notes': 'Izoh',
        }
        widgets = {
            'client': forms.Select(attrs={'class': 'field-input client-select'}),
            'payment_type': forms.Select(attrs={'class': 'field-input'}),
            'notes': forms.Textarea(attrs={'placeholder': 'Qo\'shimcha izoh', 'class': 'field-input', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['client'].empty_label = '- Klientni tanlang yoki yangisini qo\'shing -'
        # Order clients alphabetically
        self.fields['client'].queryset = Client.objects.all().order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        client = cleaned_data.get('client')
        new_name = cleaned_data.get('new_client_name')

        if not client and not new_name:
            raise forms.ValidationError('Klientni tanlang yoki yangi klient qo\'shing.')

        if new_name:
            # Create or get client
            client, created = Client.objects.get_or_create(
                name=new_name.strip(),
                defaults={
                    'phone': cleaned_data.get('new_client_phone', ''),
                }
            )
            cleaned_data['client'] = client

        return cleaned_data


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'notes']
        labels = {
            'amount': "To'lov summasi",
            'notes': 'Izoh',
        }
        widgets = {
            'amount': forms.TextInput(attrs={'class': 'field-input money-input', 'placeholder': "To'lov summasi", 'inputmode': 'decimal'}),
            'notes': forms.TextInput(attrs={'placeholder': 'Izoh', 'class': 'field-input'}),
        }


class ReserveAddForm(forms.Form):
    """Zahiraga mebel qo'shish formasi."""
    furniture = forms.ModelChoiceField(
        queryset=Furniture.objects.all().order_by('name'),
        label='Mebel',
        empty_label='- Mebel tanlang -',
        widget=forms.Select(attrs={'class': 'field-input'}),
    )
    quantity = forms.IntegerField(
        label='Soni',
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={'class': 'field-input', 'min': '1', 'step': '1', 'value': 1}),
    )