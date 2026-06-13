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
import cloudinary.uploader

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

# ==========================================
# 1. CORE AUTHENTICATION AND INDEX ROUTES
# ==========================================

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route("/dashboard")
@login_required
def dashboard():
    user_lost = current_user.lost_items
    user_claims = current_user.claims_submitted
    return render_template('dashboard.html', lost_items=user_lost, claims=user_claims, title="Dashboard")

@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email', '').strip().lower() # Normalize email string
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password') # Capture confirmation
        
        # 1. SECURITY CHECK: Confirm Password Validation
        if password != confirm_password:
            flash('Password mismatch detected! Please match both password fields.', 'danger')
            return redirect(url_for('register'))
            
        # 2. SECURITY CHECK: Domain Restriction Enforcement
        if not email.endswith('@gmail.com'):
            flash('Registration Rejected: You must use a valid @gmail.com address to register.', 'danger')
            return redirect(url_for('register'))
        
        # 3. DATABASE CHECK: Verify Duplication Conflicts
        user_exists = User.query.filter((User.username == username) | (User.email == email)).first()
        if user_exists:
            flash('That username or email is already taken!', 'danger')
            return redirect(url_for('register'))
        
        # Save record securely if all criteria checks pass successfully
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully! You can now log in.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html', title='Create Account')


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower() # Normalize email inputs
        password = request.form.get('password')
        
        # 1. GATEKEEPER EXCEPTION: Allow master admin or strictly enforce @gmail.com domain
        if email != 'admin@portal.com' and not email.endswith('@gmail.com'):
            flash('Access Denied: Invalid email authorization credentials.', 'danger')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Welcome back!', 'success')
            if user.is_admin:
                return redirect(url_for('admin_portal_dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check credentials.', 'danger')
            
    return render_template('login.html', title='Login')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ==========================================
# 2. PROPERTY REPORTING PLUGINS (CLOUDINARY READY)
# ==========================================

@app.route("/report-lost", methods=['GET', 'POST'])
@login_required
def report_lost():
    if request.method == 'POST':
        date_raw = request.form.get('date')
        try:
            parsed_date = datetime.strptime(date_raw, '%Y-%m-%d').date() if date_raw else datetime.utcnow().date()
        except ValueError:
            parsed_date = datetime.utcnow().date()
            
        file = request.files.get('item_image')
        image_url = "https://images.unsplash.com/photo-1595079676339-1534801ad6cf?w=500" # Lost fallback graphic

        if file and file.filename != '':
            try:
                upload_result = cloudinary.uploader.upload(file)
                image_url = upload_result.get('secure_url')
            except Exception as e:
                print(f"Cloudinary lost upload trace error: {str(e)}")

        lost_log = LostItem(
            title=request.form.get('title'),
            category=request.form.get('category'),
            location=request.form.get('location'), 
            date_lost=parsed_date,
            description=request.form.get('description'),
            image_file=image_url,
            owner=current_user
        )
        db.session.add(lost_log)
        db.session.commit()
        flash('Lost item reported successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('report_lost.html', categories=CATEGORIES, title='Report Lost Item')


@app.route("/post-found", methods=['GET', 'POST'])
@login_required
def post_found():
    if request.method == 'POST':
        date_raw = request.form.get('date')
        try:
            parsed_date = datetime.strptime(date_raw, '%Y-%m-%d').date() if date_raw else datetime.utcnow().date()
        except ValueError:
            parsed_date = datetime.utcnow().date()
            
        file = request.files.get('item_image')
        image_url = "https://images.unsplash.com/photo-1530541930197-ff16ac917b0e?w=500" # Found fallback graphic

        if file and file.filename != '':
            try:
                upload_result = cloudinary.uploader.upload(file)
                image_url = upload_result.get('secure_url')
            except Exception as e:
                print(f"Cloudinary found upload trace error: {str(e)}")

        # FIXED CORE MODEL BUG: Changed from LostItem to FoundItem
        found_log = FoundItem(
            title=request.form.get('title'),
            category=request.form.get('category'),
            location=request.form.get('location'), 
            date_found=parsed_date,
            description=request.form.get('description'),
            image_file=image_url,
            finder=current_user
        )
        db.session.add(found_log)
        db.session.commit()
        flash('Found item notice posted successfully!', 'success')
        return redirect(url_for('search_discover'))
    return render_template('post_found.html', categories=CATEGORIES, title='Post Found Item')

# ==========================================
# 3. INTERACTIVE DISCOVERY & VERIFICATION CLAIMS
# ==========================================

@app.route("/discover")
@login_required
def search_discover():
    query_str = request.args.get('q', '')
    category_filter = request.args.get('category', '')
    location_filter = request.args.get('location', '')
    
    found_query = FoundItem.query
    
    if query_str:
        found_query = found_query.filter(
            (FoundItem.title.ilike(f'%{query_str}%')) | 
            (FoundItem.description.ilike(f'%{query_str}%'))
        )
    if category_filter:
        found_query = found_query.filter_by(category=category_filter)
    if location_filter:
        found_query = found_query.filter(FoundItem.location.ilike(f'%{location_filter}%'))
        
    results = found_query.all()

    unclaimed_items = []
    claimed_items = []
    
    for item in results:
        is_already_claimed = any(c.status == 'Approved / Authorized' for c in item.claims)
        if is_already_claimed:
            claimed_items.append(item)
        else:
            unclaimed_items.append(item)

    return render_template(
        'search.html', 
        unclaimed=unclaimed_items, 
        claimed=claimed_items, 
        categories=CATEGORIES, 
        title='Discover Items'
    )


@app.route("/claim/<int:item_id>", methods=['GET', 'POST'])
@login_required
def claim_item(item_id):
    target_item = FoundItem.query.get_or_404(item_id)
    
    # Block redundant claims if already authorized
    if any(c.status == 'Approved / Authorized' for c in target_item.claims):
        flash('This item has already been successfully resolved.', 'info')
        return redirect(url_for('search_discover'))

    if request.method == 'POST':
        file = request.files.get('proof_image')
        saved_filename_url = "https://images.unsplash.com/photo-1554415707-6e8cfc93fe23?w=500" # Default invoice proof icon

        if file and file.filename != '':
            try:
                upload_result = cloudinary.uploader.upload(file)
                saved_filename_url = upload_result.get('secure_url')
            except Exception as e:
                print(f"Cloudinary claim validation file upload failure: {str(e)}")
        
        verification = Claim(
            proof_of_ownership=request.form.get('proof'),
            image_proof=saved_filename_url, # Now saving secure long web string URL
            status="Pending Verification",
            claimant=current_user,
            item=target_item
        )
        db.session.add(verification)
        db.session.commit()
        flash('Verification claim submitted successfully.', 'info')
        return redirect(url_for('dashboard'))
    return render_template('claim.html', item=target_item, title='File Claim')

# ==========================================
# 4. ISOLATED SYSTEM CONTROL ADMINISTRATIVE HEADQUARTERS
# ==========================================

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
    total_users = User.query.count()
    total_lost = LostItem.query.count()
    total_found = FoundItem.query.count()
    pending_claims = Claim.query.filter_by(status='Pending Verification').count()
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
    all_users = User.query.order_by(User.username.asc()).all()
    return render_template('admin_users.html', users=all_users, title="User Clearance Matrix")


@app.route("/admin/users/toggle/<int:user_id>")
@login_required
@admin_required
def toggle_user_admin_status(user_id):
    target_user = User.query.get_or_404(user_id)
    
    if target_user.id == current_user.id:
        flash("Security Conflict: You cannot revoke admin access from your own current session profile.", "danger")
        return redirect(url_for('admin_users_management'))
        
    target_user.is_admin = not target_user.is_admin
    db.session.commit()
    
    status_label = "Elevated to System Admin" if target_user.is_admin else "Revoked to Regular Status"
    flash(f"User profile context for {target_user.username} altered: {status_label}.", "success")
    return redirect(url_for('admin_users_management'))
