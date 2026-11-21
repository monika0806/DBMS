
from flask import Blueprint, jsonify, request
from config.db import get_db_connection
from utils.auth_middleware import token_required, admin_required

fines_bp = Blueprint("fines", __name__)


# -----------------------------------------
# STUDENT: VIEW OWN FINES
# -----------------------------------------

@fines_bp.route("/my", methods=["GET"])
@token_required
def get_my_fines():

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        user_id = request.user["user_id"]

        cursor.execute("""
            SELECT
                f.fine_id,
                f.loan_id,
                f.late_days,
                f.fine_amount,
                f.payment_status,
                f.created_at,
                r.resource_name,
                l.due_date,
                ret.actual_return_date
            FROM fines f
            JOIN loans l ON f.loan_id = l.loan_id
            JOIN borrow_requests br ON l.request_id = br.request_id
            JOIN resources r ON br.resource_id = r.resource_id
            LEFT JOIN returns ret ON l.loan_id = ret.loan_id
            WHERE br.borrower_id = %s
            ORDER BY f.fine_id DESC
        """, (user_id,))

        fines = cursor.fetchall()

        total_pending = sum(
            float(f["fine_amount"])
            for f in fines
            if f["payment_status"] == "Pending"
        )

        total_paid = sum(
            float(f["fine_amount"])
            for f in fines
            if f["payment_status"] == "Paid"
        )

        return jsonify({
            "fines": fines,
            "total_pending": total_pending,
            "total_paid": total_paid
        }), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()


# -----------------------------------------
# ADMIN: VIEW ALL FINES
# -----------------------------------------

@fines_bp.route("/admin/all", methods=["GET"])
@admin_required
def get_all_fines():

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                f.fine_id,
                f.loan_id,
                f.late_days,
                f.fine_amount,
                f.payment_status,
                f.created_at,
                u.full_name,
                u.email,
                r.resource_name,
                l.due_date,
                ret.actual_return_date
            FROM fines f
            JOIN loans l ON f.loan_id = l.loan_id
            JOIN borrow_requests br ON l.request_id = br.request_id
            JOIN users u ON br.borrower_id = u.user_id
            JOIN resources r ON br.resource_id = r.resource_id
            LEFT JOIN returns ret ON l.loan_id = ret.loan_id
            ORDER BY f.fine_id DESC
        """)

        fines = cursor.fetchall()

        return jsonify({
            "total": len(fines),
            "fines": fines
        }), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()
