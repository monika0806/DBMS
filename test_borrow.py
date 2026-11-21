import requests

BASE_URL = "http://127.0.0.1:5000"

# Login
login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={
        "email": "rahul_test@gmail.com",
        "password": input("Enter your password: ")
    }
)

print("LOGIN STATUS:", login_response.status_code)

if login_response.status_code != 200:
    print(login_response.text)
    exit()

token = login_response.json()["token"]

headers = {
    "Authorization": f"Bearer {token}"
}

# Submit borrow request
response = requests.post(
    f"{BASE_URL}/api/borrow/requests",
    headers=headers,
    json={
        "resource_id": 1,
        "start_date": "2026-11-20",
        "end_date": "2026-11-27"
    }
)

print("\n===== BORROW REQUEST RESULT =====")
print("Status:", response.status_code)
print(response.json())