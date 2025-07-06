from flask import Blueprint, request, jsonify
from app import db
from app.models import Partnership
from datetime import datetime
from flask_jwt_extended import jwt_required, get_jwt
import logging

partnership_bp = Blueprint('partnership_main', __name__)

logging.basicConfig(level=logging.DEBUG)

@partnership_bp.route('', methods=['GET'])
def partnership_info():
    try:
        partnership_data = {
            'opportunities': 'Collaborate with us to promote inclusion and empowerment.',
            'contact': 'Reach out via our contact form to discuss partnership opportunities.'
        }
        return jsonify(partnership_data), 200
    except Exception as e:
        logging.error(f"Error fetching partnership info: {str(e)}")
        return jsonify({'error': str(e)}), 500

@partnership_bp.route('', methods=['POST'])
def submit_partnership():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        organization = data.get('organization')
        email = data.get('email')
        message = data.get('message')

        if not organization or not email:
            return jsonify({'error': 'Organization and email are required'}), 400

        partnership = Partnership(
            organization=organization,
            email=email,
            message=message,
            created_at=datetime.utcnow()
        )
        db.session.add(partnership)
        db.session.commit()
        return jsonify({'message': 'Partnership request submitted successfully'}), 201
    except Exception as e:
        logging.error(f"Error submitting partnership: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@partnership_bp.route('/submissions', methods=['GET'])
@jwt_required()
def get_partnerships():
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        partnerships = Partnership.query.order_by(Partnership.created_at.desc()).all()
        return jsonify({
            'partnerships': [{
                'id': p.id,
                'organization': p.organization,
                'email': p.email,
                'message': p.message,
                'created_at': p.created_at.isoformat()
            } for p in partnerships]
        }), 200
    except Exception as e:
        logging.error(f"Error fetching partnerships: {str(e)}")
        return jsonify({'error': str(e)}), 500

@partnership_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_partnership(id):
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        partnership = Partnership.query.get_or_404(id)
        db.session.delete(partnership)
        db.session.commit()
        return jsonify({'message': 'Partnership deleted successfully'}), 200
    except Exception as e:
        logging.error(f"Error deleting partnership by ID {id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500