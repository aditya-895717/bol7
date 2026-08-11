from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status


class RegistrationTests(APITestCase):
    def test_register_success(self):
        resp = self.client.post("/api/auth/register/", {
            "username": "alice",
            "email": "alice@example.com",
            "password": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="alice").exists())

    def test_register_duplicate_username(self):
        User.objects.create_user(username="alice", email="a@example.com", password="pw12345678")
        resp = self.client.post("/api/auth/register/", {
            "username": "alice",
            "email": "other@example.com",
            "password": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_password_mismatch(self):
        resp = self.client.post("/api/auth/register/", {
            "username": "bob",
            "email": "bob@example.com",
            "password": "StrongPass123!",
            "password2": "Different123!",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class AuthenticatedWalletTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice", email="alice@example.com", password="StrongPass123!"
        )
        resp = self.client.post("/api/auth/login/", {
            "username": "alice", "password": "StrongPass123!",
        })
        self.access = resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access}")


class LoginTests(APITestCase):
    def setUp(self):
        User.objects.create_user(username="alice", email="a@example.com", password="StrongPass123!")

    def test_login_success(self):
        resp = self.client.post("/api/auth/login/", {"username": "alice", "password": "StrongPass123!"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_login_wrong_password(self):
        resp = self.client.post("/api/auth/login/", {"username": "alice", "password": "wrong"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class WalletAutoProvisionTests(AuthenticatedWalletTestCase):
    def test_wallet_created_on_registration(self):
        resp = self.client.get("/api/wallet/balance/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(Decimal(resp.data["balance"]), Decimal("0.00"))

    def test_balance_requires_auth(self):
        self.client.credentials()  # clear auth
        resp = self.client.get("/api/wallet/balance/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class DepositTests(AuthenticatedWalletTestCase):
    def test_deposit_success(self):
        resp = self.client.post("/api/wallet/deposit/", {"amount": "100.00"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(resp.data["balance"]), Decimal("100.00"))

    def test_deposit_negative_amount(self):
        resp = self.client.post("/api/wallet/deposit/", {"amount": "-10.00"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deposit_zero_amount(self):
        resp = self.client.post("/api/wallet/deposit/", {"amount": "0.00"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_deposit_unauthenticated(self):
        self.client.credentials()
        resp = self.client.post("/api/wallet/deposit/", {"amount": "10.00"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class WithdrawTests(AuthenticatedWalletTestCase):
    def test_withdraw_success(self):
        self.client.post("/api/wallet/deposit/", {"amount": "100.00"})
        resp = self.client.post("/api/wallet/withdraw/", {"amount": "40.00"})
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(resp.data["balance"]), Decimal("60.00"))

    def test_withdraw_insufficient_funds(self):
        resp = self.client.post("/api/wallet/withdraw/", {"amount": "40.00"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_withdraw_negative_amount(self):
        resp = self.client.post("/api/wallet/withdraw/", {"amount": "-5.00"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_withdraw_unauthenticated(self):
        self.client.credentials()
        resp = self.client.post("/api/wallet/withdraw/", {"amount": "10.00"})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class TransactionHistoryTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", email="a@example.com", password="StrongPass123!")
        self.bob = User.objects.create_user(username="bob", email="b@example.com", password="StrongPass123!")

        resp = self.client.post("/api/auth/login/", {"username": "alice", "password": "StrongPass123!"})
        self.alice_token = resp.data["access"]

        resp = self.client.post("/api/auth/login/", {"username": "bob", "password": "StrongPass123!"})
        self.bob_token = resp.data["access"]

    def test_history_scoped_to_user(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.alice_token}")
        self.client.post("/api/wallet/deposit/", {"amount": "50.00"})

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.bob_token}")
        self.client.post("/api/wallet/deposit/", {"amount": "75.00"})

        resp = self.client.get("/api/wallet/transactions/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(Decimal(results[0]["amount"]), Decimal("75.00"))

    def test_history_pagination_and_order(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.alice_token}")
        for amt in ["10.00", "20.00", "30.00"]:
            self.client.post("/api/wallet/deposit/", {"amount": amt})

        resp = self.client.get("/api/wallet/transactions/")
        results = resp.data["results"]
        # newest first
        self.assertEqual(Decimal(results[0]["amount"]), Decimal("30.00"))

    def test_history_filter_by_type(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.alice_token}")
        self.client.post("/api/wallet/deposit/", {"amount": "100.00"})
        self.client.post("/api/wallet/withdraw/", {"amount": "20.00"})

        resp = self.client.get("/api/wallet/transactions/?type=WITHDRAWAL")
        results = resp.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["type"], "WITHDRAWAL")
