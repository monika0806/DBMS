
from flask import Flask, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from routes.returns import returns_bp
from routes.fines import fines_bp
from routes.payments import payments_bp

from routes.auth import auth_bp
from routes.resources import resources_bp
from routes.borrow import borrow_bp
from routes.admin import admin_bp
from routes.notifications import notifications_bp
from routes.loans import loans_bp

app = Flask(__name__)

CORS(app, origins=["http://localhost:5173"])

bcrypt = Bcrypt(app)

# Authentication API
app.register_blueprint(
    auth_bp,
    url_prefix="/api/auth"
)
app.register_blueprint(
    notifications_bp,
    url_prefix="/api/notifications"
)
app.register_blueprint(loans_bp, url_prefix="/api/loans")
app.register_blueprint(returns_bp, url_prefix="/api/returns")
app.register_blueprint(fines_bp, url_prefix="/api/fines")
app.register_blueprint(payments_bp, url_prefix="/api/payments")
# Resources API
app.register_blueprint(
    resources_bp,
    url_prefix="/api/resources"
)

# Borrowing API
app.register_blueprint(
    borrow_bp,
    url_prefix="/api/borrow"
)

# Admin API
app.register_blueprint(
    admin_bp,
    url_prefix="/api/admin"
)


@app.route("/")
def home():
    return jsonify({
        "message": "Welcome to ShareSpace API",
        "status": "Running successfully"
    })


@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "project": "ShareSpace"
    })


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
