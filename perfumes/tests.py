from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.db.models.query import QuerySet
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from .models import Perfume


class StoreTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('shopper', password='test-account-password')
        cls.staff = User.objects.create_superuser('admin', password='test-admin-password')
        cls.rose = Perfume.objects.create(name='Rose', price='20.50', stock=5)
        cls.wood = Perfume.objects.create(name='Wood', price='10.00', stock=2)
        cls.empty = Perfume.objects.create(name='Empty', price='5.00', stock=0)

    def test_home_is_public(self):
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)

    def test_store_requires_login(self):
        response = self.client.get(reverse('store_view'))
        self.assertRedirects(response, '/login/?next=/products/')

    def test_store_search_filter_and_sort(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('store_view'), {'in_stock': '1', 'sort': 'price_low'})
        self.assertEqual(list(response.context['perfumes']), [self.wood, self.rose])
        response = self.client.get(reverse('store_view'), {'q': 'ros'})
        self.assertEqual(list(response.context['perfumes']), [self.rose])

    def test_regular_user_cannot_add_products(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('add_perfume'), {'name': 'Unauthorized', 'price': 1, 'stock': 1})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Perfume.objects.filter(name='Unauthorized').exists())

    def test_staff_can_add_products(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('add_perfume'), {'name': 'New', 'price': '3.50', 'stock': 1})
        self.assertRedirects(response, reverse('store_view'))
        self.assertTrue(Perfume.objects.filter(name='New', price=Decimal('3.50')).exists())

    def test_negative_price_is_rejected(self):
        self.client.force_login(self.staff)
        response = self.client.post(reverse('add_perfume'), {'name': 'Invalid', 'price': '-1', 'stock': 1})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Price cannot be negative.')
        self.assertFalse(Perfume.objects.filter(name='Invalid').exists())

    def test_registration_logs_in_without_granting_staff(self):
        response = self.client.post(reverse('register'), {
            'username': 'new-shopper', 'password1': 'Practice!Pass-2026', 'password2': 'Practice!Pass-2026',
        })
        self.assertRedirects(response, reverse('home'))
        user = User.objects.get(username='new-shopper')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('Practice!Pass-2026'))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_duplicate_username_and_weak_password_show_errors(self):
        for data in [
            {'username': 'shopper', 'password1': 'Practice!Pass-2026', 'password2': 'Practice!Pass-2026'},
            {'username': 'weak', 'password1': '123', 'password2': '123'},
        ]:
            with self.subTest(username=data['username']):
                response = self.client.post(reverse('register'), data)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context['form'].errors)
        self.assertFalse(User.objects.filter(username='weak').exists())

    def test_login_preserves_next_and_redirects(self):
        response = self.client.get('/login/?next=/products/')
        self.assertContains(response, 'name="next" value="/products/"')
        response = self.client.post(reverse('login'), {
            'username': 'shopper', 'password': 'test-account-password', 'next': '/products/',
        })
        self.assertRedirects(response, reverse('store_view'))

    def test_logout_requires_post_and_clears_session(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_admin_price_filter_and_search_work_together(self):
        self.client.force_login(self.staff)
        response = self.client.get(reverse('admin:perfumes_perfume_changelist'), {
            'price_min': '15', 'price_max': '25', 'q': 'Rose',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context['cl'].result_list), [self.rose])
        self.assertContains(response, 'name="q" value="Rose"')

    def test_admin_ignores_invalid_price_values(self):
        self.client.force_login(self.staff)
        for value in ['NaN', 'Infinity', 'not-a-number', '1e100000', '-5']:
            with self.subTest(value=value):
                response = self.client.get(reverse('admin:perfumes_perfume_changelist'), {'price_min': value})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(len(response.context['cl'].result_list), 3)


class PurchaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('shopper', password='test-account-password')
        cls.rose = Perfume.objects.create(name='Rose', price='20.50', stock=5)
        cls.wood = Perfume.objects.create(name='Wood', price='10.00', stock=2)

    def setUp(self):
        self.client = APIClient()
        self.client.force_login(self.user)

    def buy(self, items, email='buyer@example.com'):
        return self.client.post(reverse('purchase_perfume_api'), {'email': email, 'cart': items}, format='json')

    def test_valid_purchase_updates_stock_and_sends_summary(self):
        response = self.buy([{'id': self.rose.pk, 'quantity': 2}, {'id': self.wood.pk, 'quantity': 1}])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['total'], '51.00')
        self.assertTrue(response.data['confirmation_sent'])
        self.rose.refresh_from_db()
        self.wood.refresh_from_db()
        self.assertEqual((self.rose.stock, self.wood.stock), (3, 1))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Total: $51.00', mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ['buyer@example.com'])

    def test_invalid_quantities_leave_stock_unchanged(self):
        for quantity in [0, -2, 1.5, 'bad', 2147483648]:
            with self.subTest(quantity=quantity):
                self.assertEqual(self.buy([{'id': self.rose.pk, 'quantity': quantity}]).status_code, 400)
        self.rose.refresh_from_db()
        self.assertEqual(self.rose.stock, 5)
        self.assertEqual(len(mail.outbox), 0)

    def test_empty_cart_invalid_email_and_duplicate_ids_are_rejected(self):
        self.assertEqual(self.buy([]).status_code, 400)
        item = {'id': self.rose.pk, 'quantity': 1}
        self.assertEqual(self.buy([item], email='bad-email').status_code, 400)
        self.assertEqual(self.buy([item, item]).status_code, 400)
        self.rose.refresh_from_db()
        self.assertEqual(self.rose.stock, 5)

    def test_insufficient_stock_leaves_entire_cart_unchanged(self):
        response = self.buy([{'id': self.rose.pk, 'quantity': 1}, {'id': self.wood.pk, 'quantity': 3}])
        self.assertEqual(response.status_code, 400)
        self.rose.refresh_from_db()
        self.wood.refresh_from_db()
        self.assertEqual((self.rose.stock, self.wood.stock), (5, 2))
        self.assertEqual(len(mail.outbox), 0)

    def test_missing_product_leaves_stock_unchanged(self):
        response = self.buy([{'id': self.rose.pk, 'quantity': 1}, {'id': 999999, 'quantity': 1}])
        self.assertEqual(response.status_code, 404)
        self.rose.refresh_from_db()
        self.assertEqual(self.rose.stock, 5)

    def test_failed_second_stock_update_rolls_back_first_update(self):
        original_update = QuerySet.update
        calls = 0

        def update(queryset, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                return 0
            return original_update(queryset, **kwargs)

        with patch.object(QuerySet, 'update', autospec=True, side_effect=update):
            response = self.buy([{'id': self.rose.pk, 'quantity': 1}, {'id': self.wood.pk, 'quantity': 1}])
        self.assertEqual(response.status_code, 400)
        self.rose.refresh_from_db()
        self.wood.refresh_from_db()
        self.assertEqual((self.rose.stock, self.wood.stock), (5, 2))
        self.assertEqual(len(mail.outbox), 0)

    def test_email_failure_reports_completed_purchase_without_leaking_error(self):
        with patch('perfumes.services.send_mail', side_effect=RuntimeError('private SMTP detail')):
            response = self.buy([{'id': self.rose.pk, 'quantity': 1}])
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['confirmation_sent'])
        self.assertNotIn('private SMTP detail', str(response.data))
        self.rose.refresh_from_db()
        self.assertEqual(self.rose.stock, 4)

    def test_anonymous_apis_return_json_without_redirecting(self):
        self.client.logout()
        for url, data in [
            (reverse('purchase_perfume_api'), {'email': 'buyer@example.com', 'cart': []}),
            (reverse('perfume_stock_api'), {'id': self.rose.pk}),
        ]:
            with self.subTest(url=url):
                response = self.client.post(url, data, format='json')
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response['Content-Type'], 'application/json')

    def test_stock_api_validates_id(self):
        url = reverse('perfume_stock_api')
        self.assertEqual(self.client.post(url, {'id': self.rose.pk}, format='json').data, {'stock': 5})
        for data in [{}, {'id': 'bad'}, {'id': -1}, {'id': 9223372036854775808}]:
            with self.subTest(data=data):
                self.assertEqual(self.client.post(url, data, format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {'id': 999999}, format='json').status_code, 404)

    def test_checkout_requires_csrf_for_authenticated_session(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.user)
        payload = {'email': 'buyer@example.com', 'cart': [{'id': self.rose.pk, 'quantity': 1}]}
        url = reverse('purchase_perfume_api')
        self.assertEqual(client.post(url, payload, format='json').status_code, 403)
        response = client.get(reverse('store_view'))
        self.assertEqual(response.status_code, 200)
        token = client.cookies['csrftoken'].value
        self.assertEqual(client.post(url, payload, format='json', HTTP_X_CSRFTOKEN=token).status_code, 200)
