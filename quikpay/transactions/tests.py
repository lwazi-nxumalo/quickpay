from concurrent.futures import ThreadPoolExecutor 

from decimal import Decimal
from unittest import mock
from django.core.exceptions import ValidationError
from django.db import transaction 
from django.test import TransactionTestCase 
from transactions.models import Entry, Transaction, Wallet
from transactions.services import WalletService
from users.models import User

# Create your tests here

class WalletServiceTransferTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.sender = User.objects.create_user(
            email="sender@example.com",
            phone_number="+27821111111",
            id_number="8809306122082",
            first_name="Sender",
            last_name="User",
            password="password123",
        )

        self.recipient = User.objects.create_user(
            email="recipient@example.com",
            phone_number="+27822222222",
            id_number="8502025009082",
            first_name="Recipient",
            last_name="User",
            password="password123",
        )

        self.sender_wallet = Wallet.objects.create(
            user=self.sender,
            account_type=Wallet.AccountType.USER,
            is_active=True,
        )

        self.recipient_wallet = Wallet.objects.create(
            user=self.recipient,
            account_type=Wallet.AccountType.USER,
            is_active=True,
        )

        self.system_wallet = Wallet.objects.create(
            account_type=Wallet.AccountType.SYSTEM_POOL,
            is_active=True,
        )

        seed_transaction = Transaction.objects.create(
            description="Initial funding",
            idempotency_key="seed-transaction",
        )

        Entry.objects.create(
            transaction=seed_transaction,
            wallet=self.system_wallet,
            debit=Decimal("1000.00"),
            credit=Decimal("0.00"),
        )

        Entry.objects.create(
            transaction=seed_transaction,
            wallet=self.sender_wallet,
            debit=Decimal("0.00"),
            credit=Decimal("1000.00"),
        )

    def test_successful_transfer(self):
        transaction_record = WalletService.transfer(
            sender_wallet_id=self.sender_wallet.id,
            recipient_wallet_id=self.recipient_wallet.id,
            amount=Decimal("250.00"),
            description="Payment",
            idempotency_key="successful-transfer",
        )

        self.assertIsInstance(transaction_record, Transaction)
        self.assertEqual(
            self.sender_wallet.get_balance(),
            Decimal("750.00"),
        )
        self.assertEqual(
            self.recipient_wallet.get_balance(),
            Decimal("250.00"),
        )

        entries = Entry.objects.filter(transaction=transaction_record)

        self.assertEqual(entries.count(), 2)
        self.assertEqual(
            sum(entry.debit for entry in entries),
            Decimal("250.00"),
        )
        self.assertEqual(
            sum(entry.credit for entry in entries),
            Decimal("250.00"),
        )

    def test_rejects_zero_amount(self):
        with self.assertRaisesMessage(
            ValidationError,
            "Transfer amount must be greater than zero.",
        ):
            WalletService.transfer(
                self.sender_wallet.id,
                self.recipient_wallet.id,
                Decimal("0.00"),
                "Invalid transfer",
                "zero-transfer",
            )

    def test_rejects_negative_amount(self):
        with self.assertRaisesMessage(
            ValidationError,
            "Transfer amount must be greater than zero.",
        ):
            WalletService.transfer(
                self.sender_wallet.id,
                self.recipient_wallet.id,
                Decimal("-10.00"),
                "Invalid transfer",
                "negative-transfer",
            )

    def test_rejects_self_transfer(self):
        with self.assertRaisesMessage(
            ValidationError,
            "same wallet",
        ):
            WalletService.transfer(
                self.sender_wallet.id,
                self.sender_wallet.id,
                Decimal("50.00"),
                "Self transfer",
                "self-transfer",
            )

    def test_rejects_overdraft(self):
        with self.assertRaisesMessage(
            ValidationError,
            "Insufficient funds.",
        ):
            WalletService.transfer(
                self.sender_wallet.id,
                self.recipient_wallet.id,
                Decimal("5000.00"),
                "Overdraft",
                "overdraft-transfer",
            )

        self.assertEqual(
            self.sender_wallet.get_balance(),
            Decimal("1000.00"),
        )

    def test_rejects_inactive_wallet(self):
        self.recipient_wallet.is_active = False
        self.recipient_wallet.save(update_fields=["is_active"])

        with self.assertRaisesMessage(
            ValidationError,
            "inactive",
        ):
            WalletService.transfer(
                self.sender_wallet.id,
                self.recipient_wallet.id,
                Decimal("100.00"),
                "Inactive wallet",
                "inactive-transfer",
            )

    def test_idempotency_prevents_duplicate_transfer(self):
        first = WalletService.transfer(
            self.sender_wallet.id,
            self.recipient_wallet.id,
            Decimal("300.00"),
            "Payment",
            "duplicate-key",
        )

        second = WalletService.transfer(
            self.sender_wallet.id,
            self.recipient_wallet.id,
            Decimal("300.00"),
            "Payment retry",
            "duplicate-key",
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(
            self.sender_wallet.get_balance(),
            Decimal("700.00"),
        )
        self.assertEqual(
            self.recipient_wallet.get_balance(),
            Decimal("300.00"),
        )
        self.assertEqual(
            Entry.objects.filter(transaction=first).count(),
            2,
        )

    def test_failed_entry_write_rolls_back_transaction(self):
        initial_entry_count = Entry.objects.count()
        original_create = Entry.objects.create
        call_count = 0

        def fail_on_second_entry(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 2:
                raise RuntimeError("Simulated database failure")

            return original_create(*args, **kwargs)

        with mock.patch(
            "transactions.services.Entry.objects.create",
            side_effect=fail_on_second_entry,
        ):
            with self.assertRaisesMessage(
                ValidationError,
                "Transaction aborted",
            ):
                WalletService.transfer(
                    self.sender_wallet.id,
                    self.recipient_wallet.id,
                    Decimal("200.00"),
                    "Rollback test",
                    "rollback-transfer",
                )

        self.assertEqual(
            Entry.objects.count(),
            initial_entry_count,
        )
        self.assertEqual(
            self.sender_wallet.get_balance(),
            Decimal("1000.00"),
        )
        self.assertEqual(
            self.recipient_wallet.get_balance(),
            Decimal("0.00"),
        )
        self.assertFalse(
            Transaction.objects.filter(
                idempotency_key="rollback-transfer"
            ).exists()
        )

    def test_concurrent_transfers_do_not_overdraw_wallet(self):
        def make_transfer(key):
            try:
                with transaction.atomic():
                    return WalletService.transfer(
                        self.sender_wallet.id,
                        self.recipient_wallet.id,
                        Decimal("800.00"),
                        "Concurrent transfer",
                        key,
                    )
            except Exception as error:
                return error

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    make_transfer,
                    ["concurrent-one", "concurrent-two"],
                )
            )

        successful = [
            result
            for result in results
            if isinstance(result, Transaction)
        ]

        failed = [
            result
            for result in results
            if isinstance(result, ValidationError)
        ]

        self.assertEqual(len(successful), 1)
        self.assertEqual(len(failed), 1)
        self.assertEqual(
            self.sender_wallet.get_balance(),
            Decimal("200.00"),
        )
        self.assertEqual(
            self.recipient_wallet.get_balance(),
            Decimal("800.00"),
        )
