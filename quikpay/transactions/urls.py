from django.urls import path
from .views import BalanceAPIView, DepositAPIView, TransactionHistoryAPIView, TransferAPIView

urlpatterns = [
    path('transfer/', TransferAPIView.as_view(), name='wallet-transfer'),
    path('deposit/', DepositAPIView.as_view(), name='wallet-deposit'),
    path('balance/', BalanceAPIView.as_view(), name='wallet-balance'),
    path('history/', TransactionHistoryAPIView.as_view(), name='wallet-history'),
]