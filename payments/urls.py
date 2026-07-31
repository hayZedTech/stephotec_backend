from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, SchoolBankAccountViewSet

payment_router = DefaultRouter()
payment_router.register(r"", PaymentViewSet, basename="payment")

bank_router = DefaultRouter()
bank_router.register(r"", SchoolBankAccountViewSet, basename="bank-account")

urlpatterns = [
    path("bank-accounts/", include(bank_router.urls)),
    path("", include(payment_router.urls)),
]
