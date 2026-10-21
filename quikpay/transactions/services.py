from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import Entry , Transaction, Wallet

# define a class for transactions
# is the transfer more than the available balance in the wallet? if yes then raise an error
# are they sending to themselves? 
# is the wallet active? 

class WalletService:
    @staticmethod
    def transfer(sender_wallet: Wallet, recipient_wallet: Wallet, amount: Decimal, description: str) -> Transaction:
        # Validate the transfer conditions
        if amount <= 0:
            raise ValidationError("Transfer amount must be greater than zero.")
        if sender_wallet.id == recipient_wallet.id:
            raise ValidationError("Cannot transfer to the same wallet.")
        if not sender_wallet.is_active or not recipient_wallet.is_active:
            raise ValidationError("Both wallets must be active for a transfer.")
        