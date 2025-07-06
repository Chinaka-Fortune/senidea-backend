from flask import Blueprint, request, jsonify
from app import db
from app.models import Volunteer, User
from flask_jwt_extended import jwt_required, get_jwt
import logging

volunteer_bp = Blueprint('volunteer_main', __name__)

logging.basicConfig(level=logging.DEBUG)

@volunteer_bp.route('', methods=['POST'])
def create_volunteer():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        skills = data.get('skills')

        if not name or not email:
            return jsonify({'error': 'Name and email are required'}), 400

        volunteer = Volunteer(name=name, email=email, skills=skills)
        db.session.add(volunteer)
        db.session.commit()
        return jsonify({'message': 'Volunteer application submitted successfully'}), 201
    except Exception as e:
        logging.error(f"Error creating volunteer: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@volunteer_bp.route('', methods=['GET'])
@jwt_required()
def get_volunteers():
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        volunteers = Volunteer.query.all()
        return jsonify([{
            'id': v.id,
            'name': v.name,
            'email': v.email,
            'skills': v.skills,
            'created_at': v.created_at.isoformat()
        } for v in volunteers]), 200
    except Exception as e:
        logging.error(f"Error fetching volunteers: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500