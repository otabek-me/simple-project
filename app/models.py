from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP

CENTS = Decimal('0.01')

def to_money(value):
    """Pul summalarini har doim izchil qoidada (0.5 -> yuqoriga) 2 xonaga yaxlitlaydi."""
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


class Client(models.Model):
    name = models.CharField(max_length=200, verbose_name="Ism")
    phone = models.CharField(max_length=30, blank=True, null=True, verbose_name="Telefon")
    address = models.TextField(blank=True, null=True, verbose_name="Manzil")
    notes = models.TextField(blank=True, null=True, verbose_name="Izoh")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan vaqt")

    class Meta:
        ordering = ['name']
        verbose_name = "Klient"
        verbose_name_plural = "Klinetlar"

    def __str__(self):
        return self.name

    def total_purchases(self):
        return self.sales.filter(status='active').aggregate(total=models.Sum('total_amount'))['total'] or Decimal('0')

    def total_paid(self):
        return self.sales.filter(status='active').aggregate(total=models.Sum('paid_amount'))['total'] or Decimal('0')

    def total_debt(self):
        return self.total_purchases() - self.total_paid()


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
    quantity = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0)],
        verbose_name="Zahiradagi soni",
    )
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

    def add_quantity(self, amount):
        """Zahiraga qo'shish (qaytarib olinganda)."""
        self.quantity = self.quantity + amount
        self.save(update_fields=['quantity'])
        return self

    def reduce_quantity(self, amount):
        """Zahiradan kamaytirish (sotilganda)."""
        self.quantity = self.quantity - amount
        self.save(update_fields=['quantity'])
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

    @property
    def tannarx(self):
        """Birlik tannarxi (material + detal ustama + usta haqi).

        Sotish narxidan egasining foydasi (owner_fee_amount) ayrib
        tashlanganda ham aynan shu qiymat hosil bo'ladi.
        """
        return to_money(
            self.material_total
            + self.craft_fee_amount
            + self.master_fee_amount
        )


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


class Sale(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'Naqt'),
        ('credit', 'Nasiya'),
    ]
    STATUS_CHOICES = [
        ('active', 'Faol'),
        ('cancelled', 'Bekor qilingan'),
    ]

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Holat",
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Bekor qilingan vaqt",
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cancelled_sales',
        verbose_name="Kim bekor qilgan",
    )

    client = models.ForeignKey(
        Client,
        related_name='sales',
        on_delete=models.CASCADE,
        verbose_name="Klient",
    )
    payment_type = models.CharField(
        max_length=10,
        choices=PAYMENT_CHOICES,
        verbose_name="To'lov turi",
    )
    total_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name="Jami summa",
    )
    paid_amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name="To'langan summa",
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Izoh")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Kim qo'shgan",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Sotilgan vaqt")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Sotuv"
        verbose_name_plural = "Sotuvlar"

    def __str__(self):
        return f"{self.client.name} — {self.total_amount} ({self.get_payment_type_display()})"

    def debt_amount(self):
        return self.total_amount - self.paid_amount

    def total_cost(self):
        """Sotuv bo'yicha umumiy tannarx (barcha qatorlar)."""
        return sum((item.cost_subtotal for item in self.items.all()), Decimal('0'))

    def profit_total(self):
        """Sotuv bo'yicha sof foyda (jami summa − umumiy tannarx)."""
        return to_money(self.total_amount - self.total_cost())

    def save(self, *args, **kwargs):
        if self.payment_type == 'cash':
            self.paid_amount = self.total_amount
        super().save(*args, **kwargs)

    def cancel(self, user=None):
        """Sotuvni bekor qiladi va mebellarni zahiraga qaytaradi."""
        if self.status == 'cancelled':
            return self
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancelled_by = user
        self.save()
        # Mebellarni zahiraga qaytarish
        for item in self.items.all():
            if item.furniture:
                item.furniture.add_quantity(item.quantity)
        return self


class SaleItem(models.Model):
    sale = models.ForeignKey(
        Sale,
        related_name='items',
        on_delete=models.CASCADE,
        verbose_name="Sotuv",
    )
    furniture = models.ForeignKey(
        Furniture,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Mebel",
    )
    furniture_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Mebel nomi (saqlangan)",
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Soni",
    )
    price_at_sale = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        verbose_name="Sotish narxi",
    )
    subtotal = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name="Summa",
    )
    cost_at_sale = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0,
        verbose_name="Birlik tannarxi",
    )

    class Meta:
        ordering = ['id']
        verbose_name = "Sotuv mahsuloti"
        verbose_name_plural = "Sotuv mahsulotlari"

    @property
    def display_name(self):
        """Mebel nomini xavfsiz ko'rsatadi.

        furniture_name (saqlangan snapshot) afzal; agar bo'lmasa joriy
        furniture.name; agar mebel o'chirilgan bo'lsa 'Noma'lum'.
        Bu xossa shablonlarda `item.furniture_name|default:item.furniture.name`
        kabi eager-baholanadigan qarama-qarshi naqsh o'rniga ishlatiladi —
        aks holda furniture=None bo'lganda VariableDoesNotExist chiqadi.
        """
        if self.furniture_name:
            return self.furniture_name
        if self.furniture:
            return self.furniture.name
        return 'Noma\'lum'

    def __str__(self):
        return f"{self.display_name} × {self.quantity} = {self.subtotal}"

    @property
    def cost_subtotal(self):
        """Ushbu qatorning umumiy tannarxi (birlik tannarxi × soni)."""
        return to_money(self.cost_at_sale * self.quantity)

    @property
    def profit_subtotal(self):
        """Ushbu qatorning sof foydasi (summa − tannarx)."""
        return to_money(self.subtotal - self.cost_subtotal)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if self.furniture:
            self.furniture_name = self.furniture.name
            if not self.price_at_sale:
                self.price_at_sale = self.furniture.total_price
            if not self.cost_at_sale:
                self.cost_at_sale = self.furniture.tannarx
        self.subtotal = to_money(self.price_at_sale * self.quantity)
        super().save(*args, **kwargs)
        # Yangi sotuv elementi qo'shilganda mebel zahiradan kamayadi
        if is_new and self.furniture and self.sale.status == 'active':
            self.furniture.reduce_quantity(self.quantity)


class Payment(models.Model):
    sale = models.ForeignKey(
        Sale,
        related_name='payments',
        on_delete=models.CASCADE,
        verbose_name="Sotuv",
    )
    amount = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Summa",
    )
    notes = models.TextField(blank=True, null=True, verbose_name="Izoh")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="To'lov vaqti")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "To'lov"
        verbose_name_plural = "To'lovlar"

    def __str__(self):
        return f"{self.sale.client.name} — {self.amount}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update sale paid_amount
        sale = self.sale
        total_paid = sale.payments.aggregate(total=models.Sum('amount'))['total'] or Decimal('0')
        Sale.objects.filter(pk=sale.pk).update(paid_amount=total_paid)