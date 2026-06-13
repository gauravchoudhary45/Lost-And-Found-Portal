from flask import render_template, url_for, flash, redirect, request, abort
from app import app
from extensions import db, bcrypt
from models import User, LostItem, FoundItem, Claim
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime
import secrets
import os
from functools import wraps
import cloudinary

# Global expanded category list covering nearly all types 
CATEGORIES = [
    "Electronics (Phones, Laptops, Chargers)",
    "Wallets, Purses & Cash",
    "Keys & Keychains",
    "Bags, Backpacks & Luggage",
    "Clothing & Outwear",
    "Watches & Jewelry",
    "Eyewear (Glasses, Sunglasses)",
    "Books, Notebooks & Stationary",
    "IDs, Passports & Official Documents",
    "Cards (Credit, Debit, Metro)",
    "Water Bottles & Flasks",
    "Sports & Outdoor Equipment",
    "Tools & Hardware",
    "Toys & Hobbies",
    "Others" # Placed intentionally at the very end 
]

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403) 
        return f(*args, **kwargs)
    return decorated_function

def save_picture(form_file):
    if not form_file or form_file.filename == '':
        return 'no_image.jpg'
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_file.filename)
    picture_fn = random_hex + f_ext.lower()
    picture_path = os.path.join(app.config['UPLOAD_FOLDER'], picture_fn)
    form_file.save(picture_path)
    return picture_fn

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))
@app.route("/dashboard")
@login_required
def dashboard():
    lost_items = LostItem.query.filter_by(user_id=current_user.id).order_by(LostItem.date_posted.desc()).all()
    found_items = FoundItem.query.filter_by(user_id=current_user.id).order_by(FoundItem.date_posted.desc()).all()
    claims = Claim.query.filter_by(user_id=current_user.id).order_by(Claim.date_submitted.desc()).all()
    return render_template('dashboard.html', title='My Dashboard', lost_items=lost_items, found_items=found_items, claims=claims)


@app.route("/report-lost", methods=['GET', 'POST'])
@login_required
def report_lost():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        location = request.form.get('location')
        category = request.form.get('category')
        
        item = LostItem(title=title, description=description, location=location, category=category, user_id=current_user.id)
        db.session.add(item)
        db.session.commit()
        flash('Your missing property profile configuration has been broadcasted!', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('report_lost.html', title='Report Lost Item')


@app.route("/post-found", methods=['GET', 'POST'])
@login_required
def post_found():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        location = request.form.get('location')
        category = request.form.get('category')
        image_file = request.files.get('image_file')
        
        # Default high-res fallback geometry if no snapshot image is provided
        cloud_image_url = "https://images.unsplash.com/photo-1530541930197-ff16ac917b0e?w=500"
        
        if image_file and image_file.filename != '':
            try:
                # Stream binary data directly into the Cloudinary pipeline
                upload_result = cloudinary.uploader.upload(image_file)
                cloud_image_url = upload_result.get('secure_url')
            except Exception as e:
                flash(f"Cloud serverless pipeline failed. Error context: {str(e)}", 'warning')

        item = FoundItem(title=title, description=description, location=location, category=category, image_file=cloud_image_url, user_id=current_user.id)
        db.session.add(item)
        db.session.commit()
        flash('Discovered found asset recorded accurately!', 'success')
        return redirect(url_for('search'))
        
    return render_template('post_found.html', title='Post Found Asset')


@app.route("/search")
@login_required
def search():
    query = request.args.get('q', '')
    if query:
        # Relational SQL Wildcard scanning structure cross-queries all text metrics
        found_items = FoundItem.query.filter(
            (FoundItem.title.ilike(f'%{query}%')) | 
            (FoundItem.description.ilike(f'%{query}%')) | 
            (FoundItem.location.ilike(f'%{query}%'))
        ).order_by(FoundItem.is_claimed.asc(), FoundItem.date_posted.desc()).all()
    else:
        found_items = FoundItem.query.order_by(FoundItem.is_claimed.asc(), FoundItem.date_posted.desc()).all()
        
    return render_template('search.html', title='Search Portal', found_items=found_items, search_query=query)


@app.route("/item/<int:item_id>/claim", methods=['GET', 'POST'])
@login_required
def claim_item(item_id):
    item = FoundItem.query.get_or_404(item_id)
    if item.is_claimed:
        flash('This item asset matrix has been claimed and archived.', 'info')
        return redirect(url_for('search'))
        
    if request.method == 'POST':
        proof_text = request.form.get('proof_text')
        proof_image = request.files.get('proof_image')
        
        cloud_proof_url = None
        if proof_image and proof_image.filename != '':
            try:
                upload_result = cloudinary.uploader.upload(proof_image)
                cloud_proof_url = upload_result.get('secure_url')
            except Exception as e:
                flash(f"Cloud upload failure code exception: {str(e)}", 'danger')
                return render_template('claim.html', item=item)

        new_claim = Claim(proof_text=proof_text, proof_image=cloud_proof_url, user_id=current_user.id, item_id=item.id)
        db.session.add(new_claim)
        db.session.commit()
        flash('Ownership verification challenge dispatched successfully!', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('claim.html', item=item)

@app.route("/admin/claims")
@login_required
@admin_required
def admin_claims_dashboard():
    all_claims = Claim.query.order_by(Claim.date_created.desc()).all()
    return render_template('admin_claims.html', claims=all_claims, title="Manage Claims")

@app.route("/admin/claim/<int:claim_id>/<string:action>")
@login_required
@admin_required
def process_claim_action(claim_id, action):
    claim = Claim.query.get_or_404(claim_id)
    if action == 'approve':
        claim.status = 'Approved / Authorized'
        flash(f"Claim #{claim.id} approved. Contact details released.", "success")
    elif action == 'reject':
        claim.status = 'Rejected / Invalid Proof'
        flash(f"Claim #{claim.id} marked as rejected.", "warning")
    db.session.commit()
    return redirect(url_for('admin_claims_dashboard'))

@app.route("/admin/portal")
@login_required
@admin_required
def admin_portal_dashboard():
    """
    HQ Control Center Home: Displays critical system metrics (total system 
    counts and open requests) to provide administrative analytical visibility.
    """
    total_users = User.query.count()
    total_lost = LostItem.query.count()
    total_found = FoundItem.query.count()
    pending_claims = Claim.query.filter_by(status='Pending Verification').count()
    
    # Grab recent system logs to populate an audit feed
    recent_claims = Claim.query.order_by(Claim.date_created.desc()).limit(5).all()
    
    return render_template(
        'admin_portal.html', 
        users_count=total_users, 
        lost_count=total_lost, 
        found_count=total_found, 
        pending_count=pending_claims,
        recent_claims=recent_claims,
        title="Admin Hub"
    )


@app.route("/admin/users")
@login_required
@admin_required
def admin_users_management():
    """
    User Clerical Center: Displays all registered accounts and handles 
    in-app security clearance promotions directly.
    """
    all_users = User.query.order_by(User.username.asc()).all()
    return render_template('admin_users.html', users=all_users, title="User Clearance Matrix")


@app.route("/admin/users/toggle/<int:user_id>")
@login_required
@admin_required
def toggle_user_admin_status(user_id):
    """
    Modifies security clearance. Prevents administrative lockouts by restricting 
    users from demoting their own active accounts.
    """
    target_user = User.query.get_or_404(user_id)
    
    if target_user.id == current_user.id:
        flash("Security Conflict: You cannot revoke admin access from your own current session profile.", "danger")
        return redirect(url_for('admin_users_management'))
        
    # Invert the database boolean switch
    target_user.is_admin = not target_user.is_admin
    db.session.commit()
    
    status_label = "Elevated to System Admin" if target_user.is_admin else "Revoked to Regular Status"
    flash(f"User profile context for {target_user.username} altered: {status_label}.", "success")
    return redirect(url_for('admin_users_management'))
