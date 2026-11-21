import jwt
from functools import wraps
from flask import request, jsonify
import os
from dotenv import load_dotenv

load_dotenv()

def token_required(f):

    @wraps(f)
    def decorated(*args, **kwargs):

        token = None

        if "Authorization" in request.headers:

            auth_header = request.headers["Authorization"]

            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1]

        if not token:
            return jsonify({
                "message": "Authentication token is missing"
            }), 401

        try:

            data = jwt.decode(
                token,
                os.getenv("JWT_SECRET"),
                algorithms=["HS256"]
            )

            request.user = data

        except jwt.ExpiredSignatureError:

            return jsonify({
                "message": "Token has expired"
            }), 401

        except jwt.InvalidTokenError:

            return jsonify({
                "message": "Invalid authentication token"
            }), 401

        return f(*args, **kwargs)

    return decorated


def admin_required(f):

    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):

        if request.user.get("role") != "admin":
            return jsonify({
                "message": "Administrator access required"
            }), 403

        return f(*args, **kwargs)

    return decorated