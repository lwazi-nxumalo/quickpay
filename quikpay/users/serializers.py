from rest_framework import serializers
from .models import User    

class UserSerializer(serializers.ModelSerializer):
    
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ['id', 'email', 'phone_number', 'first_name', 'last_name', 'id_number', 'password']
        
    def create(self, validated_data):
        password=validated_data.pop('password')

        user = User.objects.create_user(
            email=validated_data['email'],
            phone_number=validated_data['phone_number'],
            id_number=validated_data['id_number'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=password
        )           
        return user
        
        
        