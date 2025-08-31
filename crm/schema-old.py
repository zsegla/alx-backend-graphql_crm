import graphene
from .models import Customer, Product, Order
from django.db import IntegrityError
import re
from datetime import datetime
from graphene import relay
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from .filters import CustomerFilter, ProductFilter, OrderFilter


class CustomerNode(DjangoObjectType):
    class Meta:
        model = Customer
        interfaces = (relay.Node,)
        filterset_class = CustomerFilter


class ProductNode(DjangoObjectType):
    class Meta:
        model = Product
        interfaces = (relay.Node,)
        filterset_class = ProductFilter


class OrderNode(DjangoObjectType):
    class Meta:
        model = Order
        interfaces = (relay.Node,)
        filterset_class = OrderFilter


# Output Types
class CustomerType(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()

class ProductType(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String(required=True)
    price = graphene.Float(required=True)
    stock = graphene.Int()

class OrderType(graphene.ObjectType):
    id = graphene.ID()
    customer = graphene.Field(CustomerType)
    products = graphene.List(ProductType)
    order_date = graphene.DateTime()

class Query(graphene.ObjectType):
    customers = graphene.List(CustomerType)
    products = graphene.List(ProductType)
    orders = graphene.List(OrderType)

    # Relay connections with filtering and sorting
    all_customers = DjangoFilterConnectionField(CustomerNode)
    all_products = DjangoFilterConnectionField(ProductNode)
    all_orders = DjangoFilterConnectionField(OrderNode)

    # fetching single nodes by global relay ID
    customer = relay.Node.Field(CustomerNode)
    product = relay.Node.Field(ProductNode)
    order = relay.Node.Field(OrderNode)

    def resolve_customers(self, info):
        return Customer.objects.all()

    def resolve_products(self, info):
        return Product.objects.all()

    def resolve_orders(self, info):
        return Order.objects.all()

# Input Types
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()

# Mutations
def validate_customer_phone_number(phone):
    phone_pattern = r'^\+?\d{1,3}?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}$'
    if not re.match(phone_pattern, phone):
        raise ValueError("Invalid phone format.")

class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String()

    customer = graphene.Field(CustomerType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, name, email, phone=None):
        if phone:
            try:
                validate_customer_phone_number(phone)
            except ValueError as e:
                return CreateCustomer(customer=None, success=False, message="Invalid phone format.")
        else :
            phone = None
        try:
            customer = Customer.objects.create(name=name, email=email, phone=phone)
            return CreateCustomer(customer=customer, success=True, message="Customer created successfully.")
        except IntegrityError as e:
            return CreateCustomer(customer=None, success=False, message=f"Email already exists.")

class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        customers = graphene.List(CustomerInput, required=True)

    new_customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)


    def mutate(self, info, customers):
        created_customers = []
        occurred_errors = []

        for index, customer in enumerate(customers):
            name = customer.get('name')
            email = customer.get('email')
            phone = customer.get('phone')
            if not name or not email:
                occurred_errors.append(f"Row {index + 1}: name and email are required.")
                continue

            if phone:
                try:
                    validate_customer_phone_number(phone)
                except ValueError:
                    occurred_errors.append(f"Row {index + 1}: Invalid phone format."
)
                    continue
            try:
                customer = Customer.objects.create(name=name, email=email, phone=phone)
                created_customers.append(customer)
            except IntegrityError:
                occurred_errors.append("Row {index + 1}: Email already exists.")
        return BulkCreateCustomers(new_customers=created_customers, errors=self.occurred_errors)

class CreateProduct(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        stock = graphene.Int()

    product = graphene.Field(ProductType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, name, price, stock=0):
        if price < 0:
            return CreateProduct(product=None, success=False, message="Price must be a positive value")
        if stock < 0:
            return CreateProduct(product=None, success=False, message="Stock must be a positive value")
        new_product = Product.objects.create(name=name, price=price, stock=stock)
        return CreateProduct(product=new_product, success=True, message="product create successfully")

class CreateOrder(graphene.Mutation):
    class Arguments:
        customer = graphene.ID(required=True)
        products = graphene.List(graphene.ID, required=True)
        order_date = graphene.DateTime()

    order = graphene.Field(OrderType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, customer, products, order_date=None):
        try:
            customer = Customer.objects.get(id=customer)
        except Customer.DoesNotExist:
            return CreateOrder(success=False, message="customer_id not valid.")

        if not products:
            return CreateOrder(success=False, message="At least one product_id is required.")

        products_exist = Product.objects.filter(id__in=products).count() == len(products)
        if not products_exist:
            return CreateOrder(success=False, message="One or more product IDs are invalid.")

        if order_date is None:
            order_date = datetime.now()

        order = Order.objects.create(customer=customer, order_date=order_date)

        order.products.add(*products)

        order_with_items = Order.objects.select_related('customer').prefetch_related('products').get(id=order.id)

        return CreateOrder(order=order_with_items, success=True, message="Order created successfully.")

class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
