from django.test import TestCase
from django.urls import reverse

from .forms import FurnitureDetailForm, FurnitureForm
from .models import Furniture, FurnitureDetail


class FurnitureEditTests(TestCase):
    def setUp(self):
        self.furniture = Furniture.objects.create(name='Shkaf', craft_fee_rate=2, master_fee_rate=5, owner_fee_rate=10)
        self.detail = FurnitureDetail.objects.create(furniture=self.furniture, name='Panel', price=100000, quantity=2)

    def test_edit_page_renders_hidden_formset_ids(self):
        response = self.client.get(reverse('furniture_edit', args=[self.furniture.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="details-0-id"')

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
                'details-0-name': 'Panel',
                'details-0-price': '150000',
                'details-0-quantity': '2',
                'details-0-DELETE': '',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.furniture.refresh_from_db()
        self.detail.refresh_from_db()
        self.assertEqual(self.furniture.name, 'Yangi shkaf')
        self.assertEqual(self.detail.price, 150000)

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

        detail_form = FurnitureDetailForm(data={
            'name': 'Panel',
            'price': '150000.5',
            'quantity': '2',
        })
        self.assertFalse(detail_form.is_valid())
        self.assertIn('price', detail_form.errors)
