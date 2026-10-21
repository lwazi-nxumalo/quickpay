from django.shortcuts import render
from rest_framework import generics
from .models import User
from .serializers import UserSerializer
from rest_framework import permissions

# Create your views here.

class IsNotAuthenticated(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and not request.user.is_authenticated)


class UserRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsNotAuthenticated]
    
    def get_object(self):
        return self.request.user
