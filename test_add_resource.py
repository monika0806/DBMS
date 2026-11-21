import requests
from getpass import getpass

BASE_URL = "http://127.0.0.1:5000"

print("\n===== SHARESPACE RESOURCE TEST =====")

# Login
email = input("Email: ")
password = getpass("Password: ")

login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={
        "email": email,
        "password": password
    }
)

if login_response.status_code != 200:
    print("Login failed:", login_response.json())
    raise SystemExit

token = login_response.json()["token"]

print("\nLogin successful!")

# Add resource
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}

resource = {
    "resource_name": "Python Programming Book",
    "category_id": 1,
    "description": "Introduction to Python programming",
    "condition_status": "Good",
    "rental_price": 0
}

response = requests.post(
    f"{BASE_URL}/api/resources/",
    json=resource,
    headers=headers
)

print("\n===== RESOURCE RESPONSE =====")
print("Status:", response.status_code)
print("Response:", response.json())