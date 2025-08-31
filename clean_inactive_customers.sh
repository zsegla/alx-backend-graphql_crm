#!/bin/bash

# Navigate to the Django project root (adjust path if needed)
PROJECT_DIR="$(dirname "$(dirname "$(realpath "$0")")")"
cd "$PROJECT_DIR" || exit 1

# Run Django shell command to delete inactive customers (no orders in the last year)
DELETED_COUNT=$(echo "
from django.utils import timezone
from datetime import timedelta
from crm.models import Customer

one_year_ago = timezone.now() - timedelta(days=365)
qs = Customer.objects.filter(orders__isnull=True, created_at__lt=one_year_ago)
count = qs.count()
qs.delete()
print(count)
" | python3 manage.py shell 2>/dev/null)

# Log output with timestamp
echo \"$(date '+%Y-%m-%d %H:%M:%S') - Deleted customers: $DELETED_COUNT\" >> /tmp/customer_cleanup_log.txt
