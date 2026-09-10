from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.forms import inlineformset_factory
from django.db.models import Sum, Count, Q, DecimalField, F
from django.db.models.functions import TruncMonth, TruncDay
from decimal import Decimal
from django.utils import timezone

from .models import Detail, Furniture, FurnitureDetail, Client, Sale, SaleItem, Payment, to_money
from .forms import (
    DetailForm,
    FurnitureForm,
    FurnitureDetailForm,
    BaseDetailFormSet,
    UzbekAuthenticationForm,
    UzbekPasswordChangeForm,
    ClientForm,
    SaleForm,
    SaleItemForm,
    BaseSaleItemFormSet,
    PaymentForm,
    ReserveAddForm,
)

DetailFormSet = inlineformset_factory(
    Furniture,
    FurnitureDetail,
    form=FurnitureDetailForm,
    formset=BaseDetailFormSet,
    extra=0,
    can_delete=True,
)

SaleItemFormSet = inlineformset_factory(
    Sale,
    SaleItem,
    form=SaleItemForm,
    formset=BaseSaleItemFormSet,
    extra=1,
    can_delete=True,
    can_delete_extra=True,
)


def auth_page(request):
    if request.method == 'POST' and 'login_submit' in request.POST:
        login_form = UzbekAuthenticationForm(request, data=request.POST)
        if login_form.is_valid():
            login(request, login_form.get_user())
            return redirect(reverse('furniture_list'))
    else:
        login_form = UzbekAuthenticationForm(request)

    password_form = None
    if request.user.is_authenticated:
        if request.method == 'POST' and 'password_submit' in request.POST:
            password_form = UzbekPasswordChangeForm(request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, password_form.user)
                messages.success(request, 'Parol muvaffaqiyatli o\'zgartirildi.')
                return redirect(reverse('furniture_list'))
        else:
            password_form = UzbekPasswordChangeForm(request.user)

    login_form.fields['username'].widget.attrs.update({'class': 'field-input', 'placeholder': 'Foydalanuvchi nomi'})
    login_form.fields['password'].widget.attrs.update({'class': 'field-input', 'placeholder': 'Parol'})

    if password_form is not None:
        password_form.fields['old_password'].widget.attrs.update({'class': 'field-input', 'placeholder': 'Eski parol'})
        password_form.fields['new_password1'].widget.attrs.update({'class': 'field-input', 'placeholder': 'Yangi parol'})
        password_form.fields['new_password2'].widget.attrs.update({'class': 'field-input', 'placeholder': 'Yangi parolni takrorlang'})

    return render(request, 'registration/login.html', {
        'login_form': login_form,
        'password_form': password_form,
    })


@login_required
def furniture_list(request):
    furnitures = list(Furniture.objects.prefetch_related('details__detail'))
    # Ro'yxatda ham joriy detal narxlari bilan mos summa ko'rinsin
    dirty_fields = (
        'material_total',
        'craft_fee_amount',
        'master_fee_amount',
        'owner_fee_amount',
        'total_price',
    )
    for furniture in furnitures:
        before = {field: getattr(furniture, field) for field in dirty_fields}
        furniture.recalculate()
        if any(getattr(furniture, field) != before[field] for field in dirty_fields):
            furniture.save()
    return render(request, 'app/furniture_list.html', {
        'furnitures': furnitures,
    })


@login_required
def reserve_list(request):
    """Zahiradagi mebellar ro'yxati."""
    furnitures = list(Furniture.objects.prefetch_related('details__detail').order_by('name'))
    # Ro'yxatda ham joriy detal narxlari bilan mos summa ko'rinsin
    dirty_fields = (
        'material_total',
        'craft_fee_amount',
        'master_fee_amount',
        'owner_fee_amount',
        'total_price',
    )
    for furniture in furnitures:
        before = {field: getattr(furniture, field) for field in dirty_fields}
        furniture.recalculate()
        if any(getattr(furniture, field) != before[field] for field in dirty_fields):
            furniture.save()

    add_form = ReserveAddForm()
    if request.method == 'POST' and 'reserve_add_submit' in request.POST:
        add_form = ReserveAddForm(request.POST)
        if add_form.is_valid():
            furniture = add_form.cleaned_data['furniture']
            quantity = add_form.cleaned_data['quantity']
            furniture.add_quantity(quantity)
            messages.success(request, f"{furniture.name} zahiraga qo'shildi: +{quantity}")
            return redirect(reverse('reserve_list'))

    return render(request, 'app/reserve_list.html', {
        'furnitures': furnitures,
        'add_form': add_form,
    })


@login_required
def reserve_edit(request, pk):
    """Zahiradagi mebel sonini o'zgartirish."""
    furniture = get_object_or_404(Furniture, pk=pk)
    if request.method == 'POST':
        new_quantity = request.POST.get('quantity')
        try:
            new_quantity = int(new_quantity)
            if new_quantity < 0:
                raise ValueError
            furniture.quantity = new_quantity
            furniture.save(update_fields=['quantity'])
            messages.success(request, f"{furniture.name} soni yangilandi: {new_quantity}")
        except (ValueError, TypeError):
            messages.error(request, "Iltimos, to'g'ri butun son kiriting.")
    return redirect(reverse('reserve_list'))


@login_required
def reserve_delete(request, pk):
    """Zahiradagi mebelni o'chirish."""
    furniture = get_object_or_404(Furniture, pk=pk)
    if request.method == 'POST':
        furniture.delete()
        messages.success(request, f"{furniture.name} zahira ro'yxatidan o'chirildi.")
    return redirect(reverse('reserve_list'))




@login_required
def furniture_create(request):
    furniture = Furniture()
    details_queryset = Detail.objects.all()
    if request.method == 'POST':
        form = FurnitureForm(request.POST, instance=furniture)
        formset = DetailFormSet(request.POST, instance=furniture, prefix='details')
        if form.is_valid() and formset.is_valid():
            furniture = form.save(commit=False)
            furniture.save()
            formset.instance = furniture
            formset.save()
            furniture.recalculate().save()
            return redirect(reverse('furniture_list'))
        else:
            errors = []
            if not form.is_valid():
                for field, errs in form.errors.items():
                    for err in errs:
                        errors.append(str(err))
            if not formset.is_valid():
                if formset.non_form_errors():
                    errors.extend(formset.non_form_errors())
                for f in formset.forms:
                    for field, errs in f.errors.items():
                        for err in errs:
                            errors.append(str(err))
            if errors:
                messages.error(request, 'Ma\'lumotlarni to\'g\'ri to\'ldiring! Xatoliklarni tekshiring.')
    else:
        form = FurnitureForm(instance=furniture)
        formset = DetailFormSet(instance=furniture, prefix='details')

    return render(request, 'app/furniture_form.html', {
        'form': form,
        'formset': formset,
        'detail_options': details_queryset,
        'page_title': 'Yangi mebel qo‘shish',
        'furniture': furniture,
    })


@login_required
def furniture_edit(request, pk):
    furniture = get_object_or_404(
        Furniture.objects.prefetch_related('details__detail'),
        pk=pk,
    )
    # Forma ochilganda ham joriy detal narxlari bilan mos summa ko'rinsin
    dirty_fields = (
        'material_total',
        'craft_fee_amount',
        'master_fee_amount',
        'owner_fee_amount',
        'total_price',
    )
    before = {field: getattr(furniture, field) for field in dirty_fields}
    furniture.recalculate()
    if any(getattr(furniture, field) != before[field] for field in dirty_fields):
        furniture.save()

    details_queryset = Detail.objects.all()
    if request.method == 'POST':

        form = FurnitureForm(request.POST, instance=furniture)
        formset = DetailFormSet(request.POST, instance=furniture, prefix='details')
        if form.is_valid() and formset.is_valid():
            furniture = form.save(commit=False)
            furniture.save()
            formset.instance = furniture
            formset.save()
            furniture.recalculate().save()
            return redirect(reverse('furniture_list'))
        else:
            errors = []
            if not form.is_valid():
                for field, errs in form.errors.items():
                    for err in errs:
                        errors.append(str(err))
            if not formset.is_valid():
                if formset.non_form_errors():
                    errors.extend(formset.non_form_errors())
                for f in formset.forms:
                    for field, errs in f.errors.items():
                        for err in errs:
                            errors.append(str(err))
            if errors:
                messages.error(request, 'Ma\'lumotlarni to\'g\'ri to\'ldiring! Xatoliklarni tekshiring.')
    else:
        form = FurnitureForm(instance=furniture)
        formset = DetailFormSet(instance=furniture, prefix='details')

    return render(request, 'app/furniture_form.html', {
        'form': form,
        'formset': formset,
        'detail_options': details_queryset,
        'page_title': f"{furniture.name} narxini yangilash",
        'furniture': furniture,
    })


@login_required
def detail_list(request):
    query = request.GET.get('q', '').strip()
    details = Detail.objects.all()
    if query:
        details = details.filter(name__icontains=query)
    if request.method == 'POST':
        form = DetailForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse('detail_list'))
    else:
        form = DetailForm()

    return render(request, 'app/detail_list.html', {
        'details': details,
        'form': form,
        'query': query,
    })


@login_required
def detail_edit(request, pk):
    detail = get_object_or_404(Detail, pk=pk)
    if request.method == 'POST':
        form = DetailForm(request.POST, instance=detail)
        if form.is_valid():
            form.save()
            return redirect(reverse('detail_list'))
    else:
        form = DetailForm(instance=detail)

    return render(request, 'app/detail_form.html', {
        'form': form,
        'detail': detail,
    })


@login_required
def detail_delete(request, pk):
    detail = get_object_or_404(Detail, pk=pk)
    if request.method == 'POST':
        detail.delete()
    return redirect(reverse('detail_list'))


@login_required
def furniture_delete(request, pk):
    furniture = get_object_or_404(Furniture, pk=pk)
    if request.method == 'POST':
        furniture.delete()
    return redirect(reverse('furniture_list'))


@login_required
def sale_create(request):
    # Faqat zahirada bor mebellarni ko'rsatish
    furnitures = Furniture.objects.filter(quantity__gt=0).order_by('name')
    if request.method == 'POST':
        form = SaleForm(request.POST)
        formset = SaleItemFormSet(request.POST, prefix='items')
        # On POST, don't add extra empty form — only show submitted forms
        formset.extra = 0

        if form.is_valid() and formset.is_valid():
            sale = form.save(commit=False)
            sale.created_by = request.user
            sale.total_amount = Decimal('0')
            sale.paid_amount = Decimal('0')
            sale.save()

            formset.instance = sale
            formset.save()

            # Calculate total
            total = Decimal('0')
            for item in sale.items.all():
                total += item.subtotal
            sale.total_amount = total
            if sale.payment_type == 'cash':
                sale.paid_amount = total
            sale.save()

            messages.success(request, f"Sotuv muvaffaqiyatli qo'shildi! Jami: {total}")
            return redirect(reverse('sale_list'))
        else:
            errors = []
            if not form.is_valid():
                for field, errs in form.errors.items():
                    for err in errs:
                        errors.append(str(err))
            if not formset.is_valid():
                if formset.non_form_errors():
                    errors.extend(formset.non_form_errors())
                for f in formset.forms:
                    for field, errs in f.errors.items():
                        for err in errs:
                            errors.append(str(err))
            if errors:
                messages.error(request, 'Ma\'lumotlarni to\'g\'ri to\'ldiring!')
    else:
        form = SaleForm()
        formset = SaleItemFormSet(prefix='items')

    return render(request, 'app/sale_form.html', {
        'form': form,
        'formset': formset,
        'furnitures': furnitures,
        'page_title': 'Yangi sotuv qo\'shish',
    })


@login_required
def sale_list(request):
    sales = Sale.objects.select_related('client').prefetch_related('items__furniture').all()
    query = request.GET.get('q', '').strip()
    if query:
        sales = sales.filter(
            Q(client__name__icontains=query) |
            Q(notes__icontains=query)
        )
    payment_filter = request.GET.get('payment', '').strip()
    if payment_filter:
        if payment_filter == 'cash':
            sales = sales.filter(payment_type='cash')
        elif payment_filter == 'credit':
            sales = sales.filter(payment_type='credit')
        elif payment_filter == 'debt':
            sales = sales.filter(total_amount__gt=F('paid_amount'))
    status_filter = request.GET.get('status', '').strip()
    if status_filter:
        sales = sales.filter(status=status_filter)

    return render(request, 'app/sale_list.html', {
        'sales': sales,
        'query': query,
        'payment_filter': payment_filter,
        'status_filter': status_filter,
    })


@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related('client', 'created_by', 'cancelled_by').prefetch_related(
            'items__furniture', 'payments'
        ),
        pk=pk,
    )
    payment_form = None
    if request.method == 'POST' and 'payment_submit' in request.POST:
        payment_form = PaymentForm(request.POST)
        if payment_form.is_valid():
            payment = payment_form.save(commit=False)
            payment.sale = sale
            payment.save()
            messages.success(request, f"To'lov qo'shildi: {payment.amount}")
            return redirect(reverse('sale_detail', args=[pk]))
    else:
        payment_form = PaymentForm()

    return render(request, 'app/sale_detail.html', {
        'sale': sale,
        'payment_form': payment_form,
    })


@login_required
def sale_cancel(request, pk):
    """Sotuvni bekor qiladi va mebellarni zahiraga qaytaradi."""
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == 'POST':
        if sale.status == 'active':
            sale.cancel(user=request.user)
            messages.success(request, f"Sotuv bekor qilindi. Mebellar zahiraga qaytarildi.")
        else:
            messages.warning(request, "Bu sotuv allaqachon bekor qilingan.")
    return redirect(reverse('sale_detail', args=[pk]))


@login_required
def sale_delete(request, pk):
    """Bekor qilingan sotuvni butunlay o'chirib tashlaydi."""
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == 'POST':
        if sale.status == 'cancelled':
            sale.delete()
            messages.success(request, "Bekor qilingan sotuv o'chirildi.")
            return redirect(reverse('sale_list'))
        else:
            messages.warning(request, "Faqat bekor qilingan sotuvlarni o'chirish mumkin.")
    return redirect(reverse('sale_detail', args=[pk]))


@login_required
def close_credit(request, pk):
    """Nasiyani bir tugma bilan to'liq yopadi (qolgan summani to'laydi)."""
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == 'POST':
        if sale.status != 'active':
            messages.warning(request, "Bu sotuv faol emas.")
        elif sale.payment_type != 'credit':
            messages.warning(request, "Bu sotuv nasiya emas.")
        else:
            remaining = sale.debt_amount()
            if remaining > 0:
                Payment.objects.create(
                    sale=sale,
                    amount=to_money(remaining),
                    notes="Nasiya to'liq yopildi",
                )
                # Nasiya to'liq yopilgach to'lov turini nasiyadan naqtga o'zgartirish
                sale.payment_type = 'cash'
                sale.save()
                messages.success(request, f"Nasiya to'liq yopildi. Qolgan summa: {to_money(remaining)}. To'lov turi naqtga o'zgartirildi.")
            else:
                messages.info(request, "Nasiya allaqachon to'liq to'langan.")
    return redirect(reverse('sale_detail', args=[pk]))


@login_required
def client_list(request):
    clients = Client.objects.annotate(
        total_purchases_sum=Sum('sales__total_amount', filter=Q(sales__status='active')),
        total_paid_sum=Sum('sales__paid_amount', filter=Q(sales__status='active')),
        sales_count=Count('sales', filter=Q(sales__status='active')),
    ).order_by('name')
    for client in clients:
        purchases = client.total_purchases_sum or Decimal('0')
        paid = client.total_paid_sum or Decimal('0')
        client.total_debt = purchases - paid
    query = request.GET.get('q', '').strip()
    if query:
        clients = clients.filter(name__icontains=query)

    return render(request, 'app/client_list.html', {
        'clients': clients,
        'query': query,
    })


@login_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk)
    sales = Sale.objects.filter(client=client).select_related('client').prefetch_related(
        'items__furniture', 'payments'
    ).order_by('-created_at')

    total_purchases = Decimal('0')
    total_paid = Decimal('0')
    for sale in sales:
        total_purchases += sale.total_amount
        total_paid += sale.paid_amount
    total_debt = total_purchases - total_paid

    # Sales by furniture type
    furniture_stats = {}
    for sale in sales:
        for item in sale.items.all():
            name = item.furniture_name or (item.furniture.name if item.furniture else 'Noma\'lum')
            if name not in furniture_stats:
                furniture_stats[name] = {
                    'count': 0,
                    'total': Decimal('0'),
                    'cost': Decimal('0'),
                    'profit': Decimal('0'),
                }
            furniture_stats[name]['count'] += int(item.quantity)
            furniture_stats[name]['total'] += item.subtotal
            furniture_stats[name]['cost'] += item.cost_subtotal
            furniture_stats[name]['profit'] += item.profit_subtotal

    return render(request, 'app/client_detail.html', {
        'client': client,
        'sales': sales,
        'total_purchases': total_purchases,
        'total_paid': total_paid,
        'total_debt': total_debt,
        'furniture_stats': furniture_stats,
    })


@login_required
def statistics(request):
    # Overall statistics (faqat faol sotuvlar)
    active_sales = Sale.objects.filter(status='active')
    total_sales_count = active_sales.count()
    total_clients = Client.objects.count()

    total_amount = active_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    total_paid = active_sales.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0')
    total_debt = total_amount - total_paid

    cash_sales = active_sales.filter(payment_type='cash')
    cash_total = cash_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')

    credit_sales = active_sales.filter(payment_type='credit')
    credit_total = credit_sales.aggregate(total=Sum('total_amount'))['total'] or Decimal('0')
    credit_paid = credit_sales.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0')
    credit_debt = credit_total - credit_paid

    # Top clients (faqat faol sotuvlar)
    top_clients = Client.objects.annotate(
        total_purchases_sum=Sum('sales__total_amount', filter=Q(sales__status='active')),
        total_paid_sum=Sum('sales__paid_amount', filter=Q(sales__status='active')),
        sales_count=Count('sales', filter=Q(sales__status='active')),
    ).filter(total_purchases_sum__isnull=False).order_by('-total_purchases_sum')[:10]

    # Top furniture sold (faqat faol sotuvlar)
    top_furniture = SaleItem.objects.filter(sale__status='active').values('furniture_name').annotate(
        total_quantity=Sum('quantity'),
        total_amount=Sum('subtotal'),
        cost_sum=Sum(
            F('cost_at_sale') * F('quantity'),
            output_field=DecimalField(max_digits=20, decimal_places=2),
        ),
        count=Count('id'),
    ).order_by('-total_amount')[:10]
    for tf_data in top_furniture:
        tf_data['cost_sum'] = tf_data['cost_sum'] or Decimal('0')
        tf_data['profit_sum'] = (tf_data['total_amount'] or Decimal('0')) - tf_data['cost_sum']

    # Monthly sales (faqat faol sotuvlar)
    monthly_sales = Sale.objects.filter(status='active').annotate(
        month=TruncMonth('created_at'),
    ).values('month').annotate(
        total=Sum('total_amount'),
        paid=Sum('paid_amount'),
        count=Count('id'),
    ).order_by('-month')[:12]
    for ms in monthly_sales:
        ms['debt'] = (ms['total'] or Decimal('0')) - (ms['paid'] or Decimal('0'))

    # Recent sales
    recent_sales = Sale.objects.select_related('client').prefetch_related('items__furniture').order_by('-created_at')[:10]

    # Calculate debt clients (faqat faol sotuvlar)
    debt_clients_list = []
    for c in Client.objects.all():
        purchases = c.total_purchases()
        paid = c.total_paid()
        debt = purchases - paid
        if debt > 0:
            debt_clients_list.append({
                'client': c,
                'purchases': purchases,
                'paid': paid,
                'debt': debt,
            })
    debt_clients_list.sort(key=lambda x: x['debt'], reverse=True)
    debt_clients_list = debt_clients_list[:10]

    return render(request, 'app/statistics.html', {
        'total_sales_count': total_sales_count,
        'total_clients': total_clients,
        'total_amount': total_amount,
        'total_paid': total_paid,
        'total_debt': total_debt,
        'cash_total': cash_total,
        'credit_total': credit_total,
        'credit_paid': credit_paid,
        'credit_debt': credit_debt,
        'top_clients': top_clients,
        'top_furniture': top_furniture,
        'monthly_sales': monthly_sales,
        'recent_sales': recent_sales,
        'debt_clients': debt_clients_list,
    })


def custom_page_not_found(request, exception):
    return render(request, 'app/error_page.html', {
        'status_code': 404,
        'message': 'Kechirasiz, bunday sahifa mavjud emas. URL manzilni tekshirib qaytadan urinib ko\'ring.',
    }, status=404)


def custom_server_error(request):
    return render(request, 'app/error_page.html', {
        'status_code': 500,
        'message': 'Serverda kutilmagan xatolik yuz berdi. Iltimos keyinroq qaytadan urinib ko\'ring.',
    }, status=500)


def custom_permission_denied(request, exception):
    return render(request, 'app/error_page.html', {
        'status_code': 403,
        'message': 'Bu sahifaga kirish huquqingiz yo\'q.',
    }, status=403)


@login_required
def add_payment(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.sale = sale
            payment.save()
            messages.success(request, f"To'lov qo'shildi: {payment.amount}")
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    messages.error(request, str(err))
    return redirect(reverse('sale_detail', args=[pk]))