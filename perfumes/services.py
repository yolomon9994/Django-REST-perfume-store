"""Checkout logic shared by the API and its tests."""

import logging
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import NotFound, ValidationError

from .models import Perfume

logger = logging.getLogger(__name__)


def purchase_perfumes(email, cart_items):
    """Deduct all items together, then attempt the confirmation email."""
    quantities = {item['id']: item['quantity'] for item in cart_items}
    summary = []
    total = Decimal('0.00')

    with transaction.atomic():
        # Consistent lock order avoids deadlocks between overlapping carts.
        perfumes = list(
            Perfume.objects.select_for_update().filter(pk__in=quantities).order_by('pk')
        )
        if len(perfumes) != len(quantities):
            raise NotFound('One or more perfumes were not found.')

        for perfume in perfumes:
            quantity = quantities[perfume.pk]
            if perfume.stock < quantity:
                raise ValidationError({'error': f'Not enough stock for {perfume.name}.'})

        for perfume in perfumes:
            quantity = quantities[perfume.pk]
            updated = Perfume.objects.filter(pk=perfume.pk, stock__gte=quantity).update(
                stock=F('stock') - quantity
            )
            if not updated:
                raise ValidationError({'error': f'Not enough stock for {perfume.name}.'})
            subtotal = perfume.price * quantity
            total += subtotal
            summary.append(
                f'{perfume.name} - {quantity} x ${perfume.price:.2f} = ${subtotal:.2f}'
            )

    # An email failure must not tell the browser to repeat a completed purchase.
    confirmation_sent = True
    try:
        sent = send_mail(
            'Your Perfume Order Confirmation',
            'Thank you for your purchase!\n\nOrder Summary:\n'
            + '\n'.join(summary)
            + f'\n\nTotal: ${total:.2f}\n\nThis is a practice order; no payment was taken.',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        confirmation_sent = sent == 1
    except Exception:
        # Avoid exposing SMTP credentials or provider details in API errors/logs.
        logger.warning('Checkout completed, but the confirmation email could not be sent.')
        confirmation_sent = False

    message = 'Order placed successfully! Confirmation sent to your email.'
    if not confirmation_sent:
        message = 'Order placed, but the confirmation email could not be sent.'
    return {'message': message, 'total': f'{total:.2f}', 'confirmation_sent': confirmation_sent}
