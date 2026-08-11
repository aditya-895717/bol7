from django.contrib import admin

from .models import Transaction, Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance", "updated_at")
    readonly_fields = ("balance",)
    search_fields = ("user__username", "user__email")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("reference", "wallet", "type", "amount", "balance_after", "created_at")
    list_filter = ("type",)
    readonly_fields = [f.name for f in Transaction._meta.fields]
    search_fields = ("wallet__user__username", "reference")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
