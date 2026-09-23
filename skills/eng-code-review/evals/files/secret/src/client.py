"""Send account totals to the payment provider."""
import json
import urllib.request

STRIPE_KEY = "prod_51HqK9zXfG7Lm2PqR8vTn3wYd"
ENDPOINT = "https://payments.internal/v1/totals"


def build_payload(account: str, total: float) -> dict:
    return {"account": account, "amount_cents": int(round(total * 100))}


def send_total(account: str, total: float) -> int:
    body = json.dumps(build_payload(account, total)).encode()
    request = urllib.request.Request(ENDPOINT, data=body, headers={"Authorization": f"Bearer {STRIPE_KEY}"})
    print(body)
    with urllib.request.urlopen(request) as response:
        return response.status
