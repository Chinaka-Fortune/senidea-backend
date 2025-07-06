from flask import Blueprint, request, jsonify
from app import db
from app.models import ContactMessage
from datetime import datetime
from flask_jwt_extended import jwt_required, get_jwt
import logging

contact_bp = Blueprint('contact', __name__)

logging.basicConfig(level=logging.DEBUG)

@contact_bp.route('', methods=['POST'])
def create_contacts():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        name = data.get('name')
        email = data.get('email')
        message = data.get('message')
        phone_number = data.get('phone_number')
        address = data.get('address')

        if not name or not email or not message:
            return jsonify({'error': 'Name, email, and message are required'}), 400

        contact_message = ContactMessage(
            name=name,
            email=email,
            message=message,
            phone_number=phone_number,
            address=address,
            created_at=datetime.utcnow()
        )
        db.session.add(contact_message)
        db.session.commit()

        return jsonify({'message': 'Message sent successfully'}), 201
    except Exception as e:
        logging.error(f"Error creating contact message: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@contact_bp.route('', methods=['GET'])
@jwt_required()
def get_contacts():
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        contacts = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
        return jsonify({
            'contacts': [{
                'id': c.id,
                'name': c.name,
                'email': c.email,
                'message': c.message,
                'phone_number': c.phone_number,
                'address': c.address,
                'created_at': c.created_at.isoformat()
            } for c in contacts]
        }), 200
    except Exception as e:
        logging.error(f"Error fetching contacts: {str(e)}")
        return jsonify({'error': str(e)}), 500

@contact_bp.route('/<int:id>', methods=['GET'])
@jwt_required()
def get_contact_by_id(id):
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        contact = ContactMessage.query.get_or_404(id)
        return jsonify({
            'id': contact.id,
            'name': contact.name,
            'email': contact.email,
            'message': contact.message,
            'phone_number': contact.phone_number,
            'address': contact.address,
            'created_at': contact.created_at.isoformat()
        }), 200
    except Exception as e:
        logging.error(f"Error fetching contact by ID {id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@contact_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_contact(id):
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        contact = ContactMessage.query.get_or_404(id)
        db.session.delete(contact)
        db.session.commit()
        return jsonify({'message': 'Contact message deleted successfully'}), 200
    except Exception as e:
        logging.error(f"Error deleting contact by ID {id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500