from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

PRICE_QUANTIZE = Decimal('1')


class Detail(models.Model):
    name = models.CharField(max_length=120)
    price = models.DecimalField(
        max_digits=20,
        decimal_places=0,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} — {self.price}"


class Furniture(models.Model):
    name = models.CharField(max_length=120)
    craft_fee_rate = models.DecimalField(
        max_digits=8,
        decimal_places=0,
        default=2,
        validators=[MinValueValidator(0)],
    )
    master_fee_rate = models.DecimalField(
        max_digits=8,
        decimal_places=0,
        default=5,
        validators=[MinValueValidator(0)],
    )
    owner_fee_rate = models.DecimalField(
        max_digits=8,
        decimal_places=0,
        default=10,
        validators=[MinValueValidator(0)],
    )
    material_total = models.DecimalField(
        max_digits=20,
        decimal_places=0,
        default=0,
        editable=False,
    )
    craft_fee_amount = models.DecimalField(
        max_digits=20,
        decimal_places=0,
        default=0,
        editable=False,
    )
    master_fee_amount = models.DecimalField(
        max_digits=20,
        decimal_places=0,
        default=0,
        editable=False,
    )
    owner_fee_amount = models.DecimalField(
        max_digits=20,
        decimal_places=0,
        default=0,
        editable=False,
    )
    total_price = models.DecimalField(
        max_digits=20,
        decimal_places=0,
        default=0,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-created_at']

    def __str__(self):
        return self.name

    def recalculate(self):
        base = sum(
            (detail.price * detail.quantity for detail in self.details.all()),
            Decimal('0.00'),
        )
        craft_amount = (base * self.craft_fee_rate / Decimal('100')).quantize(PRICE_QUANTIZE)
        subtotal = (base + craft_amount).quantize(PRICE_QUANTIZE)
        master_amount = (subtotal * self.master_fee_rate / Decimal('100')).quantize(PRICE_QUANTIZE)
        subtotal = (subtotal + master_amount).quantize(PRICE_QUANTIZE)
        owner_amount = (subtotal * self.owner_fee_rate / Decimal('100')).quantize(PRICE_QUANTIZE)
        total = (subtotal + owner_amount).quantize(PRICE_QUANTIZE)

        self.material_total = base.quantize(PRICE_QUANTIZE)
        self.craft_fee_amount = craft_amount
        self.master_fee_amount = master_amount
        self.owner_fee_amount = owner_amount
        self.total_price = total
        return self

class FurnitureDetail(models.Model):
    furniture = models.ForeignKey(
        Furniture,
        related_name='details',
        on_delete=models.CASCADE,
    )
    detail = models.ForeignKey(
        Detail,
        related_name='furniture_items',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )
    name = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
    )
    price = models.DecimalField(
        max_digits=20,
        decimal_places=0,
        validators=[MinValueValidator(0)],
        editable=False,
    )

    class Meta:
        ordering = ['detail__name']

    def __str__(self):
        name = self.detail.name if self.detail else self.name or 'Detal'
        return f"{name} · {self.price} * {self.quantity}"

    def save(self, *args, **kwargs):
        if self.detail_id:
            self.price = self.detail.price
            if not self.name:
                self.name = self.detail.name
        super().save(*args, **kwargs)
