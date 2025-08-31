import logging
import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

LOG_FILE = "/tmp/crm_heartbeat_log.txt"

def log_crm_heartbeat():
    """Log a heartbeat message and optionally verify GraphQL hello query."""
    timestamp = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    message = f"{timestamp} CRM is alive"

    try:
        # Optional: Verify GraphQL hello field
        transport = RequestsHTTPTransport(url="http://localhost:8000/graphql", verify=True, retries=3)
        client = Client(transport=transport, fetch_schema_from_transport=True)

        query = gql(""" query { hello } """)
        result = client.execute(query)
        hello_response = result.get("hello", "No response")
        message += f" | GraphQL hello: {hello_response}"

    except Exception as e:
        message += f" | GraphQL error: {e}"

    # Append to log file
    with open(LOG_FILE, "a") as f:
        f.write(message + "\n")

    # Also log via Django logger (optional)
    logger = logging.getLogger(__name__)
    logger.info(message)

def update_low_stock():
    # GraphQL endpoint (adjust port if needed)
    transport = RequestsHTTPTransport(
        url="http://127.0.0.1:8000/graphql/",
        verify=False,
        retries=3,
    )
    client = Client(transport=transport, fetch_schema_from_transport=True)

    mutation = gql("""
    mutation {
        updateLowStockProducts {
            success
            message
            updatedProducts {
                id
                name
                stock
            }
        }
    }
    """)

    response = client.execute(mutation)

    # Log results to file
    with open("/tmp/low_stock_updates_log.txt", "a") as f:
        f.write(f"{datetime.datetime.now()} - {response}\n")