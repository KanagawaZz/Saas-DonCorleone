from rest_framework import serializers
from .models import Category, Product, ProductSizePrice, PizzaCrust

class ProductSizePriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductSizePrice
        fields = ['id', 'size_id', 'size_name', 'slices', 'max_flavors', 'price']

class PizzaCrustSerializer(serializers.ModelSerializer):
    class Meta:
        model = PizzaCrust
        fields = ['id', 'name', 'slug', 'price', 'price_text', 'is_default', 'is_highlight', 'is_active']

class ProductSerializer(serializers.ModelSerializer):
    size_prices = ProductSizePriceSerializer(many=True, read_only=True)
    effective_image_url = serializers.CharField(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'product_type', 'price_category',
            'base_price', 'price_text', 'tag', 'is_highlight', 'effective_image_url',
            'is_available', 'display_order', 'extra_details', 'size_prices'
        ]

class CategorySerializer(serializers.ModelSerializer):
    itens = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'display_order', 'is_active', 'itens']

    def get_itens(self, obj):
        # Only active and available items for public catalog
        products = obj.products.filter(is_available=True)
        return ProductSerializer(products, many=True).data

class PublicCatalogSerializer(serializers.Serializer):
    categorias = CategorySerializer(many=True)
    bordas = PizzaCrustSerializer(many=True)
