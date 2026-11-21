
from flask import Blueprint, jsonify
from config.db import get_db_connection
from utils.auth_middleware import token_required, admin_required

loans_bp = Blueprint("loans", __name__)


# -----------------------------------------
# GET STUDENT'S LOANS
# -----------------------------------------

@loans_bp.route("/my", methods=["GET"])
@token_required
def get_my_loans():

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        user_id = request_user_id()

        cursor.execute("""
            UPDATE loans l
            JOIN borrow_requests br ON l.request_id = br.request_id
            SET l.loan_status = 'Overdue'
            WHERE br.borrower_id = %s
              AND l.loan_status = 'Active'
              AND l.due_date < CURDATE()
        """, (user_id,))

        connection.commit()

        cursor.execute("""
            SELECT
                l.loan_id,
                l.request_id,
                l.issue_date,
                l.due_date,
                l.loan_status,
                br.resource_id,
                r.resource_name,
                ret.actual_return_date,
                ret.resource_condition
            FROM loans l
            JOIN borrow_requests br
                ON l.request_id = br.request_id
            JOIN resources r
                ON br.resource_id = r.resource_id
            LEFT JOIN returns ret
                ON l.loan_id = ret.loan_id
            WHERE br.borrower_id = %s
            ORDER BY l.loan_id DESC
        """, (user_id,))

        loans = cursor.fetchall()

        return jsonify({
            "total": len(loans),
            "loans": loans
        }), 200

    except Exception as e:
        connection.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()


# -----------------------------------------
# GET ALL LOANS (ADMIN)
# -----------------------------------------

@loans_bp.route("/admin/all", methods=["GET"])
@admin_required
def get_all_loans():

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            UPDATE loans
            SET loan_status = 'Overdue'
            WHERE loan_status = 'Active'
              AND due_date < CURDATE()
        """)

        connection.commit()

        cursor.execute("""
            SELECT
                l.loan_id,
                l.request_id,
                l.issue_date,
                l.due_date,
                l.loan_status,
                br.resource_id,
                br.borrower_id,
                u.full_name AS borrower_name,
                r.resource_name,
                ret.actual_return_date,
                ret.resource_condition
            FROM loans l
            JOIN borrow_requests br
                ON l.request_id = br.request_id
            JOIN users u
                ON br.borrower_id = u.user_id
            JOIN resources r
                ON br.resource_id = r.resource_id
            LEFT JOIN returns ret
                ON l.loan_id = ret.loan_id
            ORDER BY l.loan_id DESC
        """)

        loans = cursor.fetchall()

        return jsonify({
            "total": len(loans),
            "loans": loans
        }), 200

    except Exception as e:
        connection.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()


def request_user_id():
    from flask import request
    return request.user["user_id"]
