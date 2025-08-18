import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "alx_backend_graphql_crm.settings")
django.setup()

from crm.models import Customer, Product

# Sample seed data
Customer.objects.create(name="Daniel Abdul", email="dan_abdul@gmail.com", phone="+2349023768712")
Product.objects.create(name="iPhone", price=450, stock=50)
Product.objects.create(name="Tablet", price=750.5, stock=30)

print("Database seeded successfully!")