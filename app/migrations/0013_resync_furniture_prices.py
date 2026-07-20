from django.db import migrations


def resync_all(apps, schema_editor):
    """Eski FurnitureDetail.price snapshotlarini joriy Detail narxiga moslashtiradi."""
    from decimal import Decimal, ROUND_HALF_UP

    Detail = apps.get_model('app', 'Detail')
    Furniture = apps.get_model('app', 'Furniture')
    FurnitureDetail = apps.get_model('app', 'FurnitureDetail')

    cents = Decimal('0.01')

    def to_money(value):
        return value.quantize(cents, rounding=ROUND_HALF_UP)

    # Snapshotlarni sinxronlash
    for fd in FurnitureDetail.objects.select_related('detail').all():
        if fd.detail_id and fd.detail is not None:
            changed = False
            if fd.price != fd.detail.price:
                fd.price = fd.detail.price
                changed = True
            if fd.name != fd.detail.name:
                fd.name = fd.detail.name
                changed = True
            if changed:
                fd.save(update_fields=['price', 'name'])

    # Barcha mebellarni qayta hisoblash
    for furniture in Furniture.objects.all():
        base = Decimal('0.00')
        for fd in furniture.details.select_related('detail').all():
            unit = fd.detail.price if fd.detail_id and fd.detail is not None else fd.price
            base += unit * fd.quantity
        craft_amount = base * furniture.craft_fee_rate / Decimal('100')
        subtotal = base + craft_amount
        master_amount = subtotal * furniture.master_fee_rate / Decimal('100')
        subtotal = subtotal + master_amount
        owner_amount = subtotal * furniture.owner_fee_rate / Decimal('100')
        total = subtotal + owner_amount
        furniture.material_total = to_money(base)
        furniture.craft_fee_amount = to_money(craft_amount)
        furniture.master_fee_amount = to_money(master_amount)
        furniture.owner_fee_amount = to_money(owner_amount)
        furniture.total_price = to_money(total)
        furniture.save(update_fields=[
            'material_total',
            'craft_fee_amount',
            'master_fee_amount',
            'owner_fee_amount',
            'total_price',
        ])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0012_recalculate_round_half_up'),
    ]

    operations = [
        migrations.RunPython(resync_all, noop),
    ]
