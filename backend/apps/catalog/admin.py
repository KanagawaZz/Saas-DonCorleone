from django.contrib import admin
from .models import Category, Product, ProductSizePrice, PizzaCrust

class ProductSizePriceInline(admin.TabularInline):
    model = ProductSizePrice
    extra = 0

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'product_type', 'price_category', 'base_price', 'is_available', 'is_highlight', 'display_order')
    list_filter = ('category', 'product_type', 'price_category', 'is_available', 'is_highlight')
    search_fields = ('name', 'description')
    list_editable = ('is_available', 'display_order', 'base_price')
    inlines = [ProductSizePriceInline]

@admin.register(PizzaCrust)
class PizzaCrustAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'price_text', 'is_default', 'is_highlight', 'is_active', 'display_order')
    list_editable = ('price', 'is_highlight', 'is_active', 'display_order')
