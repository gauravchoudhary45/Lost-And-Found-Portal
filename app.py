import os
from flask import Flask
from flask_login import LoginManager
from extensions import db, bcrypt

app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- ADDED FOR IMAGE UPLOADS ---
# Configures the storage path: C:\Lost and found\static\item_pics
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'item_pics')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Automatically create the folders if they don't exist yet
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# -------------------------------

db.init_app(app)
bcrypt.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

from models import User
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

from routes import *

# Near the bottom of app.py
with app.app_context():
    db.create_all()
    
    # AUTOMATIC ADMIN CREATOR
    from models import User
    from extensions import bcrypt
    
    # Check if an admin already exists so we don't duplicate it
    admin_exists = User.query.filter_by(email='admin@portal.com').first()
    if not admin_exists:
        hashed_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
        admin_user = User(
            username='Admin',
            email='admin@portal.com',
            password=hashed_pw,
            is_admin=True  # <-- Grants full rights immediately
        )
        db.session.add(admin_user)
        db.session.commit()
        print("System Notice: Fresh Admin account seeded successfully!")


if __name__ == '__main__':
    app.run(debug=True)
else:
    # This exposes the application variable context directly to Vercel's wrapper
    app = app