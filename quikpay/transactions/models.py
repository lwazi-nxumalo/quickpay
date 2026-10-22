from django.db import models
from decimal import Decimal
from django.core.exceptions import ValidationError
import uuid
from django.db.models import Sum

# Create your models here.

#The Accounts   

    #Wallet
"""
fields need to be ( id_number , account_type , GL Code , currency , is_active and created_at)
    
"""

class Wallet(models.Model):
    
    class AccountType(models.TextChoices):
        USER = 'user', 'User'
        SYSTEM_POOL = 'system_pool', 'System Pool'
        
    user = models.OneToOneField('users.User', on_delete=models.PROTECT, related_name='wallet', null=True, blank=True)
    account_type = models.CharField(max_length=20, choices=AccountType.choices, default=AccountType.USER)
    gl_code = models.CharField(max_length=50, unique=True, editable=False)
    currency = models.CharField(max_length=3, default='ZAR' )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.gl_code:
            if self.account_type == self.AccountType.SYSTEM_POOL:
                self.gl_code = '1000-SYS-POOL'
            elif self.account_type == self.AccountType.USER:
                if not self.user:
                    raise ValidationError("User must be set for user wallets.")
                self.gl_code = f'2000-USER-{self.user.pk:06d}'
                
        super().save(*args, **kwargs)
    
    def get_balance(self) -> Decimal:
        result = self.entries.aggregate(
            total_debit=Sum("debit"), total_credit=Sum("credit")
        )
        
        debit_sum = result["total_debit"] or Decimal("0.00")
        credit_sum = result["total_credit"] or Decimal("0.00")
        
        return credit_sum - debit_sum

    def __str__(self):
        return f'Wallet: {self.gl_code} ({self.account_type})'


#The Journal entry 

    #Transaction
"""
Fields need to be ( reference_number , description , created_at )
"""
class Transaction(models.Model):
    reference_number = models.CharField(max_length=30, unique=True, blank=True , editable=False)
    idempotency_key = models.CharField(max_length=255 , unique=True, null=False, blank=False)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self.generate_unique_reference()
        super().save(*args, **kwargs)

    def generate_unique_reference(self):
       random_hex = uuid.uuid4().hex[:8].upper()
       return f"Q-REF-{random_hex}"

    def __str__(self):
        return f"Transaction: {self.reference_number}"
    
        
#need to generate a unique reference number for each transaction that is human readable.
#user generated descripton of the transaction but must be a charfield to limit the length of the description to 255 characters.
#created_at for auditing purposes 
#save needs to check if the reference_number is unique and if not generate a new one


#The Entries

    #Entry
"""
Fields need to be ( transaction , wallet , debit , credit , created_at (technically a redundant field but for auditing purposes it is helpful to have it) )
"""
#transaction is a foreign key to the transaction model uses related_name='entries' to allow for reverse lookups from the transaction model to the entry model.
#wallet links the line item to the user wallet
#debit & credit max_digits=11 , decimal_places=2 to allow for up to 999999999.99
#created_at for auditing purposes
#ensure on_delete=models.Protect to ensure immutability 

class Entry(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT, related_name='entries')
    wallet = models.ForeignKey(Wallet, on_delete=models.PROTECT, related_name='entries')
    debit = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal('0.00'))
    credit = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"Wallet {self.wallet.gl_code} -> Debit: {self.debit} | Credit: {self.credit} | Transaction: {self.transaction.reference_number}"
        )