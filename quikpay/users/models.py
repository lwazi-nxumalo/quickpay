from datetime import datetime , date

from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import  AbstractUser, BaseUserManager
from phonenumber_field.modelfields import PhoneNumberField

def validate_rsa_id(value):
    id_str = str(value)
    
    #Base type & length check
    if not id_str.isdigit() or len(id_str) != 13:
        raise ValidationError("RSA ID must be a 13-digit number.")
    if len(id_str) != 13:
        raise ValidationError("RSA ID must be exactly 13 digits long.")
    
    # Birthdate validation
    yy = int(id_str[:2])
    mm = int(id_str[2:4])  
    dd = int(id_str[4:6])
    
    current_year = datetime.now().year
    current_yy = current_year % 100
    century = 1900 if yy > current_yy else 2000
    full_year = century + yy
    
    try:
        date(full_year, mm, dd)
    except ValueError:
        raise ValidationError("RSA ID contains an invalid date.")
    
    # Citizenship Verifivation
    citzienship = int(id_str[10])
    if citzienship not in [0, 1 ,2]:
        raise ValidationError("Invalid citizenship status in RSA ID. Must be 0, 1 or 2.")
    
    #Luhn Algorithm Check
    digits = [int(char) for char in id_str]
    for i in range(11, -1 , -2):
        doubled = digits[i] * 2
        digits[i] = doubled if doubled < 10 else doubled - 9
        
    if sum(digits) % 10 != 0:
        raise ValidationError("RSA ID failed the Luhn check.")
    
class SouthAfricanIDField(models.CharField):
    def __init__(self , *args, **kwargs):
        kwargs['max_length'] = 13
        super().__init__(*args, **kwargs)
        self.validators.append(validate_rsa_id)

class CustomUserManager(BaseUserManager):
    def create_user(self, email, phone_number, id_number, first_name, last_name, password , **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        if not phone_number:
            raise ValueError('The Phone Number field must be set')
        if not id_number:
            raise ValueError('The ID Number field must be set')
        if not first_name:
            raise ValueError('The First Name field must be set')
        if not last_name:
            raise ValueError('The Last Name field must be set')

        email = self.normalize_email(email)
        user = self.model(
            email=email,
            phone_number=phone_number,
            id_number=id_number,
            first_name=first_name,
            last_name=last_name,
            **extra_fields
        )
         
        user.set_password(password)
        user.full_clean() 
        user.save(using=self._db)
        return user

    def create_superuser(self, email, phone_number, id_number, first_name, last_name, password , **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, phone_number, id_number, first_name, last_name, password, **extra_fields)
# Create your models here.
class User(AbstractUser):
    username = None 
    email = models.EmailField(unique=True)
    phone_number = PhoneNumberField(unique=True)
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)
    id_number = SouthAfricanIDField(unique=True)
    status = models.CharField(max_length=20, choices=[
        ('pending_kyc', 'Pending KYC'),
        ('active', 'Active'),
        ('locked', 'Locked'),
        ('suspended', 'Suspended'),
        ('deleted', 'Deleted')
    ], default='pending_kyc')

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email' 
    REQUIRED_FIELDS = ['phone_number', 'id_number', 'first_name', 'last_name']

class residentialAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.address_line1}, {self.city}, {self.state}, {self.postal_code}, {self.country}"

    class Meta:
        verbose_name = "Residential Address"
        verbose_name_plural = "Residential Addresses"

