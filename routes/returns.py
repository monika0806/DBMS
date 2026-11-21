
from flask import Blueprint, request, jsonify
from config.db import get_db_connection
from utils.auth_middleware import admin_required, token_required

returns_bp = Blueprint("returns", __name__)

FINE_PER_DAY = 10.00


# -----------------------------------------
# ADMIN: RECORD A RESOURCE RETURN
# -----------------------------------------

@returns_bp.route("/<int:loan_id>", methods=["POST"])
@admin_required
def record_return(loan_id):

    data = request.get_json(silent=True) or {}

    resource_condition = data.get("resource_condition", "Good")
    remarks = (data.get("remarks") or "").strip() or None

    allowed_conditions = ["Good", "Damaged", "Lost"]

    if resource_condition not in allowed_conditions:
        return jsonify({
            "message": "Condition must be Good, Damaged or Lost."
        }), 400

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                l.loan_id,
                l.due_date,
                l.loan_status,
                br.borrower_id,
                br.resource_id
            FROM loans l
            JOIN borrow_requests br
                ON l.request_id = br.request_id
            WHERE l.loan_id = %s
            FOR UPDATE
        """, (loan_id,))

        loan = cursor.fetchone()

        if not loan:
            connection.rollback()
            return jsonify({"message": "Loan not found."}), 404

        if loan["loan_status"] == "Returned":
            connection.rollback()
            return jsonify({
                "message": "This resource has already been returned."
            }), 409

        cursor.execute("""
            SELECT return_id
            FROM returns
            WHERE loan_id = %s
        """, (loan_id,))

        if cursor.fetchone():
            connection.rollback()
            return jsonify({
                "message": "Return record already exists."
            }), 409

        cursor.execute("""
            INSERT INTO returns
                (loan_id, actual_return_date, resource_condition, remarks)
            VALUES (%s, CURDATE(), %s, %s)
        """, (loan_id, resource_condition, remarks))

        actual_return_date = None

        cursor.execute("""
            SELECT actual_return_date
            FROM returns
            WHERE loan_id = %s
        """, (loan_id,))

        return_record = cursor.fetchone()
        actual_return_date = return_record["actual_return_date"]

        due_date = loan["due_date"]

        late_days = max(
            0,
            (actual_return_date - due_date).days
        )

        fine_amount = round(late_days * FINE_PER_DAY, 2)

        cursor.execute("""
            UPDATE loans
            SET loan_status = 'Returned'
            WHERE loan_id = %s
        """, (loan_id,))

        # Make resource available only if it is in good condition.
        # Damaged or lost resources remain unavailable for admin review.
        if resource_condition == "Good":
            cursor.execute("""
                UPDATE resources
                SET availability_status = 'Available'
                WHERE resource_id = %s
            """, (loan["resource_id"],))
        else:
            cursor.execute("""
                UPDATE resources
                SET availability_status = 'Unavailable'
                WHERE resource_id = %s
            """, (loan["resource_id"],))

        if fine_amount > 0:
            cursor.execute("""
                INSERT INTO fines
                    (loan_id, late_days, fine_amount, payment_status)
                VALUES (%s, %s, %s, 'Pending')
            """, (loan_id, late_days, fine_amount))

            fine_id = cursor.lastrowid

        else:
            fine_id = None

        cursor.execute("""
            INSERT INTO notifications (user_id, message)
            VALUES (%s, %s)
        """, (
            loan["borrower_id"],
            (
                f"Your borrowed resource has been returned successfully. "
                f"Loan ID: {loan_id}. "
                + (
                    f"A fine of ₹{fine_amount:.2f} has been generated."
                    if fine_amount > 0
                    else "No late fine is applicable."
                )
            )
        ))

        connection.commit()

        return jsonify({
            "message": "Resource return recorded successfully.",
            "loan_id": loan_id,
            "actual_return_date": actual_return_date.isoformat(),
            "resource_condition": resource_condition,
            "late_days": late_days,
            "fine_amount": fine_amount,
            "fine_id": fine_id
        }), 201

    except Exception as e:
        connection.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()


# -----------------------------------------
# STUDENT: VIEW OWN RETURNS
# -----------------------------------------

@returns_bp.route("/admin/all", methods=["GET"])
@admin_required
def get_all_returns_for_admin():

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                ret.return_id,
                ret.loan_id,
                ret.actual_return_date,
                ret.resource_condition,
                ret.remarks,
                br.borrower_id,
                u.full_name AS borrower_name,
                r.resource_name
            FROM returns ret
            JOIN loans l ON ret.loan_id = l.loan_id
            JOIN borrow_requests br ON l.request_id = br.request_id
            JOIN users u ON br.borrower_id = u.user_id
            JOIN resources r ON br.resource_id = r.resource_id
            ORDER BY ret.return_id DESC
        """)

        returns = cursor.fetchall()

        return jsonify({
            "total": len(returns),
            "returns": returns
        }), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()



# -----------------------------------------
# STUDENT: VIEW OWN RETURNS
# -----------------------------------------

@returns_bp.route("/my", methods=["GET"])
@token_required
def get_my_returns():

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        from flask import request

        user_id = request.user["user_id"]

        cursor.execute("""
            SELECT
                ret.return_id,
                ret.loan_id,
                ret.actual_return_date,
                ret.resource_condition,
                ret.remarks,
                r.resource_name
            FROM returns ret
            JOIN loans l ON ret.loan_id = l.loan_id
            JOIN borrow_requests br ON l.request_id = br.request_id
            JOIN resources r ON br.resource_id = r.resource_id
            WHERE br.borrower_id = %s
            ORDER BY ret.return_id DESC
        """, (user_id,))

        returns = cursor.fetchall()

        return jsonify({
            "total": len(returns),
            "returns": returns
        }), 200

    except Exception as e:
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()

