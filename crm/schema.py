import graphene
import re
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django import DjangoObjectType
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone

from crm.models import Customer
from crm.models import Product
from crm.models import Order
from .filters import CustomerFilter, ProductFilter, OrderFilter


class Query(graphene.ObjectType):
    # Example field
    hello = graphene.String(default_value="Hello from CRM app!")

class Mutation(graphene.ObjectType):
    # Example mutation
    say_hello = graphene.String(name=graphene.String())

    def resolve_say_hello(root, info, name):
        return f"Hello {name}"

class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone")

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")

class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ("id", "customer", "products", "total_amount", "order_date")

class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String(required=False)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    def mutate(self, info, name, email, phone=None):
        if Customer.objects.filter(email=email).exists():
            raise Exception("Email already exists")
        customer = Customer(name=name, email=email, phone=phone)
        customer.full_clean()  # Run model validators
        customer.save()
        return CreateCustomer(customer=customer, message="Customer created successfully")


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        customers = graphene.List(
            graphene.NonNull(
                graphene.InputObjectType(
                    "CustomerInput",
                    name=graphene.String(required=True),
                    email=graphene.String(required=True),
                    phone=graphene.String()
                )
            )
        )

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @transaction.atomic
    def mutate(self, info, customers):
        created_customers = []
        errors = []
        for data in customers:
            try:
                if Customer.objects.filter(email=data.email).exists():
                    raise ValidationError(f"Email {data.email} already exists")
                customer = Customer(name=data.name, email=data.email, phone=data.phone)
                customer.full_clean()
                customer.save()
                created_customers.append(customer)
            except ValidationError as e:
                errors.append(str(e))
        return BulkCreateCustomers(customers=created_customers, errors=errors)


class CreateProduct(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        stock = graphene.Int(required=False, default_value=0)

    product = graphene.Field(ProductType)

    def mutate(self, info, name, price, stock):
        if price <= 0:
            raise Exception("Price must be positive")
        if stock < 0:
            raise Exception("Stock cannot be negative")
        product = Product(name=name, price=price, stock=stock)
        product.save()
        return CreateProduct(product=product)


class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.NonNull(graphene.ID), required=True)

    order = graphene.Field(OrderType)

    @transaction.atomic
    def mutate(self, info, customer_id, product_ids):
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            raise Exception("Invalid customer ID")

        products = list(Product.objects.filter(id__in=product_ids))
        if not products:
            raise Exception("No valid products found")

        order = Order.objects.create(customer=customer)
        order.products.set(products)
        order.total_amount = sum(product.price for product in products)
        order.save()

        return CreateOrder(order=order)

class Query(graphene.ObjectType):
    all_customers = graphene.List(CustomerType)
    all_products = graphene.List(ProductType)
    all_orders = graphene.List(OrderType)

    def resolve_all_customers(root, info):
        return Customer.objects.all()

    def resolve_all_products(root, info):
        return Product.objects.all()

    def resolve_all_orders(root, info):
        return Order.objects.all()


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()


class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = ("id", "name", "email", "phone")

class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = ("id", "name", "price", "stock")

class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = ("id", "customer", "products", "total_amount", "order_date")


# -------------------------------
# Helper validation functions
# -------------------------------
def validate_phone(phone):
    if not re.match(r'^(\+\d{1,15}|\d{3}-\d{3}-\d{4})$', phone):
        raise ValidationError("Phone must be in +1234567890 or 123-456-7890 format")

def validate_email_unique(email):
    if Customer.objects.filter(email=email).exists():
        raise ValidationError(f"Email '{email}' already exists")


# -------------------------------
# Mutations
# -------------------------------
class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String(required=False)

    customer = graphene.Field(CustomerType)
    message = graphene.String()
    errors = graphene.List(graphene.String)

    def mutate(self, info, name, email, phone=None):
        try:
            validate_email_unique(email)
            if phone:
                validate_phone(phone)
            customer = Customer(name=name, email=email, phone=phone)
            customer.full_clean()
            customer.save()
            return CreateCustomer(customer=customer, message="Customer created successfully", errors=[])
        except ValidationError as e:
            return CreateCustomer(customer=None, message="Customer creation failed", errors=e.messages)


class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @transaction.atomic
    def mutate(self, info, input):
        created_customers = []
        errors = []

        for data in input:
            try:
                validate_email_unique(data.email)
                if data.phone:
                    validate_phone(data.phone)
                customer = Customer(name=data.name, email=data.email, phone=data.phone)
                customer.full_clean()
                customer.save()
                created_customers.append(customer)
            except ValidationError as e:
                errors.extend(e.messages)

        return BulkCreateCustomers(customers=created_customers, errors=errors)


class CreateProduct(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        stock = graphene.Int(required=False, default_value=0)

    product = graphene.Field(ProductType)
    errors = graphene.List(graphene.String)

    def mutate(self, info, name, price, stock=0):
        try:
            if price <= 0:
                raise ValidationError("Price must be positive")
            if stock < 0:
                raise ValidationError("Stock cannot be negative")
            product = Product(name=name, price=price, stock=stock)
            product.full_clean()
            product.save()
            return CreateProduct(product=product, errors=[])
        except ValidationError as e:
            return CreateProduct(product=None, errors=e.messages)


class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.NonNull(graphene.ID), required=True)
        order_date = graphene.DateTime(required=False)

    order = graphene.Field(OrderType)
    errors = graphene.List(graphene.String)

    @transaction.atomic
    def mutate(self, info, customer_id, product_ids, order_date=None):
        errors = []

        # Validate customer
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            errors.append(f"Invalid customer ID: {customer_id}")
            return CreateOrder(order=None, errors=errors)

        # Validate products
        products = list(Product.objects.filter(id__in=product_ids))
        if len(products) != len(product_ids):
            invalid_ids = set(product_ids) - set(str(p.id) for p in products)
            errors.append(f"Invalid product IDs: {', '.join(invalid_ids)}")
            return CreateOrder(order=None, errors=errors)

        if not products:
            errors.append("At least one product is required")
            return CreateOrder(order=None, errors=errors)

        # Create order
        order = Order.objects.create(
            customer=customer,
            order_date=order_date or timezone.now()
        )
        order.products.set(products)
        order.total_amount = sum(p.price for p in products)
        order.save()

        return CreateOrder(order=order, errors=[])


# -------------------------------
# Query and Mutation Root
# -------------------------------
class Query(graphene.ObjectType):
    all_customers = graphene.List(CustomerType)
    all_products = graphene.List(ProductType)
    all_orders = graphene.List(OrderType)

    def resolve_all_customers(root, info):
        return Customer.objects.all()

    def resolve_all_products(root, info):
        return Product.objects.all()

    def resolve_all_orders(root, info):
        return Order.objects.all()


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

# Node-based types for filtering & pagination
class CustomerNode(DjangoObjectType):
    class Meta:
        model = Customer
        filterset_class = CustomerFilter
        interfaces = (graphene.relay.Node,)


class ProductNode(DjangoObjectType):
    class Meta:
        model = Product
        filterset_class = ProductFilter
        interfaces = (graphene.relay.Node,)


class OrderNode(DjangoObjectType):
    class Meta:
        model = Order
        filterset_class = OrderFilter
        interfaces = (graphene.relay.Node,)


class Query(graphene.ObjectType):
    customer = graphene.relay.Node.Field(CustomerNode)
    all_customers = DjangoFilterConnectionField(CustomerNode, order_by=graphene.List(of_type=graphene.String))

    product = graphene.relay.Node.Field(ProductNode)
    all_products = DjangoFilterConnectionField(ProductNode, order_by=graphene.List(of_type=graphene.String))

    order = graphene.relay.Node.Field(OrderNode)
    all_orders = DjangoFilterConnectionField(OrderNode, order_by=graphene.List(of_type=graphene.String))

    def resolve_all_customers(self, info, **kwargs):
        qs = Customer.objects.all()
        order_by = kwargs.get("order_by")
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

    def resolve_all_products(self, info, **kwargs):
        qs = Product.objects.all()
        order_by = kwargs.get("order_by")
        if order_by:
            qs = qs.order_by(*order_by)
        return qs

    def resolve_all_orders(self, info, **kwargs):
        qs = Order.objects.all()
        order_by = kwargs.get("order_by")
        if order_by:
            qs = qs.order_by(*order_by)
        return qs
    

class UpdateLowStockProducts(graphene.Mutation):
    class Arguments:
        pass  # no arguments needed

    success = graphene.Boolean()
    message = graphene.String()
    updated_products = graphene.List(ProductType)

    @classmethod
    def mutate(cls, root, info):
        low_stock_products = Product.objects.filter(stock__lt=10)
        updated = []

        for product in low_stock_products:
            product.stock += 10  # simulate restock
            product.save()
            updated.append(product)

        if updated:
            return UpdateLowStockProducts(
                success=True,
                message=f"{len(updated)} products updated at {timezone.now()}",
                updated_products=updated,
            )
        else:
            return UpdateLowStockProducts(
                success=True,
                message="No low-stock products found",
                updated_products=[]
            )


class Mutation(graphene.ObjectType):
    update_low_stock_products = UpdateLowStockProducts.Field()