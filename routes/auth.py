from flask import Blueprint, request, jsonify
from config.db import get_db_connection
from flask_bcrypt import Bcrypt
from utils.auth_middleware import token_required
import jwt
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

auth_bp = Blueprint("auth", __name__)

bcrypt = Bcrypt()


# ---------------- REGISTER ----------------

@auth_bp.route("/register", methods=["POST"])
def register():

    data = request.get_json()

    full_name = data.get("full_name")
    email = data.get("email")
    password = data.get("password")
    phone = data.get("phone")
    department = data.get("department")

    if not all([full_name, email, password]):
        return jsonify({
            "message": "Name, email and password are required"
        }), 400

    if len(password) < 8:
        return jsonify({
            "message": "Password must contain at least 8 characters"
        }), 400

    connection = get_db_connection()

    if not connection:
        return jsonify({
            "message": "Database connection failed"
        }), 500

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            "SELECT user_id FROM users WHERE email = %s",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:
            return jsonify({
                "message": "Email already registered"
            }), 409

        hashed_password = bcrypt.generate_password_hash(
            password
        ).decode("utf-8")

        query = """
            INSERT INTO users
            (full_name, email, password, phone, department, role)
            VALUES (%s, %s, %s, %s, %s, 'student')
        """

        cursor.execute(query, (
            full_name,
            email,
            hashed_password,
            phone,
            department
        ))

        connection.commit()

        return jsonify({
            "message": "Registration successful",
            "user_id": cursor.lastrowid
        }), 201

    except Exception as e:

        connection.rollback()

        return jsonify({
            "message": str(e)
        }), 500

    finally:

        cursor.close()
        connection.close()


# ---------------- LOGIN HELPERS ----------------

def _login_for_role(required_role):
    """Authenticate a user only when their database role matches the portal."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({
            "message": "Email and password are required"
        }), 400

    connection = get_db_connection()
    if not connection:
        return jsonify({
            "message": "Database connection failed"
        }), 500

    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT user_id, full_name, email, password, role FROM users WHERE email = %s",
            (email,)
        )
        user = cursor.fetchone()

        # Keep the response generic so the endpoint does not reveal whether an
        # email exists or belongs to a different portal.
        if not user or not bcrypt.check_password_hash(user["password"], password):
            return jsonify({
                "message": "Invalid email or password"
            }), 401

        if user["role"] != required_role:
            message = (
                "This account is not authorized for the administrator portal."
                if required_role == "admin"
                else "Administrator accounts must use the administrator login."
            )
            return jsonify({"message": message}), 403

        jwt_secret = os.getenv("JWT_SECRET")
        if not jwt_secret:
            return jsonify({
                "message": "Authentication service is not configured"
            }), 500

        token = jwt.encode({
            "user_id": user["user_id"],
            "email": user["email"],
            "role": user["role"],
            "exp": datetime.datetime.now(
                datetime.timezone.utc
            ) + datetime.timedelta(hours=24)
        }, jwt_secret, algorithm="HS256")

        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {
                "user_id": user["user_id"],
                "full_name": user["full_name"],
                "email": user["email"],
                "role": user["role"]
            }
        }), 200

    finally:
        cursor.close()
        connection.close()


# ---------------- STUDENT LOGIN ----------------

@auth_bp.route("/login", methods=["POST"])
def login():
    return _login_for_role("student")


# ---------------- ADMIN LOGIN ----------------

@auth_bp.route("/admin/login", methods=["POST"])
def admin_login():
    return _login_for_role("admin")


# ---------------- STUDENT PROFILE ----------------

@auth_bp.route("/profile", methods=["GET"])
@token_required
def get_profile():

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        user_id = request.user["user_id"]

        cursor.execute("""
            SELECT user_id, full_name, email, phone, department, role
            FROM users
            WHERE user_id = %s
        """, (user_id,))

        user = cursor.fetchone()

        if not user:
            return jsonify({"message": "User not found"}), 404

        return jsonify({
            "message": "Profile fetched successfully",
            "user": user
        }), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()


@auth_bp.route("/profile", methods=["PUT"])
@token_required
def update_profile():

    data = request.get_json(silent=True) or {}

    full_name = (data.get("full_name") or "").strip()
    phone = (data.get("phone") or "").strip() or None
    department = (data.get("department") or "").strip() or None

    if not full_name:
        return jsonify({"message": "Full name is required"}), 400

    if len(full_name) > 100:
        return jsonify({"message": "Full name is too long"}), 400

    if phone and len(phone) > 15:
        return jsonify({"message": "Phone number is too long"}), 400

    if department and len(department) > 100:
        return jsonify({"message": "Department name is too long"}), 400

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        user_id = request.user["user_id"]

        cursor.execute("""
            UPDATE users
            SET full_name = %s,
                phone = %s,
                department = %s
            WHERE user_id = %s
        """, (full_name, phone, department, user_id))

        connection.commit()

        cursor.execute("""
            SELECT user_id, full_name, email, phone, department, role
            FROM users
            WHERE user_id = %s
        """, (user_id,))

        user = cursor.fetchone()

        return jsonify({
            "message": "Profile updated successfully",
            "user": user
        }), 200

    except Exception as e:
        connection.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

