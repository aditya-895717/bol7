from django.urls import path

from .views import BalanceView, DepositView, TransactionHistoryView, WithdrawView

urlpatterns = [
    path("balance/", BalanceView.as_view(), name="wallet-balance"),
    path("deposit/", DepositView.as_view(), name="wallet-deposit"),
    path("withdraw/", WithdrawView.as_view(), name="wallet-withdraw"),
    path("transactions/", TransactionHistoryView.as_view(), name="wallet-transactions"),
]
