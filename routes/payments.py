
from flask import Blueprint, jsonify, request
from config.db import get_db_connection
from utils.auth_middleware import token_required, admin_required

payments_bp = Blueprint("payments", __name__)


# -----------------------------------------
# STUDENT: CREATE A PAYMENT RECORD
# -----------------------------------------

@payments_bp.route("/fine/<int:fine_id>", methods=["POST"])
@token_required
def create_payment(fine_id):

    data = request.get_json(silent=True) or {}
    payment_method = (data.get("payment_method") or "").strip()

    if not payment_method:
        return jsonify({"message": "Payment method is required"}), 400

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        user_id = request.user["user_id"]

        connection.start_transaction()

        cursor.execute("""
            SELECT f.fine_id, f.fine_amount, f.payment_status
            FROM fines f
            JOIN loans l ON f.loan_id = l.loan_id
            JOIN borrow_requests br ON l.request_id = br.request_id
            WHERE f.fine_id = %s AND br.borrower_id = %s
            FOR UPDATE
        """, (fine_id, user_id))

        fine = cursor.fetchone()

        if not fine:
            connection.rollback()
            return jsonify({"message": "Fine not found"}), 404

        if fine["payment_status"] == "Paid":
            connection.rollback()
            return jsonify({"message": "This fine has already been paid"}), 400

        cursor.execute("""
            SELECT payment_id
            FROM payments
            WHERE fine_id = %s AND payment_status = 'Pending'
            LIMIT 1
        """, (fine_id,))

        existing_payment = cursor.fetchone()

        if existing_payment:
            connection.rollback()
            return jsonify({
                "message": "A pending payment already exists for this fine",
                "payment_id": existing_payment["payment_id"]
            }), 409

        cursor.execute("""
            INSERT INTO payments
                (fine_id, amount, payment_method, payment_status)
            VALUES (%s, %s, %s, 'Pending')
        """, (
            fine_id,
            fine["fine_amount"],
            payment_method
        ))

        payment_id = cursor.lastrowid

        connection.commit()

        return jsonify({
            "message": "Payment record created. Payment is still pending confirmation.",
            "payment_id": payment_id,
            "fine_id": fine_id,
            "amount": float(fine["fine_amount"]),
            "payment_status": "Pending"
        }), 201

    except Exception as e:
        connection.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()


# -----------------------------------------
# STUDENT: VIEW OWN PAYMENT HISTORY
# -----------------------------------------

@payments_bp.route("/my", methods=["GET"])
@token_required
def get_my_payments():

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        user_id = request.user["user_id"]

        cursor.execute("""
            SELECT
                p.payment_id,
                p.fine_id,
                p.amount,
                p.payment_method,
                p.payment_date,
                p.payment_status,
                f.loan_id,
                r.resource_name
            FROM payments p
            JOIN fines f ON p.fine_id = f.fine_id
            JOIN loans l ON f.loan_id = l.loan_id
            JOIN borrow_requests br ON l.request_id = br.request_id
            JOIN resources r ON br.resource_id = r.resource_id
            WHERE br.borrower_id = %s
            ORDER BY p.payment_id DESC
        """, (user_id,))

        payments = cursor.fetchall()

        return jsonify({
            "total": len(payments),
            "payments": payments
        }), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()


# -----------------------------------------
# ADMIN: VIEW ALL PAYMENTS
# -----------------------------------------

@payments_bp.route("/admin/all", methods=["GET"])
@admin_required
def get_all_payments():

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                p.payment_id,
                p.fine_id,
                p.amount,
                p.payment_method,
                p.payment_date,
                p.payment_status,
                f.loan_id,
                u.full_name,
                u.email,
                r.resource_name
            FROM payments p
            JOIN fines f ON p.fine_id = f.fine_id
            JOIN loans l ON f.loan_id = l.loan_id
            JOIN borrow_requests br ON l.request_id = br.request_id
            JOIN users u ON br.borrower_id = u.user_id
            JOIN resources r ON br.resource_id = r.resource_id
            ORDER BY p.payment_id DESC
        """)

        payments = cursor.fetchall()

        return jsonify({
            "total": len(payments),
            "payments": payments
        }), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()


# -----------------------------------------
# ADMIN: UPDATE PAYMENT STATUS
# -----------------------------------------

@payments_bp.route("/<int:payment_id>/status", methods=["PUT"])
@admin_required
def update_payment_status(payment_id):

    data = request.get_json(silent=True) or {}
    new_status = data.get("payment_status")

    if new_status not in ["Successful", "Failed"]:
        return jsonify({
            "message": "Status must be Successful or Failed"
        }), 400

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        connection.start_transaction()

        cursor.execute("""
            SELECT payment_id, fine_id, payment_status
            FROM payments
            WHERE payment_id = %s
            FOR UPDATE
        """, (payment_id,))

        payment = cursor.fetchone()

        if not payment:
            connection.rollback()
            return jsonify({"message": "Payment not found"}), 404

        if payment["payment_status"] != "Pending":
            connection.rollback()
            return jsonify({
                "message": "Only pending payments can be updated"
            }), 400

        cursor.execute("""
            UPDATE payments
            SET payment_status = %s
            WHERE payment_id = %s
        """, (new_status, payment_id))

        if new_status == "Successful":
            cursor.execute("""
                UPDATE fines
                SET payment_status = 'Paid'
                WHERE fine_id = %s
            """, (payment["fine_id"],))

        connection.commit()

        return jsonify({
            "message": "Payment status updated successfully",
            "payment_id": payment_id,
            "payment_status": new_status
        }), 200

    except Exception as e:
        connection.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()
