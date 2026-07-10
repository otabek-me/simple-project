from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.forms import inlineformset_factory

from .models import Furniture, FurnitureDetail
from .forms import FurnitureForm, FurnitureDetailForm, BaseDetailFormSet

DetailFormSet = inlineformset_factory(
    Furniture,
    FurnitureDetail,
    form=FurnitureDetailForm,
    formset=BaseDetailFormSet,
    extra=1,
    can_delete=True,
)


def furniture_list(request):
    furnitures = Furniture.objects.prefetch_related('details')
    return render(request, 'app/furniture_list.html', {
        'furnitures': furnitures,
    })


def furniture_create(request):
    furniture = Furniture()
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
        'page_title': 'Yangi mebel qo‘shish',
    })


def furniture_edit(request, pk):
    furniture = get_object_or_404(Furniture, pk=pk)
    if request.method == 'POST':
        form = FurnitureForm(request.POST, instance=furniture)
        formset = DetailFormSet(request.POST, instance=furniture, prefix='details')
        if form.is_valid() and formset.is_valid():
            furniture = form.save(commit=False)
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
        'page_title': f"{furniture.name} narxini yangilash",
        'furniture': furniture,
    })


def furniture_delete(request, pk):
    furniture = get_object_or_404(Furniture, pk=pk)
    if request.method == 'POST':
        furniture.delete()
    return redirect(reverse('furniture_list'))
