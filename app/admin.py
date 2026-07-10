from django.contrib import admin

from .models import Detail, Furniture, FurnitureDetail


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
    list_display = ('detail', 'furniture', 'price', 'quantity')
    search_fields = ('detail__name',)


@admin.register(Detail)
class DetailAdmin(admin.ModelAdmin):
    list_display = ('name', 'price')
    search_fields = ('name',)
