import json
import urllib.request
import urllib.error
from getpass import getpass

def register_student():

    print("\n===== SHARESPACE REGISTRATION =====\n")

    name = input("Full Name: ").strip()
    email = input("Email: ").strip()
    password = getpass("Password: ")
    phone = input("Phone: ").strip()
    department = input("Department: ").strip()

    if not all([name, email, password]):
        print("Name, email and password are required.")
        return

    student_data = {
        "full_name": name,
        "email": email,
        "password": password,
        "phone": phone,
        "department": department
    }

    api_url = "http://127.0.0.1:5000/api/auth/register"

    request = urllib.request.Request(
        api_url,
        data=json.dumps(student_data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request) as response:

            result = json.loads(response.read().decode())

            print("\nRegistration Successful!")
            print("Status:", response.status)
            print("Response:", result)

    except urllib.error.HTTPError as error:

        result = error.read().decode()

        print("\nRegistration Failed!")
        print("Status:", error.code)
        print("Response:", result)

    except urllib.error.URLError as error:

        print("\nCannot connect to Flask server.")
        print("Error:", error.reason)


if __name__ == "__main__":
    register_student()
    