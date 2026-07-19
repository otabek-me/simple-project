from django.db import migrations
from decimal import Decimal

PRICE_QUANTIZE = Decimal('0.01')

def recalculate_all(apps, schema_editor):
    Furniture = apps.get_model('app', 'Furniture')
    for furniture in Furniture.objects.all():
        base = Decimal('0.00')
        for detail in furniture.details.all():
            base += detail.price * detail.quantity
        
        craft_amount = (base * furniture.craft_fee_rate / Decimal('100')).quantize(PRICE_QUANTIZE)
        subtotal = (base + craft_amount).quantize(PRICE_QUANTIZE)
        master_amount = (subtotal * furniture.master_fee_rate / Decimal('100')).quantize(PRICE_QUANTIZE)
        subtotal = (subtotal + master_amount).quantize(PRICE_QUANTIZE)
        owner_amount = (subtotal * furniture.owner_fee_rate / Decimal('100')).quantize(PRICE_QUANTIZE)
        total = (subtotal + owner_amount).quantize(PRICE_QUANTIZE)
        
        furniture.material_total = base.quantize(PRICE_QUANTIZE)
        furniture.craft_fee_amount = craft_amount
        furniture.master_fee_amount = master_amount
        furniture.owner_fee_amount = owner_amount
        furniture.total_price = total
        furniture.save()

class Migration(migrations.Migration):
    dependencies = [
        ('app', '0009_alter_detail_price_alter_furniture_craft_fee_amount_and_more'),
    ]

    operations = [
        migrations.RunPython(recalculate_all),
    ]