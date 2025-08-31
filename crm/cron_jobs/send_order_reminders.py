#!/usr/bin/env python3
import sys
import logging
from datetime import datetime, timedelta
import asyncio
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

# Configure logging
logging.basicConfig(
    filename="/tmp/order_reminders_log.txt",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)

# GraphQL endpoint
GRAPHQL_URL = "http://localhost:8000/graphql"

# Query orders placed within the last 7 days
query = gql("""
    query GetRecentOrders($cutoff: DateTime!) {
        orders(filter: { orderDate_Gte: $cutoff, status: "PENDING" }) {
            id
            customer {
                email
                phone
                name
            }
        }
    }
""")

async def main():
    # Compute cutoff date
    cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()

    # Setup GraphQL transport
    transport = RequestsHTTPTransport(url=GRAPHQL_URL, verify=True, retries=3)
    client = Client(transport=transport, fetch_schema_from_transport=True)

    try:
        result = await client.execute_async(query, variable_values={"cutoff": cutoff_date})
        orders = result.get("orders", [])

        for order in orders:
            order_id = order.get("id")
            customer_email = order.get("customer", {}).get("email", "unknown")
            logging.info(f"Reminder: Order {order_id} for customer {customer_email}")

        print("Order reminders processed!")

    except Exception as e:
        logging.error(f"Error fetching orders: {e}")
        print(f"Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    asyncio.run(main())