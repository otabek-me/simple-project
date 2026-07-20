from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import DetailForm, FurnitureDetailForm, FurnitureForm
from .models import Detail, Furniture, FurnitureDetail


class FurnitureEditTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username='admin', password='password')
        self.client.force_login(self.user)
        self.furniture = Furniture.objects.create(name='Shkaf', craft_fee_rate=2, master_fee_rate=5, owner_fee_rate=10)
        self.detail_template = Detail.objects.create(name='Panel', price=100000)
        self.detail = FurnitureDetail.objects.create(furniture=self.furniture, detail=self.detail_template, quantity=2)

    def test_login_required_for_list(self):
        self.client.logout()
        response = self.client.get(reverse('furniture_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])

    def test_login_page_supports_password_change(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Parolni almashtirish')

        response = self.client.post(reverse('login'), {
            'old_password': 'password',
            'new_password1': 'NewStrong123!',
            'new_password2': 'NewStrong123!',
            'password_submit': '1',
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], reverse('furniture_list'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewStrong123!'))

    def test_password_change_displays_uzbek_error_messages(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('login'), {
            'old_password': 'wrong-password',
            'new_password1': 'abc123',
            'new_password2': 'abc123',
            'password_submit': '1',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Eski parol noto‘g‘ri')

    def test_edit_page_renders_hidden_formset_ids(self):
        response = self.client.get(reverse('furniture_edit', args=[self.furniture.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="details-0-id"')
        self.assertNotContains(response, 'name="details-1-detail"')

    def test_create_page_does_not_render_initial_empty_detail_form(self):
        response = self.client.get(reverse('furniture_create'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="details-0-detail"')
        self.assertContains(response, 'id="add-detail-row"')

    def test_editing_furniture_saves_changes(self):
        response = self.client.post(
            reverse('furniture_edit', args=[self.furniture.pk]),
            {
                'name': 'Yangi shkaf',
                'craft_fee_rate': '2',
                'master_fee_rate': '5',
                'owner_fee_rate': '10',
                'details-TOTAL_FORMS': '1',
                'details-INITIAL_FORMS': '1',
                'details-MIN_NUM_FORMS': '0',
                'details-MAX_NUM_FORMS': '1000',
                'details-0-id': str(self.detail.pk),
                'details-0-detail': str(self.detail_template.pk),
                'details-0-quantity': '3',
                'details-0-DELETE': '',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.furniture.refresh_from_db()
        self.detail.refresh_from_db()
        self.assertEqual(self.furniture.name, 'Yangi shkaf')
        self.assertEqual(self.detail.quantity, 3)
        self.assertEqual(self.detail.price, 100000)

    def test_delete_furniture_removes_record_and_redirects(self):
        response = self.client.post(reverse('furniture_delete', args=[self.furniture.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Furniture.objects.filter(pk=self.furniture.pk).exists())

    def test_money_and_percent_fields_require_whole_numbers_and_limit_digits(self):
        form = FurnitureForm(data={
            'name': 'Shkaf',
            'craft_fee_rate': '2.5',
            'master_fee_rate': '100000000',
            'owner_fee_rate': '10',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('craft_fee_rate', form.errors)
        self.assertIn('master_fee_rate', form.errors)

        detail_form = DetailForm(data={
            'name': 'Panel',
            'price': '150000.5',
        })
        self.assertFalse(detail_form.is_valid())
        self.assertIn('price', detail_form.errors)


class MaterialTotalSyncTests(TestCase):
    """Material yig'indisi forma/dropdowndagi joriy detal narxlari bilan mos bo'lishi kerak."""

    def setUp(self):
        from decimal import Decimal
        self.Decimal = Decimal
        self.furniture = Furniture.objects.create(
            name='170lik Kupe',
            craft_fee_rate=2,
            master_fee_rate=6,
            owner_fee_rate=24,
        )
        self.kromka = Detail.objects.create(name='Kromka (19×04)', price=Decimal('2200'))
        self.ruchka = Detail.objects.create(name='Ruchka #300', price=Decimal('1700'))
        FurnitureDetail.objects.create(
            furniture=self.furniture,
            detail=self.kromka,
            quantity=Decimal('29.00'),
        )
        FurnitureDetail.objects.create(
            furniture=self.furniture,
            detail=self.ruchka,
            quantity=Decimal('1.00'),
        )
        self.furniture.recalculate().save()

    def test_material_total_matches_current_detail_prices(self):
        from decimal import Decimal
        expected = Decimal('2200') * Decimal('29') + Decimal('1700') * Decimal('1')
        self.furniture.refresh_from_db()
        self.assertEqual(self.furniture.material_total, expected)

    def test_stale_snapshot_price_is_fixed_on_recalculate(self):
        """Agar FurnitureDetail.price eski qolgan bo'lsa, recalculate joriy Detail narxini oladi."""
        from decimal import Decimal
        fd = self.furniture.details.get(detail=self.kromka)
        # Snapshotni sun'iy ravishda eskirish (masalan eski 2100 farq)
        FurnitureDetail.objects.filter(pk=fd.pk).update(price=Decimal('2100'))
        fd.refresh_from_db()
        self.assertEqual(fd.price, Decimal('2100'))

        self.furniture.recalculate().save()
        fd.refresh_from_db()
        self.furniture.refresh_from_db()

        self.assertEqual(fd.price, Decimal('2200'))
        expected = Decimal('2200') * Decimal('29') + Decimal('1700') * Decimal('1')
        self.assertEqual(self.furniture.material_total, expected)

    def test_detail_price_change_updates_furniture_total(self):
        from decimal import Decimal
        self.kromka.price = Decimal('2300')
        self.kromka.save()
        self.furniture.refresh_from_db()
        expected = Decimal('2300') * Decimal('29') + Decimal('1700') * Decimal('1')
        self.assertEqual(self.furniture.material_total, expected)

    def test_kupe_full_material_sum(self):
        """Foydalanuvchi hisoblagan 1 358 700 bilan bir xil bo'lishi kerak."""
        from decimal import Decimal
        FurnitureDetail.objects.all().delete()
        items = [
            ('Faton 2lik', '5000', '4.00'),
            ('Germetik Akfix', '30000', '0.50'),
            ('Kardon Algarit', '90000', '0.80'),
            ('Kromka (19×04)', '2200', '29.00'),
            ('Laminat', '330000', '2.20'),
            ('Lipichka', '2000', '4.00'),
            ('Metan', '5700', '5.00'),
            ('Oyna Farset', '100000', '0.90'),
            ('Oyna Farset Metr', '5000', '4.10'),
            ('Petle ITVP', '2500', '2.00'),
            ('Qosh', '40000', '1.00'),
            ('Reles 2metrli', '75000', '1.00'),
            ('Rolik BBS', '24000', '3.00'),
            ('Ruchka #300', '1700', '1.00'),
            ('Ruchka (35 157)', '2800', '2.00'),
            ('Ruchka Alumen 2metrlik', '33000', '2.00'),
            ('Salaska Ximenyupin 35lik', '12000', '2.00'),
            ('Taqa Qovun', '1400', '4.00'),
            ('Turba Qovun', '30000', '0.50'),
            ('Zamok Drawer Lock', '5000', '1.00'),
        ]
        for name, price, qty in items:
            d = Detail.objects.create(name=name, price=Decimal(price))
            FurnitureDetail.objects.create(
                furniture=self.furniture,
                detail=d,
                quantity=Decimal(qty),
            )
        self.furniture.recalculate().save()
        self.furniture.refresh_from_db()
        self.assertEqual(self.furniture.material_total, Decimal('1358700.00'))

