from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.permissions import IsAccountActive
from .serializers import DepositSerializer, TransferSerializer
from .services import WalletService


class TransferAPIView(APIView):
  permission_classes = [IsAuthenticated, IsAccountActive]

  def post(self, request):
    serializer = TransferSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
      # Securely fetch sender wallet from authenticated user
      sender_wallet_id = request.user.wallet.id

      txn = WalletService.transfer(
          sender_wallet_id=sender_wallet_id,
          recipient_wallet_id=serializer.validated_data['recipient_wallet_id'],
          amount=serializer.validated_data['amount'],
          description=serializer.validated_data['description'],
          idempotency_key=serializer.validated_data['idempotency_key'],
      )
      return Response(
          {'status': 'success', 'transaction_id': txn.id},
          status=status.HTTP_201_CREATED,
      )
    except ValidationError as e:
      return Response(
          {'status': 'error', 'message': str(e)},
          status=status.HTTP_400_BAD_REQUEST,
      )


class DepositAPIView(APIView):
  permission_classes = [IsAuthenticated, IsAccountActive]

  def post(self, request):
    serializer = DepositSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
      # Securely fetch recipient wallet from authenticated user (Self-Load)
      recipient_wallet_id = request.user.wallet.id

      txn = WalletService.deposit(
          recipient_wallet_id=recipient_wallet_id,
          amount=serializer.validated_data['amount'],
          description=serializer.validated_data['description'],
          idempotency_key=serializer.validated_data['idempotency_key'],
      )
      return Response(
          {'status': 'success', 'transaction_id': txn.id},
          status=status.HTTP_201_CREATED,
      )
    except ValidationError as e:
      return Response(
          {'status': 'error', 'message': str(e)},
          status=status.HTTP_400_BAD_REQUEST,
      )