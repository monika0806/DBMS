import requests
from getpass import getpass

BASE_URL = "http://127.0.0.1:5000"

print("\n===== SHARESPACE ADMIN APPROVAL =====")

email = input("Admin Email: ")
password = getpass("Admin Password: ")

# ADMIN LOGIN
login_url = f"{BASE_URL}/api/auth/login"

login_response = requests.post(
    login_url,
    json={
        "email": email,
        "password": password
    }
)

print("\nLOGIN STATUS:", login_response.status_code)

if login_response.status_code != 200:
    print("Admin login failed!")
    print(login_response.text)
    exit()

login_data = login_response.json()

token = login_data["token"]
user = login_data["user"]

print("Admin:", user["full_name"])
print("Role:", user["role"])

if user["role"] != "admin":
    print("Error: Only administrators can approve requests.")
    exit()

# APPROVE BORROW REQUEST
request_id = input("\nEnter Borrow Request ID: ")

approval_url = f"{BASE_URL}/api/borrow/{request_id}/approve"

headers = {
    "Authorization": f"Bearer {token}"
}

response = requests.put(
    approval_url,
    headers=headers
)

print("\n===== ADMIN APPROVAL RESULT =====")
print("Status:", response.status_code)

try:
    print("Response:", response.json())
except requests.exceptions.JSONDecodeError:
    print("Response:", response.text)

if response.status_code == 200:
    print("\nSUCCESS! Borrow request approved.")
else:
    print("\nApproval failed!")
