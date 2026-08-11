from django.db import transaction as db_transaction
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Transaction, Wallet
from .serializers import AmountSerializer, TransactionSerializer, WalletSerializer


class BalanceView(generics.RetrieveAPIView):
    """GET /api/wallet/balance/ - authenticated user's current balance."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WalletSerializer

    def get_object(self):
        wallet, _ = Wallet.objects.get_or_create(user=self.request.user)
        return wallet


class DepositView(APIView):
    """POST /api/wallet/deposit/  { "amount": "100.00" }"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AmountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]

        with db_transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=request.user)
            wallet.balance += amount
            wallet.save(update_fields=["balance", "updated_at"])
            txn = Transaction.objects.create(
                wallet=wallet,
                type=Transaction.DEPOSIT,
                amount=amount,
                balance_after=wallet.balance,
            )

        return Response(
            {
                "message": "Deposit successful.",
                "balance": wallet.balance,
                "transaction": TransactionSerializer(txn).data,
            },
            status=status.HTTP_201_CREATED,
        )


class WithdrawView(APIView):
    """POST /api/wallet/withdraw/  { "amount": "50.00" }"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = AmountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]

        with db_transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(user=request.user)
            if amount > wallet.balance:
                return Response(
                    {"detail": "Insufficient funds."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            wallet.balance -= amount
            wallet.save(update_fields=["balance", "updated_at"])
            txn = Transaction.objects.create(
                wallet=wallet,
                type=Transaction.WITHDRAWAL,
                amount=amount,
                balance_after=wallet.balance,
            )

        return Response(
            {
                "message": "Withdrawal successful.",
                "balance": wallet.balance,
                "transaction": TransactionSerializer(txn).data,
            },
            status=status.HTTP_201_CREATED,
        )


class TransactionHistoryView(generics.ListAPIView):
    """GET /api/wallet/transactions/?type=DEPOSIT&start_date=&end_date=

    Paginated, newest first, scoped strictly to the authenticated user.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        qs = Transaction.objects.filter(wallet__user=self.request.user)

        txn_type = self.request.query_params.get("type")
        if txn_type:
            qs = qs.filter(type=txn_type.upper())

        start_date = self.request.query_params.get("start_date")
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)

        end_date = self.request.query_params.get("end_date")
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)

        return qs
