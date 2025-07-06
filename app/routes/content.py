from flask import Blueprint, request, jsonify, send_file
from app import db
from app.models import Content, User
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from io import BytesIO
import logging

content_bp = Blueprint('content_main', __name__)

logging.basicConfig(level=logging.DEBUG)

@content_bp.route('', methods=['GET'])
def get_all_content():
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        contents = Content.query.order_by(Content.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({
            'contents': [{
                'id': c.id,
                'title': c.title,
                'body': c.body,
                'category': c.category,
                'image_mimetype': c.image_mimetype,
                'created_at': c.created_at.isoformat(),
                'updated_at': c.updated_at.isoformat()
            } for c in contents.items],
            'total': contents.total,
            'pages': contents.pages,
            'current_page': contents.page
        }), 200
    except Exception as e:
        logging.error(f"Error fetching content: {str(e)}")
        return jsonify({'error': str(e)}), 500

@content_bp.route('/<int:id>', methods=['GET'])
def get_content_by_id(id):
    try:
        content = Content.query.get_or_404(id)
        return jsonify({
            'id': content.id,
            'title': content.title,
            'body': content.body,
            'category': content.category,
            'image_mimetype': content.image_mimetype,
            'created_at': content.created_at.isoformat(),
            'updated_at': content.updated_at.isoformat()
        }), 200
    except Exception as e:
        logging.error(f"Error fetching content {id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@content_bp.route('/image/<int:id>', methods=['GET'])
def get_content_image(id):
    try:
        content = Content.query.get_or_404(id)
        if not content.image_data:
            return jsonify({'error': 'No image available'}), 404
        return send_file(
            BytesIO(content.image_data),
            mimetype=content.image_mimetype,
            as_attachment=False
        )
    except Exception as e:
        logging.error(f"Error fetching content image {id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@content_bp.route('/<category>', methods=['GET'])
def get_content_by_category(category):
    try:
        contents = Content.query.filter_by(category=category).all()
        return jsonify([{
            'id': c.id,
            'title': c.title,
            'body': c.body,
            'category': c.category,
            'image_mimetype': c.image_mimetype,
            'created_at': c.created_at.isoformat(),
            'updated_at': c.updated_at.isoformat()
        } for c in contents]), 200
    except Exception as e:
        logging.error(f"Error fetching content by category {category}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@content_bp.route('', methods=['POST'])
@jwt_required()
def create_content():
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        user = User.query.get_or_404(get_jwt_identity())
        if 'image' not in request.files:
            image_data = None
            image_mimetype = None
        else:
            image = request.files['image']
            if image.filename == '':
                return jsonify({'error': 'No image selected'}), 400
            if not image.mimetype.startswith('image/'):
                return jsonify({'error': 'Invalid image format'}), 400
            if image.content_length > 1 * 1024 * 1024:  # 1MB limit
                return jsonify({'error': 'Image size exceeds 1MB'}), 400
            image_data = image.read()
            image_mimetype = image.mimetype

        title = request.form.get('title')
        body = request.form.get('body')
        category = request.form.get('category')

        if not title or not body or not category:
            return jsonify({'error': 'Title, body, and category are required'}), 400

        content = Content(
            title=title,
            body=body,
            category=category,
            image_data=image_data,
            image_mimetype=image_mimetype,
            user_id=user.id
        )
        db.session.add(content)
        db.session.commit()
        return jsonify({'message': 'Content created successfully'}), 201
    except Exception as e:
        logging.error(f"Error creating content: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@content_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_content(id):
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        user = User.query.get_or_404(get_jwt_identity())
        content = Content.query.get_or_404(id)

        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '':
                if not image.mimetype.startswith('image/'):
                    return jsonify({'error': 'Invalid image format'}), 400
                if image.content_length > 1 * 1024 * 1024:
                    return jsonify({'error': 'Image size exceeds 1MB'}), 400
                content.image_data = image.read()
                content.image_mimetype = image.mimetype
            else:
                content.image_data = None
                content.image_mimetype = None

        title = request.form.get('title', content.title)
        body = request.form.get('body', content.body)
        category = request.form.get('category', content.category)

        content.title = title
        content.body = body
        content.category = category
        db.session.commit()
        return jsonify({'message': 'Content updated successfully'}), 200
    except Exception as e:
        logging.error(f"Error updating content {id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@content_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_content(id):
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403

        user = User.query.get_or_404(get_jwt_identity())
        content = Content.query.get_or_404(id)
        db.session.delete(content)
        db.session.commit()
        return jsonify({'message': 'Content deleted successfully'}), 200
    except Exception as e:
        logging.error(f"Error deleting content {id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500