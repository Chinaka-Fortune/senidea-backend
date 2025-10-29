# api/debug_secret.py
from app import create_app
from flask import jsonify

app = create_app()

def handler(event, context=None):
    """Vercel serverless handler"""
    with app.app_context():
        secret = app.config.get('ADMIN_SECRET', 'NOT SET')
        return {
            'statusCode': 200,
            'body': jsonify({
                'admin_secret_loaded': bool(secret != 'NOT SET'),
                'secret_preview': secret[:10] + '...' if secret else None,  # First 10 chars
                'full_length': len(secret) if secret else 0
            }).get_data(as_text=True),
            'headers': {'Content-Type': 'application/json'}
        }

lambda_handler = handler