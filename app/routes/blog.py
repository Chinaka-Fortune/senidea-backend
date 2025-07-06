from flask import Blueprint, request, jsonify, send_file, make_response
from app import db
from app.models import BlogPost, User, Comment, Like
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from PIL import Image, UnidentifiedImageError
import io
import logging
import tempfile
import os
import binascii

blog_bp = Blueprint('blog', __name__)

logging.basicConfig(filename='/Users/apple/Desktop/senidea-enableall/senidea-backend/app.log', level=logging.DEBUG)

@blog_bp.route('', methods=['GET', 'OPTIONS'])
def get_posts():
    if request.method == 'OPTIONS':
        logging.debug("Handling OPTIONS for /api/blog")
        response = jsonify({"status": "ok"})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, bypass-tunnel-reminder, x-tunnel-password')
        response.headers.add('Access-Control-Max-Age', '86400')
        return response

    try:
        logging.debug("Fetching blog posts")
        category = request.args.get('category')
        limit = request.args.get('limit', type=int, default=3)
        offset = request.args.get('offset', type=int, default=0)
        query = BlogPost.query
        if category:
            query = query.filter_by(category=category)
        total = query.count()
        posts = query.order_by(BlogPost.created_at.desc()).limit(limit).offset(offset).all()
        response = make_response(jsonify({
            'posts': [{
                'id': p.id,
                'title': p.title,
                'content': p.content,
                'category': p.category,
                'image_path': f'/api/blog/image/{p.id}' if p.image_data else None,
                'image_mimetype': p.image_mimetype,
                'author_id': p.author_id,
                'created_at': p.created_at.isoformat(),
                'updated_at': p.updated_at.isoformat(),
                'comment_count': len(p.comments),
                'like_count': len(p.likes)
            } for p in posts],
            'total': total
        }))
        response.headers['Cache-Control'] = 'public, max-age=300'
        # Handle empty posts list for ETag
        response.headers['ETag'] = f'posts-{len(posts)}-{max(p.updated_at.timestamp() for p in posts) if posts else 0}'
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        return response, 200
    except Exception as e:
        logging.error(f"Error fetching blog posts: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@blog_bp.route('/<int:id>', methods=['GET'])
def get_post(id):
    try:
        post = BlogPost.query.get_or_404(id)
        response = make_response(jsonify({
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'category': post.category,
            'image_path': f'/api/blog/image/{post.id}' if post.image_data else None,
            'image_mimetype': post.image_mimetype,
            'author_id': post.author_id,
            'created_at': post.created_at.isoformat(),
            'updated_at': post.updated_at.isoformat(),
            'comment_count': len(post.comments),
            'like_count': len(post.likes)
        }))
        response.headers['Cache-Control'] = 'public, max-age=300'
        response.headers['ETag'] = f'post-{id}-{post.updated_at.timestamp()}'
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        return response, 200
    except Exception as e:
        logging.error(f"Error fetching blog post {id}: {str(e)}")
        return jsonify({'error': 'Blog post not found'}), 404

@blog_bp.route('/image/<int:id>', methods=['GET', 'OPTIONS'])
def get_post_image(id):
    if request.method == 'OPTIONS':
        logging.debug(f"Handling OPTIONS for /api/blog/image/{id}")
        response = jsonify({"status": "ok"})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, bypass-tunnel-reminder, x-tunnel-password')
        response.headers.add('Access-Control-Max-Age', '86400')
        return response

    try:
        logging.debug(f"Fetching image for post {id}")
        post = BlogPost.query.get_or_404(id)
        if not post.image_data:
            logging.warning(f"No image data for post {id}")
            return jsonify({'error': 'No image found for this post'}), 404
        response = make_response(send_file(
            io.BytesIO(post.image_data),
            mimetype=post.image_mimetype
        ))
        response.headers['Cache-Control'] = 'public, max-age=86400'
        response.headers['ETag'] = f'image-{id}-{post.updated_at.timestamp()}'
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        logging.debug(f"Image for post {id} served successfully")
        return response
    except Exception as e:
        logging.error(f"Error fetching image for post {id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@blog_bp.route('', methods=['POST'])
@jwt_required()
def create_post():
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
            if image.content_length and image.content_length > 1 * 1024 * 1024:
                return jsonify({'error': 'Image size exceeds 1MB'}), 400
            try:
                # Log file details
                image.seek(0)
                first_bytes = image.read(8)
                image.seek(0)
                logging.debug(f"Processing image: filename={image.filename}, mimetype={image.mimetype}, size={image.content_length or 'unknown'}, first_bytes={binascii.hexlify(first_bytes)}")
                
                # Save to temporary file to ensure stream integrity
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image.filename)[1]) as temp_file:
                    image.save(temp_file.name)
                    logging.debug(f"Saved image to temp file: {temp_file.name}")
                    img = Image.open(temp_file.name)
                    img.verify()  # Verify image
                    img = Image.open(temp_file.name)  # Reopen for processing
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    output = io.BytesIO()
                    format_map = {
                        'image/jpeg': 'JPEG',
                        'image/png': 'PNG',
                        'image/gif': 'GIF',
                        'image/bmp': 'BMP',
                        'image/webp': 'WEBP'
                    }
                    image_format = format_map.get(image.mimetype, 'JPEG')  # Fallback to JPEG
                    img.save(output, format=image_format, quality=85 if image_format == 'JPEG' else None)
                    image_data = output.getvalue()
                    image_mimetype = image.mimetype
                os.unlink(temp_file.name)  # Clean up temp file
                logging.debug(f"Processed image {image.filename} successfully")
            except UnidentifiedImageError as e:
                logging.error(f"Cannot identify image file {image.filename}: {str(e)}")
                return jsonify({'error': f'Invalid image file: {str(e)}'}), 400
            except Exception as e:
                logging.error(f"Error processing image {image.filename}: {str(e)}")
                return jsonify({'error': f'Image processing error: {str(e)}'}), 400

        title = request.form.get('title')
        content = request.form.get('content')
        category = request.form.get('category')

        if not title or not content or not category:
            return jsonify({'error': 'Title, content, and category are required'}), 400

        post = BlogPost(
            title=title,
            content=content,
            category=category,
            image_data=image_data,
            image_mimetype=image_mimetype,
            author_id=user.id
        )
        db.session.add(post)
        db.session.commit()
        logging.info(f"Blog post created with ID {post.id} by user {user.id}")
        return jsonify({'message': 'Blog post created successfully', 'id': post.id}), 201
    except Exception as e:
        logging.error(f"Error creating blog post: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@blog_bp.route('/<int:id>', methods=['PUT'])
@jwt_required()
def update_post(id):
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403
        user = User.query.get_or_404(get_jwt_identity())
        post = BlogPost.query.get_or_404(id)

        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '':
                if not image.mimetype.startswith('image/'):
                    return jsonify({'error': 'Invalid image format'}), 400
                if image.content_length and image.content_length > 1 * 1024 * 1024:
                    return jsonify({'error': 'Image size exceeds 1MB'}), 400
                try:
                    image.seek(0)
                    first_bytes = image.read(8)
                    image.seek(0)
                    logging.debug(f"Processing image: filename={image.filename}, mimetype={image.mimetype}, size={image.content_length or 'unknown'}, first_bytes={binascii.hexlify(first_bytes)}")
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(image.filename)[1]) as temp_file:
                        image.save(temp_file.name)
                        img = Image.open(temp_file.name)
                        img.verify()
                        img = Image.open(temp_file.name)
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        output = io.BytesIO()
                        format_map = {
                            'image/jpeg': 'JPEG',
                            'image/png': 'PNG',
                            'image/gif': 'GIF',
                            'image/bmp': 'BMP',
                            'image/webp': 'WEBP'
                        }
                        image_format = format_map.get(image.mimetype, 'JPEG')
                        img.save(output, format=image_format, quality=85 if image_format == 'JPEG' else None)
                        post.image_data = output.getvalue()
                        post.image_mimetype = image.mimetype
                    os.unlink(temp_file.name)
                except UnidentifiedImageError as e:
                    logging.error(f"Cannot identify image file {image.filename}: {str(e)}")
                    return jsonify({'error': f'Invalid image file: {str(e)}'}), 400
                except Exception as e:
                    logging.error(f"Error processing image {image.filename}: {str(e)}")
                    return jsonify({'error': f'Image processing error: {str(e)}'}), 400
            else:
                post.image_data = None
                post.image_mimetype = None

        title = request.form.get('title', post.title)
        content = request.form.get('content', post.content)
        category = request.form.get('category', post.category)

        post.title = title
        post.content = content
        post.category = category
        db.session.commit()
        logging.info(f"Blog post {id} updated by user {user.id}")
        return jsonify({'message': 'Blog post updated successfully'}), 200
    except Exception as e:
        logging.error(f"Error updating blog post {id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@blog_bp.route('/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_post(id):
    try:
        claims = get_jwt()
        if claims.get('role') != 'Admin':
            return jsonify({'error': 'Admin access required'}), 403
        user = User.query.get_or_404(get_jwt_identity())
        post = BlogPost.query.get_or_404(id)
        db.session.delete(post)
        db.session.commit()
        logging.info(f"Blog post {id} deleted by user {user.id}")
        return jsonify({'message': 'Blog post deleted successfully'}), 200
    except Exception as e:
        logging.error(f"Error deleting blog post {id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@blog_bp.route('/<int:id>/comments', methods=['GET', 'OPTIONS'])
def get_comments(id):
    if request.method == 'OPTIONS':
        logging.debug(f"Handling OPTIONS for /api/blog/{id}/comments")
        response = jsonify({"status": "ok"})
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, bypass-tunnel-reminder, x-tunnel-password')
        response.headers.add('Access-Control-Max-Age', '86400')
        return response

    try:
        post = BlogPost.query.get_or_404(id)
        comments = Comment.query.filter_by(post_id=id).order_by(Comment.created_at.desc()).all()
        response = make_response(jsonify([{
            'id': c.id,
            'content': c.content,
            'username': c.username,
            'created_at': c.created_at.isoformat()
        } for c in comments]))
        response.headers['Cache-Control'] = 'public, max-age=300'
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        return response, 200
    except Exception as e:
        logging.error(f"Error fetching comments for post {id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@blog_bp.route('/<int:id>/comments', methods=['POST'])
def add_comment(id):
    try:
        post = BlogPost.query.get_or_404(id)
        data = request.get_json()
        if not data or not data.get('content') or not data.get('username'):
            return jsonify({'error': 'Username and comment content are required'}), 400
        if len(data['username']) > 100:
            return jsonify({'error': 'Username must be 100 characters or less'}), 400
        if len(data['content']) > 1000:
            return jsonify({'error': 'Comment must be 1000 characters or less'}), 400

        comment = Comment(
            post_id=id,
            user_id=None,
            username=data['username'],
            content=data['content']
        )
        db.session.add(comment)
        db.session.commit()
        logging.info(f"Comment added to post {id} by {data['username']}")
        return jsonify({'message': 'Comment added successfully', 'id': comment.id}), 201
    except Exception as e:
        logging.error(f"Error adding comment to post {id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@blog_bp.route('/<int:id>/like', methods=['POST'])
def toggle_like(id):
    try:
        post = BlogPost.query.get_or_404(id)
        ip_address = request.remote_addr or request.headers.get('X-Forwarded-For', 'unknown')
        logging.debug(f"Toggle like for post {id}, IP: {ip_address}")
        if ip_address == 'unknown':
            return jsonify({'error': 'Unable to detect IP address'}), 400
        like = Like.query.filter_by(post_id=id, ip_address=ip_address).first()
        if like:
            db.session.delete(like)
            db.session.commit()
            like_count = len(post.likes)
            logging.info(f"Like removed from post {id} by IP {ip_address}, new like_count: {like_count}")
            return jsonify({'message': 'Like removed successfully', 'like_count': like_count}), 200
        else:
            like = Like(post_id=id, user_id=None, ip_address=ip_address)
            db.session.add(like)
            db.session.commit()
            like_count = len(post.likes)
            logging.info(f"Like added to post {id} by IP {ip_address}, new like_count: {like_count}")
            return jsonify({'message': 'Like added successfully', 'like_count': like_count}), 201
    except Exception as e:
        logging.error(f"Error toggling like for post {id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500

@blog_bp.route('/<int:id>/likes', methods=['GET'])
def get_likes(id):
    try:
        post = BlogPost.query.get_or_404(id)
        ip_address = request.remote_addr or request.headers.get('X-Forwarded-For', 'unknown')
        logging.debug(f"Fetching likes for post {id}, IP: {ip_address}")
        like_count = len(post.likes)
        user_liked = Like.query.filter_by(post_id=id, ip_address=ip_address).first() is not None
        response = make_response(jsonify({
            'like_count': like_count,
            'user_liked': user_liked
        }))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        logging.info(f"Likes fetched for post {id}: like_count={like_count}, user_liked={user_liked}, IP={ip_address}")
        return response, 200
    except Exception as e:
        logging.error(f"Error fetching likes for post {id}: {str(e)}")
        return jsonify({'error': f'Internal server error: {str(e)}'}), 500