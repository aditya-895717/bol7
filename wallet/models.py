import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wallet"
    )
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s wallet (${self.balance})"


class Transaction(models.Model):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    TYPE_CHOICES = [
        (DEPOSIT, "Deposit"),
        (WITHDRAWAL, "Withdrawal"),
    ]

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name="transactions")
    reference = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.type} {self.amount} ({self.wallet.user.username})"
