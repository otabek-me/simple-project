from decimal import Decimal, ROUND_HALF_UP

from django.db import migrations, models

CENTS = Decimal('0.01')


def to_money(value):
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


def backfill_cost(apps, schema_editor):
    """Eski sotuv elementlariga joriy mebel tannarxini yozib chiqadi."""
    SaleItem = apps.get_model('app', 'SaleItem')
    for item in SaleItem.objects.select_related('furniture').all():
        f = item.furniture
        if f is not None and not item.cost_at_sale:
            item.cost_at_sale = to_money(
                f.material_total + f.craft_fee_amount + f.master_fee_amount
            )
            item.save(update_fields=['cost_at_sale'])


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0016_alter_furniture_quantity'),
    ]

    operations = [
        migrations.AddField(
            model_name='saleitem',
            name='cost_at_sale',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20, verbose_name='Birlik tannarxi'),
        ),
        migrations.RunPython(backfill_cost, migrations.RunPython.noop),
    ]