from django.core.exceptions import ValidationError
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import User
from users.permissions import IsAccountActive
from .models import Wallet , Entry
from .serializers import DepositSerializer, TransferSerializer ,TransactionHistorySerializer
from .services import WalletService


class TransferAPIView(APIView):
  permission_classes = [IsAuthenticated, IsAccountActive]

  def post(self, request):
    serializer = TransferSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
      # Securely fetch sender wallet from authenticated user
      sender_wallet_id = request.user.wallet.id

      recipient_identifier = serializer.validated_data['recipient']
      recipient_user = User.objects.get(
          Q(email=recipient_identifier) | Q(phone_number=recipient_identifier)
      )
      recipient_wallet_id = recipient_user.wallet.id

      txn = WalletService.transfer(
          sender_wallet_id=sender_wallet_id,
          recipient_wallet_id=recipient_wallet_id,
          amount=serializer.validated_data['amount'],
          description=serializer.validated_data['description'],
          idempotency_key=serializer.validated_data['idempotency_key'],
      )
      return Response(
          {'status': 'success', 'transaction_id': txn.id},
          status=status.HTTP_201_CREATED,
      )
    except (User.DoesNotExist, Wallet.DoesNotExist):
      return Response(
          {'status': 'error', 'message': 'Recipient not found.'},
          status=status.HTTP_404_NOT_FOUND,
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
      
class BalanceAPIView(APIView):
  permission_classes = [IsAuthenticated, IsAccountActive]

  def get(self, request):
    try:
      wallet = request.user.wallet
      return Response(
          {
              'status': 'success',
              'balance': wallet.get_balance(),
              'is_active': wallet.is_active,
          },
          status=status.HTTP_200_OK,
      )
    except Wallet.DoesNotExist:
      return Response(
          {'status': 'error', 'message': 'Wallet not found.'},
          status=status.HTTP_404_NOT_FOUND,
      )


class TransactionHistoryAPIView(APIView):
  permission_classes = [IsAuthenticated, IsAccountActive]

  def get(self, request):
    try:
      wallet = request.user.wallet
      entries = (
          Entry.objects.filter(wallet=wallet)
          .select_related('transaction')
          .order_by('-transaction__created_at')
      )
      serializer = TransactionHistorySerializer(entries, many=True)
      return Response(
          {'status': 'success', 'history': serializer.data},
          status=status.HTTP_200_OK,
      )
    except Wallet.DoesNotExist:
      return Response(
          {'status': 'error', 'message': 'Wallet not found.'},
          status=status.HTTP_404_NOT_FOUND,
      )