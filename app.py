import os
from flask import Flask
from flask_login import LoginManager
from extensions import db, bcrypt

app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'

# Serverless Production Database Configuration (Writes directly to Vercel's allowed /tmp space)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- IMAGE UPLOAD CONFIGURATION ---
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'item_pics')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Automatically create structural folders safely if they do not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# ----------------------------------

# Initialize extensions
db.init_app(app)
bcrypt.init_app(app)

# Login Session Management
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

from models import User
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import all view handlers and blueprint targets 
from routes import *

# --- SERVERLESS ON-DEMAND ENGINE RUNTIME INITIALIZER ---
db_initialized = False

@app.before_request
def initialize_database_once():
    """
    Ensures database structures are verified and an administrative system account 
    is safely seeded only once per serverless environment container initialization.
    """
    global db_initialized
    if not db_initialized:
        db.create_all()
        
        # AUTOMATIC ADMIN CREATOR
        from models import User
        from extensions import bcrypt
        
        # Check if the master admin node exists before creating to prevent duplicate entries
        admin_exists = User.query.filter_by(email='admin@portal.com').first()
        if not admin_exists:
            hashed_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin_user = User(
                username='Admin',
                email='admin@portal.com',
                password=hashed_pw,
                is_admin=True  # <-- Grants full administrative rights automatically
            )
            db.session.add(admin_user)
            db.session.commit()
            print("System Notice: Fresh Admin account seeded successfully!")
        
        db_initialized = True

# Execution entry point for local development environment
if __name__ == '__main__':
    app.run(debug=True)
