import requests
from getpass import getpass

print("\n===== SHARESPACE LOGIN =====")

email = input("Email: ")
password = getpass("Password: ")

url = "http://127.0.0.1:5000/api/auth/login"

payload = {
    "email": email,
    "password": password
}

try:

    response = requests.post(url, json=payload)

    print("\n===== LOGIN RESPONSE =====")
    print("Status:", response.status_code)
    print("Response:", response.json())

    if response.status_code == 200:

        data = response.json()

        print("\nLOGIN SUCCESSFUL!")
        print("User:", data["user"]["full_name"])
        print("Role:", data["user"]["role"])
        print("JWT Token received successfully!")

    else:

        print("\nLOGIN FAILED!")

except requests.exceptions.ConnectionError:

    print("Could not connect to ShareSpace server.")