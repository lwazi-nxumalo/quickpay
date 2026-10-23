from rest_framework import serializers


class TransferSerializer(serializers.Serializer):
  recipient = serializers.CharField(max_length=255)
  amount = serializers.DecimalField(max_digits=12, decimal_places=2)
  description = serializers.CharField(max_length=255)
  idempotency_key = serializers.CharField(max_length=255)


class DepositSerializer(serializers.Serializer):
  amount = serializers.DecimalField(max_digits=12, decimal_places=2)
  description = serializers.CharField(max_length=255)
  idempotency_key = serializers.CharField(max_length=255)