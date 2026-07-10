from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.forms import inlineformset_factory

from .models import Detail, Furniture, FurnitureDetail
from .forms import DetailForm, FurnitureForm, FurnitureDetailForm, BaseDetailFormSet

DetailFormSet = inlineformset_factory(
    Furniture,
    FurnitureDetail,
    form=FurnitureDetailForm,
    formset=BaseDetailFormSet,
    extra=1,
    can_delete=True,
)


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
            details = formset.save(commit=False)
            for detail in details:
                detail.furniture = furniture
                detail.save()
            for detail in formset.deleted_objects:
                detail.delete()
            furniture.recalculate().save()
            return redirect(reverse('furniture_list'))
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
            details = formset.save(commit=False)
            for detail in details:
                detail.furniture = furniture
                detail.save()
            for detail in formset.deleted_objects:
                detail.delete()
            furniture.recalculate().save()
            return redirect(reverse('furniture_list'))
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
