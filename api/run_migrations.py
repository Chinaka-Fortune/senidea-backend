# api/run_migrations.py
from app import create_app
from flask_migrate import upgrade
from flask import jsonify

app = create_app()

def handler(event, context=None):
    """Vercel serverless handler"""
    with app.app_context():
        try:
            upgrade()
            response = jsonify({"status": "success", "message": "Migrations applied!"})
            return {
                'statusCode': 200,
                'body': response.get_data(as_text=True),
                'headers': {'Content-Type': 'application/json'}
            }
        except Exception as e:
            response = jsonify({"status": "error", "message": str(e)})
            return {
                'statusCode': 500,
                'body': response.get_data(as_text=True),
                'headers': {'Content-Type': 'application/json'}
            }

# Vercel expects this
lambda_handler = handler