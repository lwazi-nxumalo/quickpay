from rest_framework import serializers
from .models import Entry, Wallet


class TransferSerializer(serializers.Serializer):
  recipient = serializers.CharField(max_length=255)
  amount = serializers.DecimalField(max_digits=12, decimal_places=2)
  description = serializers.CharField(max_length=255)
  idempotency_key = serializers.CharField(max_length=255)


class DepositSerializer(serializers.Serializer):
  amount = serializers.DecimalField(max_digits=12, decimal_places=2)
  description = serializers.CharField(max_length=255)
  idempotency_key = serializers.CharField(max_length=255)

class BalanceSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(source='get_balance', max_digits=12, decimal_places=2)

    class Meta:
        model = Wallet
        fields = ['balance', 'is_active', 'created_at']


class TransactionHistorySerializer(serializers.ModelSerializer):
    transaction_id = serializers.IntegerField(source='transaction.id')
    description = serializers.CharField(source='transaction.description')
    timestamp = serializers.DateTimeField(source='transaction.created_at')

    class Meta:
        model = Entry
        fields = ['transaction_id', 'description', 'debit', 'credit', 'timestamp']