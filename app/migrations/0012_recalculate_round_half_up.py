from django.db import migrations
from decimal import Decimal, ROUND_HALF_UP

CENTS = Decimal('0.01')


def to_money(value):
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def recalculate_round_half_up(apps, schema_editor):
    """
    Avvalgi versiyada narxlar Django'ning standart DecimalField saqlash
    xatti-harakati (ROUND_HALF_EVEN, "bankir yaxlitlashi") bilan saqlangan
    edi. Bu ba'zi hollarda 0.5 chegarasidagi summalarni kutilmagan
    tomonga yaxlitlagan. Bu migratsiya barcha mavjud mebellarni izchil
    ROUND_HALF_UP qoidasi bilan qayta hisoblaydi.
    """
    Furniture = apps.get_model('app', 'Furniture')
    for furniture in Furniture.objects.all():
        base = Decimal('0.00')
        for fd in furniture.details.all():
            base += fd.price * fd.quantity

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
        furniture.save()


def noop_reverse(apps, schema_editor):
    # Eski qiymatlarni tiklashning ilojisi yo'q (asl xato qiymatlar
    # saqlanmagan), shuning uchun orqaga qaytarish shunchaki hech narsa
    # qilmaydi.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('app', '0011_recalculate_no_rounding'),
    ]

    operations = [
        migrations.RunPython(recalculate_round_half_up, noop_reverse),
    ]
