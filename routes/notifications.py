
from flask import Blueprint, jsonify, request
from config.db import get_db_connection
from utils.auth_middleware import token_required, admin_required

notifications_bp = Blueprint("notifications", __name__)


# -------------------------------------------------
# 1. STUDENT: VIEW OWN NOTIFICATIONS
# -------------------------------------------------

@notifications_bp.route("/my", methods=["GET"])
@token_required
def get_my_notifications():

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                notification_id,
                message,
                is_read,
                created_at
            FROM notifications
            WHERE user_id = %s
            ORDER BY created_at DESC
        """, (request.user["user_id"],))

        notifications = cursor.fetchall()

        return jsonify({
            "total": len(notifications),
            "notifications": notifications
        }), 200

    except Exception as e:
        print("My notifications error:", e)
        return jsonify({"message": "Unable to fetch notifications"}), 500

    finally:
        cursor.close()
        connection.close()


# -------------------------------------------------
# 2. ADMIN: VIEW ALL STUDENT NOTIFICATIONS
# -------------------------------------------------

@notifications_bp.route("/admin/all", methods=["GET"])
@admin_required
def get_all_notifications():

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                n.notification_id,
                n.user_id,
                u.full_name,
                u.email,
                n.message,
                n.is_read,
                n.created_at
            FROM notifications n
            JOIN users u ON n.user_id = u.user_id
            WHERE u.role = 'student'
            ORDER BY n.created_at DESC
        """)

        notifications = cursor.fetchall()

        return jsonify({
            "total": len(notifications),
            "notifications": notifications
        }), 200

    except Exception as e:
        print("Admin notifications error:", e)
        return jsonify({"message": "Unable to fetch notifications"}), 500

    finally:
        cursor.close()
        connection.close()


# -------------------------------------------------
# 3. STUDENT: MARK OWN NOTIFICATION AS READ
# -------------------------------------------------

@notifications_bp.route("/<int:notification_id>/read", methods=["PUT"])
@token_required
def mark_notification_read(notification_id):

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            UPDATE notifications
            SET is_read = 1
            WHERE notification_id = %s
              AND user_id = %s
        """, (
            notification_id,
            request.user["user_id"]
        ))

        if cursor.rowcount == 0:
            connection.rollback()
            return jsonify({
                "message": "Notification not found"
            }), 404

        connection.commit()

        return jsonify({
            "message": "Notification marked as read"
        }), 200

    except Exception as e:
        connection.rollback()
        print("Mark notification read error:", e)
        return jsonify({"message": "Unable to update notification"}), 500

    finally:
        cursor.close()
        connection.close()


# -------------------------------------------------
# 4. ADMIN: DELETE A NOTIFICATION
# -------------------------------------------------

@notifications_bp.route("/admin/<int:notification_id>", methods=["DELETE"])
@admin_required
def delete_notification(notification_id):

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor()

    try:
        cursor.execute("""
            DELETE FROM notifications
            WHERE notification_id = %s
        """, (notification_id,))

        if cursor.rowcount == 0:
            connection.rollback()
            return jsonify({"message": "Notification not found"}), 404

        connection.commit()

        return jsonify({
            "message": "Notification deleted successfully"
        }), 200

    except Exception as e:
        connection.rollback()
        print("Delete notification error:", e)
        return jsonify({"message": "Unable to delete notification"}), 500

    finally:
        cursor.close()
        connection.close()
