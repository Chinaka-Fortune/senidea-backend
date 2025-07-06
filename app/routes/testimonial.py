from flask import Blueprint, request, jsonify
from app import db
from app.models import Testimonial, User
from flask_jwt_extended import jwt_required, get_jwt
import logging

testimonial_bp = Blueprint('testimonial_main', __name__)

logging.basicConfig(level=logging.DEBUG)

@testimonial_bp.route('', methods=['POST'])
def create_testimonial():
    try:
        data = request.get_json()
        name = data.get('name')
        content = data.get('content')
        location = data.get('location')

        if not name or not content or not location:
            return jsonify({'error': 'Name, content, and location are required'}), 400

        testimonial = Testimonial(name=name, content=content, location=location)
        db.session.add(testimonial)
        db.session.commit()
        return jsonify({'message': 'Testimonial submitted successfully', 'id': testimonial.id}), 201
    except Exception as e:
        logging.error(f"Error creating testimonial: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@testimonial_bp.route('', methods=['GET'])
def get_testimonials():
    try:
        testimonials = Testimonial.query.order_by(Testimonial.created_at.desc()).all()
        return jsonify([{
            'id': t.id,
            'name': t.name,
            'content': t.content,
            'location': t.location,
            'created_at': t.created_at.isoformat()
        } for t in testimonials]), 200
    except Exception as e:
        logging.error(f"Error fetching testimonials: {str(e)}")
        return jsonify({'error': str(e)}), 500

@testimonial_bp.route('/<int:id>', methods=['GET'])
def get_testimonial(id):
    try:
        testimonial = Testimonial.query.get_or_404(id)
        return jsonify({
            'id': testimonial.id,
            'name': testimonial.name,
            'content': testimonial.content,
            'location': testimonial.location,
            'created_at': testimonial.created_at.isoformat()
        }), 200
    except Exception as e:
        logging.error(f"Error fetching testimonial {id}: {str(e)}")
        return jsonify({'error': str(e)}), 404

@testimonial_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_testimonial(id):
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        testimonial = Testimonial.query.get_or_404(id)
        data = request.get_json()

        testimonial.name = data.get('name', testimonial.name)
        testimonial.content = data.get('content', testimonial.content)
        testimonial.location = data.get('location', testimonial.location)
        db.session.commit()
        return jsonify({'message': 'Testimonial updated successfully'}), 200
    except Exception as e:
        logging.error(f"Error updating testimonial {id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@testimonial_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_testimonial(id):
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        testimonial = Testimonial.query.get_or_404(id)
        db.session.delete(testimonial)
        db.session.commit()
        return jsonify({'message': 'Testimonial deleted successfully'}), 200
    except Exception as e:
        logging.error(f"Error deleting testimonial {id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 400