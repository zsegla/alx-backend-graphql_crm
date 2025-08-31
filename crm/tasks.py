from celery import shared_task
from datetime import datetime
from django.db.models import Sum
import requests
from crm.models import Customer, Order  # adjust to your actual model names


@shared_task
def generate_crm_report():
    total_customers = Customer.objects.count()
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(total=Sum("totalamount"))["total"] or 0

    # Use datetime instead of Django timezone
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = f"{timestamp} - Report: {total_customers} customers, {total_orders} orders, {total_revenue} revenue\n"

    # Save to local file
    with open("/tmp/crm_report_log.txt", "a") as f:
        f.write(report)

    # Example: send the report to a webhook (adjust URL)
    try:
        requests.post(
            "http://localhost:8000/api/report-webhook/",  # replace with your endpoint
            json={"report": report},
            timeout=5
        )
    except requests.RequestException as e:
        with open("/tmp/crm_report_log.txt", "a") as f:
            f.write(f"Error sending report: {e}\n")

    return report