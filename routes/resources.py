from flask import Blueprint, request, jsonify
from config.db import get_db_connection
from utils.auth_middleware import token_required,admin_required

resources_bp = Blueprint("resources", __name__)


# ---------------- VIEW ALL RESOURCES ----------------

@resources_bp.route("/", methods=["GET"])
def get_resources():

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:

        query = """
            SELECT
                r.*,
                u.full_name AS owner_name,
                c.category_name
            FROM resources r
            JOIN users u ON r.owner_id = u.user_id
            JOIN categories c ON r.category_id = c.category_id
            WHERE r.availability_status = 'Available'
            ORDER BY r.created_at DESC
        """

        cursor.execute(query)

        resources = cursor.fetchall()

        return jsonify(resources), 200

    finally:

        cursor.close()
        connection.close()


# ---------------- VIEW RESOURCE BY ID ----------------

@resources_bp.route("/<int:resource_id>", methods=["GET"])
def get_resource(resource_id):

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:

        query = """
            SELECT
                r.*,
                u.full_name AS owner_name,
                c.category_name
            FROM resources r
            JOIN users u ON r.owner_id = u.user_id
            JOIN categories c ON r.category_id = c.category_id
            WHERE r.resource_id = %s
        """

        cursor.execute(query, (resource_id,))

        resource = cursor.fetchone()

        if not resource:
            return jsonify({"message": "Resource not found"}), 404

        return jsonify(resource), 200

    finally:

        cursor.close()
        connection.close()



# ---------------- ADMIN: VIEW ALL RESOURCES ----------------

@resources_bp.route("/admin/all", methods=["GET"])
@admin_required
def get_all_resources():

    connection = get_db_connection()

    if not connection:
        return jsonify({
            "message": "Database connection failed"
        }), 500

    cursor = connection.cursor(dictionary=True)

    try:

        query = """
            SELECT
                r.*,
                u.full_name AS owner_name,
                u.email AS owner_email,
                c.category_name
            FROM resources r
            LEFT JOIN users u ON r.owner_id = u.user_id
            LEFT JOIN categories c ON r.category_id = c.category_id
            ORDER BY r.created_at DESC
        """

        cursor.execute(query)

        resources = cursor.fetchall()

        return jsonify({
            "message": "Resources fetched successfully",
            "total": len(resources),
            "resources": resources
        }), 200

    except Exception as e:

        print("Admin resources error:", e)

        return jsonify({
            "message": "Unable to fetch resources"
        }), 500

    finally:

        cursor.close()
        connection.close()



# ---------------- ADD RESOURCE ----------------

@resources_bp.route("/", methods=["POST"])
@token_required
def add_resource():

    data = request.get_json()

    resource_name = data.get("resource_name")
    category_id = data.get("category_id")

    if not resource_name or not category_id:
        return jsonify({
            "message": "Resource name and category are required"
        }), 400

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor()

    try:

        query = """
            INSERT INTO resources
            (
                owner_id,
                category_id,
                resource_name,
                description,
                condition_status,
                rental_price,
                resource_image
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(query, (

            request.user["user_id"],
            category_id,
            resource_name,
            data.get("description"),
            data.get("condition_status", "Good"),
            data.get("rental_price", 0),
            data.get("resource_image")

        ))

        connection.commit()

        return jsonify({
            "message": "Resource added successfully",
            "resource_id": cursor.lastrowid
        }), 201

    except Exception as e:

        connection.rollback()

        return jsonify({"message": str(e)}), 400

    finally:

        cursor.close()
        connection.close()


# ---------------- UPDATE RESOURCE ----------------

@resources_bp.route("/<int:resource_id>", methods=["PUT"])
@token_required
def update_resource(resource_id):

    data = request.get_json()

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            "SELECT * FROM resources WHERE resource_id = %s",
            (resource_id,)
        )

        resource = cursor.fetchone()

        if not resource:
            return jsonify({"message": "Resource not found"}), 404

        if (
            request.user["role"] != "admin"
            and resource["owner_id"] != request.user["user_id"]
        ):
            return jsonify({"message": "Access denied"}), 403

        fields = [
            "resource_name",
            "description",
            "category_id",
            "condition_status",
            "rental_price",
            "resource_image",
            "availability_status"
        ]

        updates = []
        values = []

        for field in fields:

            if field in data:
                updates.append(f"{field} = %s")
                values.append(data[field])

        if not updates:
            return jsonify({"message": "No fields provided"}), 400

        values.append(resource_id)

        query = f"""
            UPDATE resources
            SET {', '.join(updates)}
            WHERE resource_id = %s
        """

        cursor.execute(query, tuple(values))

        connection.commit()

        return jsonify({
            "message": "Resource updated successfully"
        }), 200

    except Exception as e:

        connection.rollback()

        return jsonify({"message": str(e)}), 400

    finally:

        cursor.close()
        connection.close()


# ---------------- DELETE RESOURCE ----------------

@resources_bp.route("/<int:resource_id>", methods=["DELETE"])
@token_required
def delete_resource(resource_id):

    connection = get_db_connection()

    if not connection:
        return jsonify({"message": "Database connection failed"}), 500

    cursor = connection.cursor(dictionary=True)

    try:

        cursor.execute(
            "SELECT * FROM resources WHERE resource_id = %s",
            (resource_id,)
        )

        resource = cursor.fetchone()

        if not resource:
            return jsonify({"message": "Resource not found"}), 404

        if (
            request.user["role"] != "admin"
            and resource["owner_id"] != request.user["user_id"]
        ):
            return jsonify({"message": "Access denied"}), 403

        cursor.execute(
            "DELETE FROM resources WHERE resource_id = %s",
            (resource_id,)
        )

        connection.commit()

        return jsonify({
            "message": "Resource deleted successfully"
        }), 200

    except Exception as e:

        connection.rollback()

        return jsonify({"message": str(e)}), 400

    finally:

        cursor.close()
        connection.close()