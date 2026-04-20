import os

import requests


base_url = os.environ.get("TEST_MEMBERSHIP_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
price_id = os.environ.get("TEST_MEMBERSHIP_PRICE_ID", "").strip()

if not price_id:
    raise SystemExit(
        "Falta TEST_MEMBERSHIP_PRICE_ID. Configura el Price ID de Stripe antes de ejecutar la prueba."
    )

url = f"{base_url}/billing/create-membership"
data = {
    "name": os.environ.get("TEST_MEMBERSHIP_NAME", "Juan Perez"),
    "email": os.environ.get("TEST_MEMBERSHIP_EMAIL", "juan.perez@example.com"),
    "price_id": price_id,
    "payment_method": os.environ.get("TEST_MEMBERSHIP_PAYMENT_METHOD", "pm_card_visa"),
}

customer_id = os.environ.get("TEST_MEMBERSHIP_CUSTOMER_ID", "").strip()
if customer_id:
    data["customer_id"] = customer_id

response = requests.post(url, json=data, timeout=30)
print("Status:", response.status_code)
try:
    print("Respuesta:", response.json())
except requests.exceptions.JSONDecodeError:
    print("Respuesta cruda:", response.text)
