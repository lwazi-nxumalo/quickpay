from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from .models import Entry, Transaction, Wallet


class WalletService:

  @staticmethod
  def transfer(
      sender_wallet_id: int,
      recipient_wallet_id: int,
      amount: Decimal,
      description: str,
      idempotency_key: str,
  ) -> Transaction:
    """Executes a race-condition safe, idempotent P2P transfer between wallets.

    Rule: User wallets are liabilities (balance = credits - debits).
    """

    # Fast-path check outside transaction
    existing_txn = Transaction.objects.filter(
        idempotency_key=idempotency_key
    ).first()
    if existing_txn:
      return existing_txn

    if amount <= 0:
      raise ValidationError("Transfer amount must be greater than zero.")

    if sender_wallet_id == recipient_wallet_id:
      raise ValidationError("Cannot transfer funds to the same wallet.")

    try:
      with transaction.atomic():
        # Figure out lock order to prevent deadlocks 
        wallet_ids = sorted([sender_wallet_id, recipient_wallet_id])

        # Fetch and lock both wallets in strict ascending ID order
        locked_wallets = {
            w.id: w
            for w in Wallet.objects.select_for_update()
            .filter(id__in=wallet_ids)
            .order_by("id")
        }

        if len(locked_wallets) != 2:
          raise ValidationError("One or both wallets do not exist.")

        sender_wallet = locked_wallets[sender_wallet_id]
        recipient_wallet = locked_wallets[recipient_wallet_id]

        if not sender_wallet.is_active or not recipient_wallet.is_active:
          raise ValidationError("One or both wallets are inactive.")

        # Overdraft check (System pool is exempt)
        if (
            sender_wallet.account_type == Wallet.AccountType.USER
            and sender_wallet.get_balance() < amount
        ):
          raise ValidationError("Insufficient funds.")

        # Creates a savepoint for race-condition idempotency retries
        try:
          with transaction.atomic():
            txn = Transaction.objects.create(
                description=description, idempotency_key=idempotency_key
            )
        except IntegrityError:
          # Savepoint rolls back
          return Transaction.objects.get(idempotency_key=idempotency_key)

        # DEBIT
        Entry.objects.create(
            transaction=txn,
            wallet=sender_wallet,
            debit=amount,
            credit=Decimal("0.00"),
        )

        # CREDIT
        Entry.objects.create(
            transaction=txn,
            wallet=recipient_wallet,
            debit=Decimal("0.00"),
            credit=amount,
        )

        return txn

    except Wallet.DoesNotExist:
      raise ValidationError("One or both wallets do not exist.")
    except Exception as e:
      raise ValidationError(f"Transaction aborted: {str(e)}")

  @staticmethod
  def deposit(
      recipient_wallet_id: int,
      amount: Decimal,
      description: str,
      idempotency_key: str,
  ) -> Transaction:
    """A load is a transfer from the system pool to the user's wallet."""
    try:
      system_wallet = Wallet.objects.get(account_type=Wallet.AccountType.SYSTEM_POOL)
    except Wallet.DoesNotExist:
      raise ValidationError("System pool wallet is not set up.")

    return WalletService.transfer(
        sender_wallet_id=system_wallet.id,
        recipient_wallet_id=recipient_wallet_id,
        amount=amount,
        description=f"SYSTEM DEPOSIT: {description}",
        idempotency_key=idempotency_key,
    )