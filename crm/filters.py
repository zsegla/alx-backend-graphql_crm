import django_filters as filters
import django_filters
from django.db.models import Sum
from .models import Customer, Product, Order


class CustomerFilter(django_filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    email = filters.CharFilter(field_name="email", lookup_expr="icontains")

    created_at__gte = filters.DateTimeFilter(field_name="created_at", lookup_expr="gte")
    created_at__lte = filters.DateTimeFilter(field_name="created_at", lookup_expr="lte")

    phone_pattern = filters.CharFilter(method="filter_phone_pattern")

    order_by = filters.OrderingFilter(
        fields=(
            ("name", "name"),
            ("email", "email"),
            ("created_at", "created_at"),
        ),
        field_labels={
            "name": "Name",
            "email": "Email",
            "created_at": "Created At",
        },
        label="Order by",
    )

    def filter_phone_pattern(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(phone__startswith=value)

    class Meta:
        model = Customer
        fields = [
            "name",
            "email",
            "created_at__gte",
            "created_at__lte",
            "phone_pattern",
            "order_by",
        ]


class ProductFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    price__gte = filters.NumberFilter(field_name="price", lookup_expr="gte")
    price__lte = filters.NumberFilter(field_name="price", lookup_expr="lte")
    stock__gte = filters.NumberFilter(field_name="stock", lookup_expr="gte")
    stock__lte = filters.NumberFilter(field_name="stock", lookup_expr="lte")

    low_stock = filters.BooleanFilter(method="filter_low_stock")

    order_by = filters.OrderingFilter(
        fields=(
            ("name", "name"),
            ("price", "price"),
            ("stock", "stock"),
        ),
    )

    def filter_low_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock__lt=10)
        return queryset

    class Meta:
        model = Product
        fields = [
            "name",
            "price__gte",
            "price__lte",
            "stock__gte",
            "stock__lte",
            "low_stock",
            "order_by",
        ]


class OrderFilter(filters.FilterSet):
    # Date range
    order_date__gte = filters.DateTimeFilter(field_name="order_date", lookup_expr="gte")
    order_date__lte = filters.DateTimeFilter(field_name="order_date", lookup_expr="lte")

    # Related lookups
    customer_name = filters.CharFilter(field_name="customer__name", lookup_expr="icontains")
    product_name = filters.CharFilter(field_name="products__name", lookup_expr="icontains")

    product_id = filters.NumberFilter(method="filter_product_id")

    total_amount__gte = filters.NumberFilter(method="filter_total_amount_gte")
    total_amount__lte = filters.NumberFilter(method="filter_total_amount_lte")

    order_by = filters.OrderingFilter(
        fields=(
            ("order_date", "order_date"),
        ),
    )

    def _annotate_total(self, queryset):
        # Sum of product prices for each order
        return queryset.annotate(total_amount=Sum("products__price"))

    def filter_total_amount_gte(self, queryset, name, value):
        if value is None:
            return queryset
        qs = self._annotate_total(queryset)
        return qs.filter(total_amount__gte=value)

    def filter_total_amount_lte(self, queryset, name, value):
        if value is None:
            return queryset
        qs = self._annotate_total(queryset)
        return qs.filter(total_amount__lte=value)

    def filter_product_id(self, queryset, name, value):
        if value is None:
            return queryset
        return queryset.filter(products__id=value).distinct()

    class Meta:
        model = Order
        fields = [
            "order_date__gte",
            "order_date__lte",
            "customer_name",
            "product_name",
            "product_id",
            "total_amount__gte",
            "total_amount__lte",
            "order_by",
        ]
