from django.contrib import admin

from .models import Furniture, FurnitureDetail


class FurnitureDetailInline(admin.TabularInline):
    model = FurnitureDetail
    extra = 1


@admin.register(Furniture)
class FurnitureAdmin(admin.ModelAdmin):
    list_display = ('name', 'material_total', 'total_price', 'updated_at')
    search_fields = ('name',)
    inlines = [FurnitureDetailInline]


@admin.register(FurnitureDetail)
class FurnitureDetailAdmin(admin.ModelAdmin):
    list_display = ('name', 'furniture', 'price', 'quantity')
    search_fields = ('name',)
