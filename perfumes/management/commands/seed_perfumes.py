"""Load the bundled sample catalog without replacing existing products."""

import json
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from perfumes.models import Perfume

SAMPLE_ROOT = Path(__file__).resolve().parents[2] / 'sample_data'


class Command(BaseCommand):
    help = 'Add the bundled sample perfumes and images; skip existing product names.'

    def handle(self, *args, **options):
        items = json.loads((SAMPLE_ROOT / 'perfumes.json').read_text(encoding='utf-8'))
        for item in items:
            if item.get('image') and not (SAMPLE_ROOT / 'images' / item['image']).is_file():
                raise CommandError(f"Missing sample image for {item['name']}.")

        added = 0
        skipped = 0
        with transaction.atomic():
            for item in items:
                perfume, created = Perfume.objects.get_or_create(
                    name=item['name'],
                    defaults={'price': item['price'], 'stock': item['stock']},
                )
                if not created:
                    skipped += 1
                    continue

                if item.get('image'):
                    # Keep original demo assets in Git, and copies in local media.
                    image_name = 'sample_perfumes/' + item['image']
                    storage = perfume.image.storage
                    if not storage.exists(image_name):
                        with (SAMPLE_ROOT / 'images' / item['image']).open('rb') as source:
                            image_name = storage.save(image_name, File(source))
                    perfume.image.name = image_name
                    perfume.save(update_fields=['image'])
                added += 1

        self.stdout.write(self.style.SUCCESS(
            f'Added {added} sample perfumes; skipped {skipped} existing perfumes.'
        ))
