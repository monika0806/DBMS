from flask import Blueprint, request, jsonify
from config.db import get_db_connection
from utils.auth_middleware import token_required, admin_required

from datetime import date

borrow_bp = Blueprint("borrow", __name__)


# -------------------------------------------------
# 1. STUDENT: SUBMIT BORROW REQUEST
# -------------------------------------------------

@borrow_bp.route("/requests", methods=["POST"])
@token_required
def create_borrow_request():

    data = request.get_json(silent=True) or {}

    resource_id = data.get("resource_id")
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    if not all([resource_id, start_date, end_date]):
        return jsonify({
            "message": "Resource ID, start date and end date are required"
        }), 400

    if request.user.get("role") != "student":
        return jsonify({
            "message": "Only students can submit borrow requests"
        }), 403

    try:
        resource_id = int(resource_id)
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)

    except (ValueError, TypeError):
        return jsonify({
            "message": "Invalid resource ID or date format. Use YYYY-MM-DD."
        }), 400

    if start < date.today():
        return jsonify({
            "message": "Start date cannot be in the past"
        }), 400

    if end < start:
        return jsonify({
            "message": "End date cannot be before start date"
        }), 400

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:

        connection.start_transaction()

        # Lock resource to prevent simultaneous conflicting operations
        cursor.execute("""
            SELECT *
            FROM resources
            WHERE resource_id = %s
            FOR UPDATE
        """, (resource_id,))

        resource = cursor.fetchone()

        if not resource:
            connection.rollback()
            return jsonify({"message": "Resource not found"}), 404

        if resource["owner_id"] == request.user["user_id"]:
            connection.rollback()
            return jsonify({
                "message": "You cannot borrow your own resource"
            }), 400

        if resource["availability_status"] != "Available":
            connection.rollback()
            return jsonify({
                "message": "This resource is currently unavailable"
            }), 409

        # Check existing pending or approved request from same student
        cursor.execute("""
            SELECT request_id
            FROM borrow_requests
            WHERE resource_id = %s
              AND borrower_id = %s
              AND request_status IN ('Pending', 'Approved')
        """, (
            resource_id,
            request.user["user_id"]
        ))

        existing_request = cursor.fetchone()

        if existing_request:
            connection.rollback()
            return jsonify({
                "message": "You already have a pending or approved request for this resource"
            }), 409

        # Check for overlapping active loans
        cursor.execute("""
            SELECT l.loan_id
            FROM loans l
            JOIN borrow_requests br
                ON l.request_id = br.request_id
            WHERE br.resource_id = %s
              AND l.loan_status IN ('Active', 'Overdue')
              AND br.start_date <= %s
              AND br.end_date >= %s
        """, (
            resource_id,
            end,
            start
        ))

        conflicting_loan = cursor.fetchone()

        if conflicting_loan:
            connection.rollback()
            return jsonify({
                "message": "Resource is already booked for the selected dates"
            }), 409

        cursor.execute("""
            INSERT INTO borrow_requests
            (
                resource_id,
                borrower_id,
                start_date,
                end_date,
                request_status
            )
            VALUES (%s, %s, %s, %s, 'Pending')
        """, (
            resource_id,
            request.user["user_id"],
            start,
            end
        ))

        request_id = cursor.lastrowid

        connection.commit()

        return jsonify({
            "message": "Borrow request submitted successfully",
            "request_id": request_id,
            "status": "Pending"
        }), 201

    except Exception as e:

        connection.rollback()
        print("Borrow request error:", e)

        return jsonify({
            "message": "Unable to submit borrow request"
        }), 500

    finally:
        cursor.close()
        connection.close()


# -------------------------------------------------
# 2. STUDENT: VIEW MY BORROW REQUESTS
# -------------------------------------------------

@borrow_bp.route("/my-requests", methods=["GET"])
@token_required
def get_my_requests():

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                br.request_id,
                br.resource_id,
                r.resource_name,
                r.resource_image,
                br.start_date,
                br.end_date,
                br.request_date,
                br.request_status
            FROM borrow_requests br
            JOIN resources r
                ON br.resource_id = r.resource_id
            WHERE br.borrower_id = %s
            ORDER BY br.request_date DESC
        """, (request.user["user_id"],))

        requests = cursor.fetchall()

        return jsonify(requests), 200

    except Exception as e:

        print("My requests error:", e)

        return jsonify({
            "message": "Unable to retrieve borrow requests"
        }), 500

    finally:
        cursor.close()
        connection.close()


# -------------------------------------------------
# 3. ADMIN: VIEW ALL BORROW REQUESTS
# -------------------------------------------------

@borrow_bp.route("/all", methods=["GET"])
@admin_required
def get_all_requests():

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                br.request_id,
                br.resource_id,
                r.resource_name,
                br.borrower_id,
                u.full_name AS borrower_name,
                u.email AS borrower_email,
                br.start_date,
                br.end_date,
                br.request_date,
                br.request_status
            FROM borrow_requests br
            JOIN resources r
                ON br.resource_id = r.resource_id
            JOIN users u
                ON br.borrower_id = u.user_id
            ORDER BY br.request_date DESC
        """)

        requests = cursor.fetchall()

        return jsonify(requests), 200

    except Exception as e:

        print("All requests error:", e)

        return jsonify({
            "message": "Unable to retrieve requests"
        }), 500

    finally:
        cursor.close()
        connection.close()


# -------------------------------------------------
# 4. ADMIN: APPROVE BORROW REQUEST
# -------------------------------------------------

@borrow_bp.route("/<int:request_id>/approve", methods=["PUT"])
@admin_required
def approve_request(request_id):

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:

        connection.start_transaction()

        cursor.execute("""
            SELECT *
            FROM borrow_requests
            WHERE request_id = %s
            FOR UPDATE
        """, (request_id,))

        borrow_request = cursor.fetchone()

        if not borrow_request:
            connection.rollback()
            return jsonify({"message": "Request not found"}), 404

        if borrow_request["request_status"] != "Pending":
            connection.rollback()
            return jsonify({
                "message": "Only pending requests can be approved"
            }), 409

        # Lock resource
        cursor.execute("""
            SELECT *
            FROM resources
            WHERE resource_id = %s
            FOR UPDATE
        """, (borrow_request["resource_id"],))

        resource = cursor.fetchone()

        if not resource:
            connection.rollback()
            return jsonify({"message": "Resource not found"}), 404

        if resource["availability_status"] != "Available":
            connection.rollback()
            return jsonify({
                "message": "Resource is no longer available"
            }), 409

        # Check overlapping active loans
        cursor.execute("""
            SELECT l.loan_id
            FROM loans l
            JOIN borrow_requests br
                ON l.request_id = br.request_id
            WHERE br.resource_id = %s
              AND l.loan_status IN ('Active', 'Overdue')
              AND br.start_date <= %s
              AND br.end_date >= %s
            FOR UPDATE
        """, (
            borrow_request["resource_id"],
            borrow_request["end_date"],
            borrow_request["start_date"]
        ))

        if cursor.fetchone():
            connection.rollback()
            return jsonify({
                "message": "Another active loan conflicts with these dates"
            }), 409

        # Create loan record
        cursor.execute("""
            INSERT INTO loans
            (
                request_id,
                issue_date,
                due_date,
                loan_status
            )
            VALUES (%s, %s, %s, 'Active')
        """, (
            request_id,
            borrow_request["start_date"],
            borrow_request["end_date"]
        ))

        loan_id = cursor.lastrowid

        # Update request status
        cursor.execute("""
            UPDATE borrow_requests
            SET request_status = 'Approved'
            WHERE request_id = %s
        """, (request_id,))

        # Mark resource as borrowed
        cursor.execute("""
            UPDATE resources
            SET availability_status = 'Borrowed'
            WHERE resource_id = %s
        """, (borrow_request["resource_id"],))

        # Notify student
        cursor.execute("""
            INSERT INTO notifications (user_id, message)
            VALUES (%s, %s)
        """, (
            borrow_request["borrower_id"],
            f"Your borrow request #{request_id} has been approved."
        ))

        connection.commit()

        return jsonify({
            "message": "Borrow request approved successfully",
            "request_id": request_id,
            "loan_id": loan_id,
            "status": "Approved"
        }), 200

    except Exception as e:

        connection.rollback()
        print("Approval error:", e)

        return jsonify({
            "message": "Unable to approve borrow request"
        }), 500

    finally:
        cursor.close()
        connection.close()


# -------------------------------------------------
# 5. ADMIN: REJECT BORROW REQUEST
# -------------------------------------------------

@borrow_bp.route("/<int:request_id>/reject", methods=["PUT"])
@admin_required
def reject_request(request_id):

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:

        connection.start_transaction()

        cursor.execute("""
            SELECT *
            FROM borrow_requests
            WHERE request_id = %s
            FOR UPDATE
        """, (request_id,))

        borrow_request = cursor.fetchone()

        if not borrow_request:
            connection.rollback()
            return jsonify({"message": "Request not found"}), 404

        if borrow_request["request_status"] != "Pending":
            connection.rollback()
            return jsonify({
                "message": "Only pending requests can be rejected"
            }), 409

        cursor.execute("""
            UPDATE borrow_requests
            SET request_status = 'Rejected'
            WHERE request_id = %s
        """, (request_id,))

        cursor.execute("""
            INSERT INTO notifications (user_id, message)
            VALUES (%s, %s)
        """, (
            borrow_request["borrower_id"],
            f"Your borrow request #{request_id} has been rejected."
        ))

        connection.commit()

        return jsonify({
            "message": "Borrow request rejected successfully",
            "request_id": request_id,
            "status": "Rejected"
        }), 200

    except Exception as e:

        connection.rollback()
        print("Rejection error:", e)

        return jsonify({
            "message": "Unable to reject borrow request"
        }), 500

    finally:
        cursor.close()
        connection.close()


# -------------------------------------------------
# 6. STUDENT: CANCEL PENDING REQUEST
# -------------------------------------------------

@borrow_bp.route("/<int:request_id>/cancel", methods=["PUT"])
@token_required
def cancel_request(request_id):

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:

        connection.start_transaction()

        cursor.execute("""
            SELECT *
            FROM borrow_requests
            WHERE request_id = %s
            FOR UPDATE
        """, (request_id,))

        borrow_request = cursor.fetchone()

        if not borrow_request:
            connection.rollback()
            return jsonify({"message": "Request not found"}), 404

        if borrow_request["borrower_id"] != request.user["user_id"]:
            connection.rollback()
            return jsonify({
                "message": "You cannot cancel another user's request"
            }), 403

        if borrow_request["request_status"] != "Pending":
            connection.rollback()
            return jsonify({
                "message": "Only pending requests can be cancelled"
            }), 409

        cursor.execute("""
            UPDATE borrow_requests
            SET request_status = 'Cancelled'
            WHERE request_id = %s
        """, (request_id,))

        connection.commit()

        return jsonify({
            "message": "Borrow request cancelled successfully",
            "status": "Cancelled"
        }), 200

    except Exception as e:

        connection.rollback()
        print("Cancellation error:", e)

        return jsonify({
            "message": "Unable to cancel borrow request"
        }), 500

    finally:
        cursor.close()
        connection.close()