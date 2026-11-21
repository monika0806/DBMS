import requests
from getpass import getpass
from config.db import get_db_connection

BASE_URL = "http://127.0.0.1:5000/api"

print("\n===== SHARESPACE REJECTION WORKFLOW =====")

# STUDENT LOGIN

student_email = input("\nStudent Email: ")
student_password = getpass("Student Password: ")

student_response = requests.post(
    f"{BASE_URL}/auth/login",
    json={
        "email": student_email,
        "password": student_password
    }
)

if student_response.status_code != 200:
    print("Student login failed:", student_response.json())
    exit()

student_token = student_response.json()["token"]
print("Student login successful!")


# ADMIN LOGIN

admin_email = input("\nAdmin Email: ")
admin_password = getpass("Admin Password: ")

admin_response = requests.post(
    f"{BASE_URL}/auth/login",
    json={
        "email": admin_email,
        "password": admin_password
    }
)

if admin_response.status_code != 200:
    print("Admin login failed:", admin_response.json())
    exit()

admin_token = admin_response.json()["token"]
print("Admin login successful!")


student_headers = {
    "Authorization": f"Bearer {student_token}"
}

admin_headers = {
    "Authorization": f"Bearer {admin_token}"
}


# FIND AVAILABLE RESOURCE

connection = get_db_connection()
cursor = connection.cursor(dictionary=True)

cursor.execute("""
    SELECT user_id
    FROM users
    WHERE email = %s
""", (student_email,))

student = cursor.fetchone()

if not student:
    print("Student not found!")
    cursor.close()
    connection.close()
    exit()

cursor.execute("""
    SELECT resource_id, resource_name
    FROM resources
    WHERE availability_status = 'Available'
      AND owner_id != %s
    LIMIT 1
""", (student["user_id"],))

resource = cursor.fetchone()

cursor.close()
connection.close()

if not resource:
    print("No available resources!")
    exit()

resource_id = resource["resource_id"]

print("\nSelected Resource:", resource["resource_name"])
print("Resource ID:", resource_id)


# CREATE BORROW REQUEST

print("\n===== CREATING BORROW REQUEST =====")

borrow_data = {
    "resource_id": resource_id,
    "start_date": "2026-11-20",
    "end_date": "2026-11-22"
}

response = requests.post(
    f"{BASE_URL}/borrow/requests",
    json=borrow_data,
    headers=student_headers
)

print("Status:", response.status_code)
print("Response:", response.json())

if response.status_code != 201:
    print("Borrow request failed!")
    exit()

request_id = response.json()["request_id"]


# REJECT REQUEST

print("\n===== ADMIN REJECTING REQUEST =====")

response = requests.put(
    f"{BASE_URL}/borrow/{request_id}/reject",
    headers=admin_headers
)

print("Status:", response.status_code)
print("Response:", response.json())

if response.status_code != 200:
    print("Rejection failed!")
    exit()


# VERIFY REQUEST

print("\n===== VERIFYING REQUEST =====")

response = requests.get(
    f"{BASE_URL}/borrow/my-requests",
    headers=student_headers
)

if response.status_code == 200:

    for item in response.json():

        if item["request_id"] == request_id:

            print("Request ID:", request_id)
            print("Final Status:", item["request_status"])

            if item["request_status"] == "Rejected":
                print("\nSUCCESS! REJECTION WORKFLOW WORKING!")
            else:
                print("\nRejection verification failed!")

else:
    print("Verification failed:", response.json())