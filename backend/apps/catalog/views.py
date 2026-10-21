from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAdminUser
from .models import Category, Product, PizzaCrust
from .serializers import CategorySerializer, ProductSerializer, PizzaCrustSerializer
from apps.tenants.models import Tenant
from apps.core.tenancy import get_current_tenant
from .site_data import build_site_data

class PublicCatalogView(APIView):
    """Public endpoint returning all categories, products and crusts for the Don Corleone website."""
    permission_classes = [AllowAny]

    def get(self, request):
        tenant = Tenant.objects.first()
        if not tenant:
            return Response({"categorias": [], "bordas": []})

        categories = Category.objects.filter(tenant=tenant, is_active=True).prefetch_related('products')
        crusts = PizzaCrust.objects.filter(tenant=tenant, is_active=True)

        return Response({
            "categorias": CategorySerializer(categories, many=True).data,
            "bordas": PizzaCrustSerializer(crusts, many=True).data
        })

class PublicSiteDataView(APIView):
    """Menu, crusts, neighborhoods, hours and payment info in the website's own data format."""
    permission_classes = [AllowAny]

    def get(self, request):
        tenant = get_current_tenant()
        if not tenant:
            return Response({"detail": "Loja não configurada."}, status=status.HTTP_404_NOT_FOUND)
        return Response(build_site_data(tenant, request))

class AdminProductViewSet(viewsets.ModelViewSet):
    """Admin CRUD for products."""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        tenant = Tenant.objects.first()
        serializer.save(tenant=tenant)

class AdminCategoryViewSet(viewsets.ModelViewSet):
    """Admin CRUD for categories."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        tenant = Tenant.objects.first()
        serializer.save(tenant=tenant)

class AdminPizzaCrustViewSet(viewsets.ModelViewSet):
    """Admin CRUD for crusts."""
    queryset = PizzaCrust.objects.all()
    serializer_class = PizzaCrustSerializer
    permission_classes = [IsAdminUser]

    def perform_create(self, serializer):
        tenant = Tenant.objects.first()
        serializer.save(tenant=tenant)

class ToggleProductAvailabilityView(APIView):
    """Quick 1-click toggle for product availability by owner/kitchen."""
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
            product.is_available = not product.is_available
            product.save()
            return Response({
                "id": str(product.id),
                "name": product.name,
                "is_available": product.is_available,
                "message": f"Produto {'ativado' if product.is_available else 'marcado como esgotado'} com sucesso!"
            })
        except Product.DoesNotExist:
            return Response({"error": "Produto não encontrado"}, status=status.HTTP_404_NOT_FOUND)
