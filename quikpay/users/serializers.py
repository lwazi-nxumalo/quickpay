import logging
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import serializers
from .models import User

logger = logging.getLogger(__name__)

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ['id', 'email', 'phone_number', 'first_name', 'last_name', 'id_number', 'password']

    def create(self, validated_data):
        password = validated_data.pop('password')

        try:
            user = User.objects.create_user(
                email=validated_data['email'],
                phone_number=validated_data['phone_number'],
                id_number=validated_data['id_number'],
                first_name=validated_data['first_name'],
                last_name=validated_data['last_name'],
                password=password
            )
            return user

        except (IntegrityError, DjangoValidationError) as e:
            logger.error(f"Database Integrity Error during user creation: {str(e)}", exc_info=True)

            if hasattr(e, 'message_dict'):
                raise serializers.ValidationError(e.message_dict)
            elif hasattr(e, 'messages'):
                raise serializers.ValidationError(e.messages)

            error_msg = str(e).lower()
            if "unique constraint" in error_msg or "duplicate key" in error_msg:
                raise serializers.ValidationError({
                    "detail": "A user with this email, phone number, or ID number already exists."
                })

            raise serializers.ValidationError({
                "detail": "An error occurred while processing your request. Please try again."
            })