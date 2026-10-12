from django.contrib import admin
from django.contrib.admin.views.main import ChangeList
from decimal import Decimal, InvalidOperation

from .forms import PerfumeForm
from .models import Perfume


class PriceRangeChangeList(ChangeList):
    def get_filters_params(self, params=None):
        # These are custom controls, not model field lookups.
        filters = super().get_filters_params(params)
        filters.pop('price_min', None)
        filters.pop('price_max', None)
        return filters


class PerfumeAdmin(admin.ModelAdmin):
    form = PerfumeForm
    list_display = ('name', 'price', 'stock')
    search_fields = ('name',)
    list_editable = ('stock',)
    ordering = ['-price']
    fields = ('name', 'price', 'stock', 'image')
    
    change_list_template = "admin/perfumes/perfume/change_list.html"

    def get_changelist(self, request, **kwargs):
        return PriceRangeChangeList

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['price_min'] = request.GET.get('price_min', '')
        extra_context['price_max'] = request.GET.get('price_max', '')
        extra_context['price_filter_parameters'] = [
            (key, value)
            for key, values in request.GET.lists()
            if key not in {'price_min', 'price_max', 'p', 'e'}
            for value in values
        ]
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        price_min = request.GET.get('price_min', '').strip()
        price_max = request.GET.get('price_max', '').strip()

        if price_min:
            try:
                price_min_decimal = Decimal(price_min)
                if price_min_decimal.is_finite() and 0 <= price_min_decimal <= Decimal('999999.99'):
                    qs = qs.filter(price__gte=price_min_decimal)
            except (InvalidOperation, ValueError):
                pass

        if price_max:
            try:
                price_max_decimal = Decimal(price_max)
                if price_max_decimal.is_finite() and 0 <= price_max_decimal <= Decimal('999999.99'):
                    qs = qs.filter(price__lte=price_max_decimal)
            except (InvalidOperation, ValueError):
                pass

        return qs


admin.site.register(Perfume, PerfumeAdmin)
