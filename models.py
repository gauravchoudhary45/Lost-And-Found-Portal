from datetime import datetime
from extensions import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    
    lost_items = db.relationship('LostItem', backref='owner', lazy=True)
    found_items = db.relationship('FoundItem', backref='finder', lazy=True)
    claims_submitted = db.relationship('Claim', backref='claimant', lazy=True)


class LostItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(150), nullable=False) # Changed to support manual strings
    date_lost = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.String(40), nullable=False, default='no_image.jpg')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


class FoundItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(150), nullable=False) # Changed to support manual strings
    date_found = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    description = db.Column(db.Text, nullable=False) 
    image_file = db.Column(db.String(40), nullable=False, default='no_image.jpg')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    claims = db.relationship('Claim', backref='item', lazy=True)


class Claim(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    proof_of_ownership = db.Column(db.Text, nullable=False)
    image_proof = db.Column(db.String(40), nullable=False, default='no_proof.jpg')
    status = db.Column(db.String(30), nullable=False, default='Pending Verification')
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    found_item_id = db.Column(db.Integer, db.ForeignKey('found_item.id'), nullable=False)