"""Store pages, account views, and authenticated checkout endpoints."""

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import PerfumeForm, RegistrationForm
from .models import Perfume
from .serializers import PurchaseSerializer, StockRequestSerializer
from .services import purchase_perfumes


def home_view(request):
    return render(request, 'home.html')


@login_required
@ensure_csrf_cookie
def store_view(request):
    perfumes = Perfume.objects.all().order_by('name', 'pk')
    query = request.GET.get('q', '').strip()
    if query:
        perfumes = perfumes.filter(name__icontains=query)
    if request.GET.get('in_stock') == '1':
        perfumes = perfumes.filter(stock__gt=0)
    ordering = {'price_low': 'price', 'price_high': '-price', 'name': 'name'}
    sort = request.GET.get('sort')
    if sort in ordering:
        perfumes = perfumes.order_by(ordering[sort], 'pk')
    return render(request, 'store.html', {'perfumes': perfumes})


@staff_member_required
@require_http_methods(['GET', 'POST'])
def add_perfume_view(request):
    form = PerfumeForm(
        request.POST if request.method == 'POST' else None,
        request.FILES if request.method == 'POST' else None,
    )
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Perfume added successfully!')
            return redirect('store_view')
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'add_perfume.html', {'form': form})


@require_http_methods(['GET', 'POST'])
def register_view(request):
    form = RegistrationForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
        messages.error(request, 'Please correct the errors below.')
    return render(request, 'register.html', {'form': form})


@api_view(['POST'])
def purchase_perfume_api(request):
    serializer = PurchaseSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    return Response(purchase_perfumes(
        email=serializer.validated_data['email'],
        cart_items=serializer.validated_data['cart'],
    ))


class PerfumeStockView(APIView):
    def post(self, request):
        serializer = StockRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        perfume = get_object_or_404(Perfume, pk=serializer.validated_data['id'])
        return Response({'stock': perfume.stock})


class LoginWithMessageView(LoginView):
    template_name = 'login.html'

    def form_valid(self, form):
        messages.success(self.request, 'Login successful!')
        return super().form_valid(form)


class LogoutWithMessageView(LogoutView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.success(request, 'Logged out successfully!')
        return response
