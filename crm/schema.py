# listings/schema.py

import graphene
import re
from graphene_django.types import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.db import transaction, IntegrityError
from django.core.exceptions import ValidationError

from .models import Customer, Product, Order
from .filters import CustomerFilter, ProductFilter, OrderFilter

# GraphQL Types for our Django models
class CustomerType(DjangoObjectType):
    """GraphQL type for the Customer model."""
    class Meta:
        model = Customer
        filter_fields = ['name', 'email']
        interfaces = (graphene.Node,)
        

class ProductType(DjangoObjectType):
    """GraphQL type for the Product model."""
    class Meta:
        model = Product
        filter_fields = {
            'name': ['exact', 'icontains', 'istartswith'],
            'price': ['exact', 'gte', 'lte'],
            'stock': ['exact', 'gte', 'lte'],
        }
        interfaces = (graphene.Node,)
        

class OrderType(DjangoObjectType):
    """GraphQL type for the Order model."""
    class Meta:
        model = Order
        filter_fields = ['total_amount', 'order_date']
        interfaces = (graphene.Node,)

# --- MUTATIONS ---

# Inputs for creating new objects
class CustomerInput(graphene.InputObjectType):
    """Input for creating a new Customer."""
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String(required=False)

class ProductInput(graphene.InputObjectType):
    """Input for creating a new Product."""
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int(required=False, default_value=0)


class CreateCustomer(graphene.Mutation):
    """
    Mutation to create a single customer with added validations.
    Ensures email is unique and validates phone number format.
    """
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    success = graphene.Boolean()
    message = graphene.String()

    @staticmethod
    def mutate(root, info, input=None):
        phone = input.get('phone', None)
        email = input.get('email')

        # Phone number validation using regex (optional field)
        if phone:
            # This regex allows for various formats, including
            # +1234567890, 123-456-7890, (123) 456-7890, etc.
            phone_regex = re.compile(r'^\+?1?\d{9,15}$')
            if not phone_regex.match(phone):
                raise ValidationError("Invalid phone number format. Please use a valid format like '+1234567890' or '123-456-7890'.")

        try:
            # Use transaction.atomic() to ensure the operation is all or nothing
            with transaction.atomic():
                # Create the customer. IntegrityError will be raised if the email exists.
                customer = Customer.objects.create(
                    name=input.get('name'),
                    email=email,
                    phone=phone
                )
            return CreateCustomer(customer=customer, success=True, message="Customer created successfully.")
        except IntegrityError:
            # This specific exception is for when a unique field (like email) is duplicated
            raise ValidationError(f"A customer with the email '{email}' already exists.")
        except Exception as e:
            # Catch any other unexpected errors during creation
            raise ValidationError(f"An unexpected error occurred: {e}")
        
        
class CreateProduct(graphene.Mutation):
    """Mutation to create a single product."""
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)

    @staticmethod
    def mutate(root, info, input=None):
        price = input.get('price')
        stock = input.get('stock', 0)

        # Validation: Ensure price is positive and stock is non-negative
        if price <= 0:
            raise ValidationError("Price must be a positive number.")
        if stock < 0:
            raise ValidationError("Stock cannot be a negative number.")

        try:
            # Create and save the new product
            product = Product.objects.create(
                name=input.get('name'),
                price=price,
                stock=stock,
                description=input.get('description', '')
            )
            return CreateProduct(product=product)
        except Exception as e:
            raise ValidationError(f"An unexpected error occurred while creating the product: {e}")

class BulkCreateCustomers(graphene.Mutation):
    """
    Mutation to create multiple customers in a single transaction,
    supporting partial success.
    """
    class Arguments:
        customers = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, customers):
        created_customers = []
        errors = []

        # Iterate through each customer record to validate and create
        for customer_data in customers:
            try:
                # Validate required fields
                if not customer_data.get('name') or not customer_data.get('email'):
                    raise ValidationError("Name and email are required.")

                # Use a separate transaction for each customer to allow partial success
                with transaction.atomic():
                    new_customer = Customer.objects.create(
                        name=customer_data['name'],
                        email=customer_data['email'],
                        phone=customer_data.get('phone')
                    )
                    created_customers.append(new_customer)
            except IntegrityError as e:
                # Handle unique constraint violation for email
                errors.append(f"Failed to create customer '{customer_data.get('email')}': An account with this email already exists.")
            except ValidationError as e:
                # Handle validation errors
                errors.append(f"Failed to create customer '{customer_data.get('email')}': {e.message}")
            except Exception as e:
                # Catch all other exceptions
                errors.append(f"Failed to create customer '{customer_data.get('email')}': An unexpected error occurred.")

        return BulkCreateCustomers(customers=created_customers, errors=errors)


class CreateOrder(graphene.Mutation):
    """Mutation to create a new order with multiple products."""
    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.ID, required=True)

    order = graphene.Field(OrderType)

    @staticmethod
    def mutate(root, info, customer_id, product_ids):
        # Validation: Ensure at least one product is selected
        if not product_ids:
            raise ValidationError("Order must contain at least one product.")
        
        try:
            with transaction.atomic():
                # Fetch customer and products
                customer = Customer.objects.get(id=customer_id)
                products = Product.objects.filter(id__in=product_ids)

                # Validation: Check for invalid product IDs
                if len(products) != len(product_ids):
                    # Find which IDs were invalid
                    valid_ids = {str(p.id) for p in products}
                    invalid_ids = [id for id in product_ids if id not in valid_ids]
                    raise graphene.ValidationError(f"Invalid product ID(s) found: {', '.join(invalid_ids)}")

                # Create the order and set the products
                order = Order.objects.create(customer=customer)
                order.products.set(products)

                # Calculate total amount and update the order
                total_amount = sum(p.price for p in products)
                order.total_amount = total_amount
                order.save()
            
            return CreateOrder(order=order)
        except Customer.DoesNotExist:
            raise ValidationError(f"Customer with ID {customer_id} does not exist.")
        except Exception as e:
            raise ValidationError(f"An unexpected error occurred while creating the order: {e}")

class Query(graphene.ObjectType):
    # Old queries
    all_customers = DjangoFilterConnectionField(CustomerType)
    all_products = DjangoFilterConnectionField(ProductType)
    all_orders = DjangoFilterConnectionField(OrderType)
    
    # New queries with custom filters
    customers = DjangoFilterConnectionField(CustomerType,
        filterset_class=CustomerFilter,
        description="""
        Query customers with advanced filtering options.
        """
    )
    
    products = DjangoFilterConnectionField(ProductType,
        filterset_class=ProductFilter,
        description="""
        Query products with advanced filtering options.
        """
    )

    orders = DjangoFilterConnectionField(OrderType,
        filterset_class=OrderFilter,
        description="""
        Query orders with advanced filtering options.
        """
    )

    customer = graphene.Node.Field(CustomerType)
    product = graphene.Node.Field(ProductType)
    order = graphene.Node.Field(OrderType)

    # Added resolver for the customer_by_email field
    customer_by_email = graphene.Field(CustomerType, email=graphene.String())
    def resolve_customer_by_email(self, info, email):
        try:
            return Customer.objects.get(email=email)
        except Customer.DoesNotExist:
            return None


class Mutation(graphene.ObjectType):
    """The root Mutation for the listings app, exposing the CRM mutations."""
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
