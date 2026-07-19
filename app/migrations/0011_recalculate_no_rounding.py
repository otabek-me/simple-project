from django.db import migrations
from decimal import Decimal

def recalculate_no_rounding(apps, schema_editor):
    Furniture = apps.get_model('app', 'Furniture')
    for furniture in Furniture.objects.all():
        base = Decimal('0.00')
        for detail in furniture.details.all():
            base += detail.price * detail.quantity
        
        craft_amount = base * furniture.craft_fee_rate / Decimal('100')
        subtotal = base + craft_amount
        master_amount = subtotal * furniture.master_fee_rate / Decimal('100')
        subtotal = subtotal + master_amount
        owner_amount = subtotal * furniture.owner_fee_rate / Decimal('100')
        total = subtotal + owner_amount
        
        furniture.material_total = base
        furniture.craft_fee_amount = craft_amount
        furniture.master_fee_amount = master_amount
        furniture.owner_fee_amount = owner_amount
        furniture.total_price = total
        furniture.save()

class Migration(migrations.Migration):
    dependencies = [
        ('app', '0010_recalculate_all_furniture'),
    ]

    operations = [
        migrations.RunPython(recalculate_no_rounding),
    ]