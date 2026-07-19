from django.contrib import messages
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.forms import inlineformset_factory

from .models import Detail, Furniture, FurnitureDetail
from .forms import (
    DetailForm,
    FurnitureForm,
    FurnitureDetailForm,
    BaseDetailFormSet,
    UzbekAuthenticationForm,
    UzbekPasswordChangeForm,
)

DetailFormSet = inlineformset_factory(
    Furniture,
    FurnitureDetail,
    form=FurnitureDetailForm,
    formset=BaseDetailFormSet,
    extra=0,
    can_delete=True,
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
    furnitures = Furniture.objects.prefetch_related('details__detail')
    return render(request, 'app/furniture_list.html', {
        'furnitures': furnitures,
    })


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
    })


@login_required
def furniture_edit(request, pk):
    furniture = get_object_or_404(Furniture, pk=pk)
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


def furniture_delete(request, pk):
    furniture = get_object_or_404(Furniture, pk=pk)
    if request.method == 'POST':
        furniture.delete()
    return redirect(reverse('furniture_list'))