from flask import Blueprint, request, jsonify
from app import db
from app.models import Donation, User
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from paystackapi.transaction import Transaction
import os
import logging

donation_bp = Blueprint('donation_main', __name__)
PAYSTACK_SECRET_KEY = os.environ.get('PAYSTACK_SECRET_KEY')

logging.basicConfig(level=logging.DEBUG)

@donation_bp.route('/test', methods=['GET'])
def test_donation():
    return jsonify({'message': 'Donation blueprint is working'}), 200

@donation_bp.route('', methods=['POST'])
@jwt_required(optional=True)
def donate():
    try:
        data = request.get_json()
        amount = data.get('amount')
        frequency = data.get('frequency', 'One-time')
        recognition = data.get('recognition', 'Private')
        email = data.get('email')

        if not amount or not email:
            return jsonify({'error': 'Amount and email are required'}), 400

        user_id = None
        try:
            
            user_id = get_jwt_identity()
            if user_id:
                logging.debug(f"JWT identity: {user_id}")
                user = User.query.get(user_id)
                if user:
                    email = user.email
                    logging.debug(f"User found: id={user_id}, email={email}")
                else:
                    logging.error(f"No user found for id: {user_id}")
                    user_id = None
            else:
                logging.debug("No valid JWT token provided")
        except Exception as e:
            logging.error(f"JWT processing error: {str(e)}")
            user_id = None

        logging.debug(f"Creating donation with user_id: {user_id}, email: {email}")
        transaction = Transaction(secret_key=PAYSTACK_SECRET_KEY)
        response = transaction.initialize(
            email=email,
            amount=int(amount * 100),
            callback_url='https://senidea-backend.vercel.app/api/donation/verify',
            metadata={'user_id': user_id, 'frequency': frequency, 'recognition': recognition}
        )

        if response['status']:
            donation = Donation(
                user_id=user_id,
                amount=amount,
                email=email,
                frequency=frequency,
                recognition=recognition,
                paystack_transaction_ref=response['data']['reference']
            )
            db.session.add(donation)
            db.session.commit()

            return jsonify({
                'message': 'Donation initialized',
                'authorization_url': response['data']['authorization_url'],
                'reference': response['data']['reference']
            }), 200
        else:
            return jsonify({'error': response['message']}), 400
    except Exception as e:
        logging.error(f"Error initializing donation: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@donation_bp.route('/verify/<reference>', methods=['GET'])
def verify_donation(reference):
    try:
        transaction = Transaction(secret_key=PAYSTACK_SECRET_KEY)
        response = transaction.verify(reference=reference)
        logging.debug(f"Paystack verify response for {reference}: {response}")
        if response['status'] and response['data']['status'] == 'success':
            donation = Donation.query.filter_by(paystack_transaction_ref=reference).first()
            if donation:
                db.session.commit()
                return jsonify({'message': 'Donation verified successfully', 'reference': reference}), 200
            return jsonify({'error': 'Donation not found in database', 'reference': reference}), 404
        return jsonify({'error': 'Transaction verification failed', 'details': response.get('message', 'No message provided')}), 400
    except Exception as e:
        logging.error(f"Error verifying donation {reference}: {str(e)}")
        return jsonify({'error': 'Verification error', 'details': str(e)}), 500

@donation_bp.route('', methods=['GET'])
@jwt_required()
def get_donations():
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        donations = Donation.query.all()
        return jsonify([{
            'id': d.id,
            'user_id': d.user_id,
            'user_email': User.query.get(d.user_id).email if d.user_id else d.email,
            'amount': d.amount,
            'frequency': d.frequency,
            'recognition': d.recognition,
            'paystack_transaction_ref': d.paystack_transaction_ref,
            'created_at': d.created_at.isoformat()
        } for d in donations]), 200
    except Exception as e:
        logging.error(f"Error fetching donations: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@donation_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_donation(id):
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        donation = Donation.query.get_or_404(id)
        data = request.get_json()

        donation.amount = data.get('amount', donation.amount)
        donation.email = data.get('email', donation.email)
        donation.frequency = data.get('frequency', donation.frequency)
        donation.recognition = data.get('recognition', donation.recognition)

        if data.get('email'):
            user = User.query.filter_by(email=data.get('email').lower()).first()
            donation.user_id = user.id if user else None

        db.session.commit()
        return jsonify({'message': 'Donation updated successfully'}), 200
    except Exception as e:
        logging.error(f"Error updating donation {id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@donation_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_donation(id):
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        donation = Donation.query.get_or_404(id)
        db.session.delete(donation)
        db.session.commit()
        return jsonify({'message': 'Donation deleted successfully'}), 200
    except Exception as e:
        logging.error(f"Error deleting donation {id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 400