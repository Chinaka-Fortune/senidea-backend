from flask import Blueprint, request, jsonify
from app import db
from app.models import NewsletterSubscription
from datetime import datetime
from flask_jwt_extended import jwt_required, get_jwt
import logging

newsletter_bp = Blueprint('newsletter', __name__)

logging.basicConfig(level=logging.DEBUG)

@newsletter_bp.route('/subscribe', methods=['POST'])
def subscribe_newsletter():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        email = data.get('email')
        if not email:
            return jsonify({'error': 'Email is required'}), 400

        if NewsletterSubscription.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already subscribed'}), 400

        subscription = NewsletterSubscription(
            email=email,
            subscribed_at=datetime.utcnow()
        )
        db.session.add(subscription)
        db.session.commit()
        return jsonify({'message': 'Subscribed successfully'}), 201
    except Exception as e:
        logging.error(f"Error creating subscription: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@newsletter_bp.route('', methods=['GET'])
@jwt_required()
def get_subscriptions():
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        subscriptions = NewsletterSubscription.query.order_by(NewsletterSubscription.subscribed_at.desc()).all()
        return jsonify({
            'subscriptions': [{
                'id': s.id,
                'email': s.email,
                'subscribed_at': s.subscribed_at.isoformat()
            } for s in subscriptions]
        }), 200
    except Exception as e:
        logging.error(f"Error fetching subscriptions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@newsletter_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_subscription(id):
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        subscription = NewsletterSubscription.query.get_or_404(id)
        db.session.delete(subscription)
        db.session.commit()
        return jsonify({'message': 'Subscription deleted successfully'}), 200
    except Exception as e:
        logging.error(f"Error deleting subscription by ID {id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500