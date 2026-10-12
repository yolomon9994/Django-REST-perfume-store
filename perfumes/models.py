from django.db import models

class Perfume(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    stock = models.PositiveIntegerField()
    image = models.ImageField(upload_to='perfume_images/', null=True, blank=True)

    def __str__(self):
        return self.name
