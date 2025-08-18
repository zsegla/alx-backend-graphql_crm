# crm/filters.py

import django_filters
from django_filters import rest_framework as filters
from .models import Customer, Product, Order
import re

class CustomerFilter(filters.FilterSet):
    """
    FilterSet for the Customer model, allowing filtering by various fields.
    """
    # Case-insensitive partial match for name
    name = filters.CharFilter(field_name="name", lookup_expr='icontains')
    
    # Case-insensitive partial match for email
    email = filters.CharFilter(field_name="email", lookup_expr='icontains')
    
    # Date range filter for created_at field
    created_at__gte = django_filters.DateFilter(field_name="created_at", lookup_expr="gte")
    created_at__lte = django_filters.DateFilter(field_name="created_at", lookup_expr="lte")

    # Custom filter to match phone numbers with a specific pattern (e.g., starting with +1)
    phone_pattern = filters.CharFilter(method='filter_phone_pattern', label="Phone Pattern")

    def filter_phone_pattern(self, queryset, name, value):
        """
        Filters customers by a phone number pattern.
        """
        if value:
            # The regex pattern will match the value at the beginning of the phone number string.
            pattern = re.compile(r'^{}'.format(re.escape(value)))
            
            # Filter the queryset to find customers whose phone number matches the pattern.
            return queryset.filter(phone__regex=pattern.pattern)
        return queryset

    class Meta:
        model = Customer
        # Define fields to be filtered directly by django-filter
        fields = ['name', 'email', 'created_at', 'phone']


class ProductFilter(filters.FilterSet):
    """
    FilterSet for the Product model.
    """
    # Case-insensitive partial match for product name
    name = filters.CharFilter(lookup_expr='icontains')
    
    # Range filter for price
    price = filters.RangeFilter()
    price__gte = django_filters.NumberFilter(field_name="price", lookup_expr="gte")
    price__lte = django_filters.NumberFilter(field_name="price", lookup_expr="lte")
    
    # Range filter for stock
    stock = filters.RangeFilter() 
    stock__gte = django_filters.NumberFilter(field_name="stock", lookup_expr="gte")
    stock__lte = django_filters.NumberFilter(field_name="stock", lookup_expr="lte")
    

    # Custom boolean filter to easily find products with low stock (e.g., stock < 10)
    low_stock = filters.BooleanFilter(method='filter_low_stock', label="Low Stock")

    def filter_low_stock(self, queryset, name, value):
        """
        Filters for products with less than 10 items in stock.
        """
        if value:
            return queryset.filter(stock__lt=10)
        return queryset

    class Meta:
        model = Product
        fields = ['name', 'price', 'stock']


class OrderFilter(filters.FilterSet):
    """
    FilterSet for the Order model.
    """
    # Range filter for total_amount
    total_amount = filters.RangeFilter()

    # Date range filter for order_date
    order_date = filters.DateFromToRangeFilter()
    
    # Filter orders by the customer's name using a related field lookup
    customer_name = filters.CharFilter(field_name='customer__name', lookup_expr='icontains')
    
    # Filter orders by a product's name using a related field lookup
    product_name = filters.CharFilter(field_name='products__name', lookup_expr='icontains')

    # Challenge: Allow filtering orders that include a specific product ID
    # This filter allows selection of multiple product IDs to find orders containing them.
    product_ids = filters.ModelMultipleChoiceFilter(
        field_name='products__id',
        queryset=Product.objects.all()
    )

    class Meta:
        model = Order
        fields = ['total_amount', 'order_date', 'customer_name', 'product_name']