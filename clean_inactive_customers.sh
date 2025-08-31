#!/bin/bash

# Navigate to the Django project root (adjust path if needed)
cd "$(dirname "$0")/.."

# Run Django shell command to delete inactive customers and capture output
deleted_count=$(python3 manage.py shell -c "
import datetime
from crm.models import Customer
from django.utils import timezone

one_year_ago = timezone.now() - datetime.timedelta(days=365)
inactive_customers = Customer.objects.filter(order__isnull=True) | Customer.objects.exclude(order__created_at__gte=one_year_ago)
inactive_customers = inactive_customers.distinct()
count = inactive_customers.count()
inactive_customers.delete()
print(count)
" 2>/dev/null)

# Log the result with timestamp
echo \"[\$(date '+%Y-%m-%d %H:%M:%S')] Deleted \$deleted_count inactive customers\" >> /tmp/customer_cleanup_log.txt