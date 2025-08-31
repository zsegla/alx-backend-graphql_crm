#!/bin/bash

# Navigate to project root (adjust if needed)
cd "$(dirname "$0")/../.." || exit 1

# Run Django shell command to delete inactive customers
deleted_count=$(python manage.py shell -c "
from datetime import timedelta
from django.utils.timezone import now
from django.db.models import Max
from crm.models import Customer

cutoff = now() - timedelta(days=365)

# Customers with last order older than cutoff OR never ordered
inactive_customers = Customer.objects.annotate(
    last_order_date=Max('orders__created_at')
).filter(
    last_order_date__lt=cutoff
) | Customer.objects.filter(orders__isnull=True)

count = inactive_customers.count()
inactive_customers.delete()
print(count)
")

# Log result with timestamp
echo "$(date '+%Y-%m-%d %H:%M:%S') - Deleted customers: $deleted_count" >> /tmp/customer_cleanup_log.txt