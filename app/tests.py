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
