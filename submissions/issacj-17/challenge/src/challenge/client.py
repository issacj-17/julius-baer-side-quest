# Python 3 + httpx version
import httpx
from typing import Optional


def transfer_money(from_acc: str, to_acc: str, amount: float) -> Optional[str]:
    url = "http://localhost:8123/transfer"
    payload = {"fromAccount": from_acc, "toAccount": to_acc, "amount": amount}

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            result = resp.text  # or resp.json() if server returns JSON object
            print(f"Transfer result: {result}")
            return result
    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code} {e.response.text[:200]}")
    except httpx.RequestError as e:
        # Network issues, DNS errors, timeouts, connection refused, etc.
        print(f"Request error: {e}")
    return None


if __name__ == "__main__":
    transfer_money("ACC1000", "ACC1001", 100.00)
