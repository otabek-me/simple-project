from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal, ROUND_HALF_UP

CENTS = Decimal('0.01')

def to_money(value):
    """Pul summalarini har doim izchil qoidada (0.5 -> yuqoriga) 2 xonaga yaxlitlaydi."""
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)

class Detail(models.Model):
    name = models.CharField(max_length=120)
    price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} — {self.price}"

    def save(self, *args, **kwargs):
        old_price = None
        if self.pk:
            try:
                old_price = Detail.objects.get(pk=self.pk).price
            except Detail.DoesNotExist:
                pass
        super().save(*args, **kwargs)
        if old_price is not None and old_price != self.price:
            affected_furniture_ids = set()
            for fd in FurnitureDetail.objects.filter(detail=self):
                fd.price = self.price
                fd.save(update_fields=['price'])
                affected_furniture_ids.add(fd.furniture_id)
            for fid in affected_furniture_ids:
                try:
                    f = Furniture.objects.get(pk=fid)
                    f.recalculate().save()
                except Furniture.DoesNotExist:
                    pass


class Furniture(models.Model):
    name = models.CharField(max_length=120)
    craft_fee_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=2,
        validators=[MinValueValidator(0)],
    )
    master_fee_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=5,
        validators=[MinValueValidator(0)],
    )
    owner_fee_rate = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=10,
        validators=[MinValueValidator(0)],
    )
    material_total = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        editable=False,
    )
    craft_fee_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        editable=False,
    )
    master_fee_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        editable=False,
    )
    owner_fee_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        editable=False,
    )
    total_price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        editable=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', '-created_at']

    def __str__(self):
        return self.name

    def sync_detail_prices(self):
        """Har bir qatordagi narxni joriy Detail narxiga sinxronlaydi.

        Forma/ro'yxatda ko'rinadigan detal narxi bilan material yig'indisi
        o'rtasida farq chiqmasligi uchun hisobdan oldin chaqiriladi.
        """
        to_update = []
        for fd in self.details.select_related('detail').all():
            if not fd.detail_id or fd.detail is None:
                continue
            new_price = fd.detail.price
            new_name = fd.detail.name
            if fd.price != new_price or fd.name != new_name:
                fd.price = new_price
                fd.name = new_name
                to_update.append(fd)
        if to_update:
            FurnitureDetail.objects.bulk_update(to_update, ['price', 'name'])
        return self

    def recalculate(self):
        # Avval snapshot narxlarni joriy Detail narxlari bilan moslashtiramiz.
        # Aks holda forma dropdownida yangi narx ko'rinadi, material_total esa
        # eski FurnitureDetail.price bo'yicha qolib, farq chiqadi (masalan 2100).
        self.sync_detail_prices()

        base = Decimal('0.00')
        for fd in self.details.select_related('detail').all():
            unit_price = fd.detail.price if fd.detail_id and fd.detail is not None else fd.price
            base += unit_price * fd.quantity

        craft_amount = base * self.craft_fee_rate / Decimal('100')
        subtotal = base + craft_amount
        master_amount = subtotal * self.master_fee_rate / Decimal('100')
        subtotal = subtotal + master_amount
        owner_amount = subtotal * self.owner_fee_rate / Decimal('100')
        total = subtotal + owner_amount

        # Django DecimalField saqlashda rounding ko'rsatilmasa ROUND_HALF_EVEN
        # (bankir yaxlitlashi) ishlatadi — bu 0.5 chegarasidagi summalarni
        # kutilmagan tomonga yaxlitlab, "bir xil narxlar turlicha yaxlitlanadi"
        # degan taassurot uyg'otadi. Shu sabab bu yerda har bir maydonni
        # aniq ROUND_HALF_UP bilan o'zimiz yaxlitlaymiz.
        self.material_total = to_money(base)
        self.craft_fee_amount = to_money(craft_amount)
        self.master_fee_amount = to_money(master_amount)
        self.owner_fee_amount = to_money(owner_amount)
        self.total_price = to_money(total)
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
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    name = models.CharField(
        max_length=120,
        blank=True,
        null=True,
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    price = models.DecimalField(
        max_digits=20,
        decimal_places=2,
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
            # Har doim joriy Detail dan oling — eski snapshot qolmasin
            detail = self.detail
            if detail is not None:
                self.price = detail.price
                self.name = detail.name
        super().save(*args, **kwargs)


