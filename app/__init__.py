from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_admin import Admin
import os
from dotenv import load_dotenv
import logging

db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()


log_file = '/tmp/app.log' if os.environ.get('VERCEL') else 'app.log'
try:
    logging.basicConfig(
        level=logging.DEBUG,
        filename=log_file,
        filemode='a',
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
except OSError:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )  

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    
    try:
        os.makedirs(app.instance_path, exist_ok=True)
        logging.debug(f"Instance directory: {app.instance_path}")
    except Exception as e:
        logging.error(f"Error creating instance directory: {str(e)}")

    env_path = os.path.join(app.instance_path, '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logging.debug(f"Loaded .env from {env_path}")
    else:
        logging.warning(f".env file not found at {env_path}")

    jwt_key = os.environ.get('JWT_SECRET_KEY', 'Not set')
    logging.debug(f"JWT_SECRET_KEY (first 10 chars): {jwt_key[:10]}...")
    
    logging.debug(f"DATABASE_URL: {os.environ.get('DATABASE_URL', 'Not set')}")

    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///site.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default-secret-key')
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY')
    app.config['PAYSTACK_SECRET_KEY'] = os.environ.get('PAYSTACK_SECRET_KEY')
    app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'

    CORS(app, resources={r"/api/*": {
        "origins": [
            "http://localhost:3000",
            "https://quick-hands-dig.loca.lt",
            "https://senidea-frontend-r7hz03bkp-fortune-chinakas-projects.vercel.app",
            "https://senidea-backend-pevnhet0h-fortune-chinakas-projects.vercel.app"
        ],
        "methods": ["GET", "POST", "OPTIONS", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization", "User-Agent", "bypass-tunnel-reminder"],
        "expose_headers": ["Content-Type"],
        "supports_credentials": True,
        "send_wildcard": False,
        "automatic_options": True
    }})

    @app.before_request
    def handle_options():
        if request.method == "OPTIONS":
            response = jsonify({"status": "ok"})
            response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
            response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS, PUT, DELETE')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, bypass-tunnel-reminder, x-tunnel-password')
            response.headers.add('Access-Control-Max-Age', '86400')
            return response

    try:
        db.init_app(app)
        migrate.init_app(app, db)
        bcrypt.init_app(app)
        jwt.init_app(app)
        logging.debug("Extensions initialized successfully")
    except Exception as e:
        logging.error(f"Error initializing extensions: {str(e)}")

    with app.app_context():
        try:
            db.create_all()
            logging.debug("Database tables created")
        except Exception as e:
            logging.error(f"Error creating database tables: {str(e)}")

    from app.models import User, Content, Donation, NewsletterSubscription, ContactMessage, BlogPost, Testimonial, Partnership, Volunteer
    from app.admin.views import AdminModelView, AdminIndex

    admin = Admin(app, name='Senidea Admin', template_mode='bootstrap4', index_view=AdminIndex())
    admin.add_view(AdminModelView(User, db.session))
    admin.add_view(AdminModelView(Content, db.session))
    admin.add_view(AdminModelView(Donation, db.session))
    admin.add_view(AdminModelView(NewsletterSubscription, db.session))
    admin.add_view(AdminModelView(ContactMessage, db.session))
    admin.add_view(AdminModelView(BlogPost, db.session))
    admin.add_view(AdminModelView(Testimonial, db.session))
    admin.add_view(AdminModelView(Partnership, db.session))
    admin.add_view(AdminModelView(Volunteer, db.session))

    from app.routes.auth import auth_bp
    from app.routes.content import content_bp
    from app.routes.donation import donation_bp
    from app.routes.newsletter import newsletter_bp
    from app.routes.contact import contact_bp
    from app.routes.volunteer import volunteer_bp
    from app.routes.partnership import partnership_bp
    from app.routes.blog import blog_bp
    from app.routes.testimonial import testimonial_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(donation_bp, url_prefix='/api/donation')
    app.register_blueprint(newsletter_bp, url_prefix='/api/newsletter')
    app.register_blueprint(contact_bp, url_prefix='/api/contact')
    app.register_blueprint(volunteer_bp, url_prefix='/api/volunteer')
    app.register_blueprint(partnership_bp, url_prefix='/api/partnership')
    app.register_blueprint(blog_bp, url_prefix='/api/blog')
    app.register_blueprint(content_bp, url_prefix='/api/content')
    app.register_blueprint(testimonial_bp, url_prefix='/api/testimonial')

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        logging.error(f"Invalid token error: {str(error)}, Request URL: {request.url}")
        return jsonify({'error': 'invalid_token', 'details': str(error)}), 400

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        logging.error(f"Expired token: {jwt_payload}")
        return jsonify({'error': 'expired_token'}), 401

    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        logging.error(f"Unauthorized access: {str(error)}")
        return jsonify({'error': 'unauthorized_access'}), 401

    return app