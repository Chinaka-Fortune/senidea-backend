from flask import Blueprint, request, jsonify
from app import db, bcrypt
from app.models import User
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import logging
import os

auth_bp = Blueprint('auth', __name__)

logging.basicConfig(level=logging.DEBUG)

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        email = data.get('email').lower()
        password = data.get('password')
        role = data.get('role', 'Visitor')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 400

        valid_roles = ['Visitor', 'Donor', 'Volunteer', 'Partner', 'Admin']
        if role not in valid_roles:
            return jsonify({'error': 'Invalid role'}), 400

        if role == 'Admin' and data.get('admin_secret') != os.getenv('ADMIN_SECRET', 'your-admin-secret'):
            return jsonify({'error': 'Invalid admin secret'}), 403

        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(email=email, password_hash=password_hash, role=role)
        db.session.add(user)
        db.session.commit()

        access_token = create_access_token(identity=str(user.id), additional_claims={'role': role})
        logging.debug(f"Register token for user {user.id} ({email}): {access_token}")

        return jsonify({'access_token': access_token, 'role': role}), 201
    except Exception as e:
        logging.error(f"Error registering user: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        email = data.get('email').lower()
        password = data.get('password')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            access_token = create_access_token(identity=str(user.id), additional_claims={'role': user.role})
            logging.debug(f"Login token for user {user.id} ({email}): {access_token}")

            return jsonify({'access_token': access_token, 'role': user.role}), 200
        return jsonify({'error': 'Invalid credentials'}), 401
    except Exception as e:
        logging.error(f"Error logging in: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@auth_bp.route('/validate', methods=['GET'])
@jwt_required()
def validate():
    try:
        user_id = get_jwt_identity()
        logging.debug(f"Validating JWT for user_id: {user_id}")
        user = User.query.get(user_id)
        if not user:
            logging.error(f"No user found for id: {user_id}")
            return jsonify({'error': 'User not found'}), 404
        return jsonify({'email': user.email, 'role': user.role}), 200
    except Exception as e:
        logging.error(f"Error validating token: {str(e)}")
        return jsonify({'error': str(e)}), 400