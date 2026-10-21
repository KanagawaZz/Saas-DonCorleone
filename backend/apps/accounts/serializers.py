from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import User, CustomerProfile
from apps.tenants.models import Tenant

def normalize_login(value: str) -> str:
    """Customers log in with their WhatsApp: '(65) 99999-0000' and '65999990000' are the same login."""
    value = (value or '').strip()
    digits = ''.join(filter(str.isdigit, value))
    if digits and len(digits) >= 10 and not any(c.isalpha() for c in value):
        return digits
    return value


class CustomerRegisterSerializer(serializers.Serializer):
    # The customer's login is the WhatsApp number (digits only)
    password = serializers.CharField(write_only=True, min_length=6)
    name = serializers.CharField(write_only=True, max_length=150)
    whatsapp = serializers.CharField(write_only=True)
    street = serializers.CharField(write_only=True, required=False, allow_blank=True)
    number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    neighborhood = serializers.CharField(write_only=True, required=False, allow_blank=True)
    city = serializers.CharField(write_only=True, required=False, default="Cuiabá")

    def validate_whatsapp(self, value):
        digits = ''.join(filter(str.isdigit, value))
        if len(digits) < 10:
            raise serializers.ValidationError("Informe um WhatsApp válido com DDD.")
        if User.objects.filter(username=digits).exists():
            raise serializers.ValidationError("Este WhatsApp já está cadastrado. Faça login.")
        return digits

    def validate(self, attrs):
        try:
            validate_password(attrs['password'], User(username=attrs['whatsapp'], first_name=attrs['name']))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'password': list(exc.messages)})
        return attrs

    def create(self, validated_data):
        name = validated_data.pop('name')
        whatsapp = validated_data.pop('whatsapp')
        street = validated_data.pop('street', '')
        number = validated_data.pop('number', '')
        neighborhood = validated_data.pop('neighborhood', '')
        city = validated_data.pop('city', 'Cuiabá')
        password = validated_data.pop('password')
        username = whatsapp

        # Get default tenant (Don Corleone)
        tenant = Tenant.objects.first()

        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=name,
            phone=whatsapp,
            role=User.Role.CUSTOMER,
            tenant=tenant
        )

        CustomerProfile.objects.create(
            user=user,
            tenant=tenant,
            whatsapp=whatsapp,
            default_address_street=street,
            default_address_number=number,
            default_address_neighborhood=neighborhood,
            default_address_city=city
        )

        return user

class CustomerLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = normalize_login(attrs.get('username'))
        password = attrs.get('password')
        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Credenciais inválidas. Verifique seu login e senha.")
        attrs['user'] = user
        return attrs

class UserProfileSerializer(serializers.ModelSerializer):
    customer_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'phone', 'role', 'customer_profile']

    def get_customer_profile(self, obj):
        if hasattr(obj, 'customer_profile'):
            cp = obj.customer_profile
            return {
                'whatsapp': cp.whatsapp,
                'street': cp.default_address_street,
                'number': cp.default_address_number,
                'neighborhood': cp.default_address_neighborhood,
                'city': cp.default_address_city,
                'is_vip': cp.is_vip,
                'total_orders': cp.total_orders_count
            }
        return None
