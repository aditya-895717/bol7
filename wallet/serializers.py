from decimal import Decimal

from rest_framework import serializers

from .models import Transaction, Wallet


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ("balance", "updated_at")
        read_only_fields = fields


class AmountSerializer(serializers.Serializer):
    """Shared validation for deposit/withdraw request bodies."""

    amount = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_amount(self, value):
        if value <= Decimal("0.00"):
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ("reference", "type", "amount", "balance_after", "created_at")
        read_only_fields = fields
