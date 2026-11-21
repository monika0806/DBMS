
from flask import Blueprint, request, jsonify
from config.db import get_db_connection
from utils.auth_middleware import admin_required

admin_bp = Blueprint("admin", __name__)


# ---------------- GET ALL STUDENTS ----------------

@admin_bp.route("/users", methods=["GET"])
@admin_required
def get_students():

    connection = get_db_connection()

    if not connection:
        return jsonify({
            "message": "Database connection failed"
        }), 500

    cursor = connection.cursor(dictionary=True)

    try:
        search = request.args.get("search", "").strip()

        query = """
            SELECT
                user_id,
                full_name,
                email,
                phone,
                department,
                created_at
            FROM users
            WHERE role = 'student'
        """

        params = []

        if search:
            query += """
                AND (
                    full_name LIKE %s
                    OR email LIKE %s
                    OR department LIKE %s
                )
            """
            search_value = f"%{search}%"
            params.extend([
                search_value,
                search_value,
                search_value
            ])

        query += " ORDER BY created_at DESC"

        cursor.execute(query, tuple(params))
        students = cursor.fetchall()

        return jsonify({
            "message": "Students fetched successfully",
            "total": len(students),
            "users": students
        }), 200

    except Exception as e:
        print("Get students error:", e)

        return jsonify({
            "message": "Unable to fetch students"
        }), 500

    finally:
        cursor.close()
        connection.close()
