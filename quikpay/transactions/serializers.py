from rest_framework import serializers


class TransferSerializer(serializers.Serializer):
  recipient_wallet_id = serializers.IntegerField()
  amount = serializers.DecimalField(max_digits=12, decimal_places=2)
  description = serializers.CharField(max_length=255)
  idempotency_key = serializers.CharField(max_length=255)


class DepositSerializer(serializers.Serializer):
  amount = serializers.DecimalField(max_digits=12, decimal_places=2)
  description = serializers.CharField(max_length=255)
  idempotency_key = serializers.CharField(max_length=255)