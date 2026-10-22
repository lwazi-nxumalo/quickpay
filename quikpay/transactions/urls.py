from django.urls import path
from .views import DepositAPIView, TransferAPIView

urlpatterns = [
    path('api/transfer/', TransferAPIView.as_view(), name='api-transfer'),
    path('api/deposit/', DepositAPIView.as_view(), name='api-deposit'),
]