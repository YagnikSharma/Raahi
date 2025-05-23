import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash
from app import db
from models import User
from utils import send_password_reset_email, send_admin_confirmation_email

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.check_password(password):
            flash('Please check your login details and try again.', 'danger')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=remember)
        user.last_login = datetime.datetime.utcnow()
        db.session.commit()
        
        # Redirect to the page the user was trying to access
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('admin.dashboard')
        
        flash('Login successful!', 'success')
        return redirect(next_page)
    
    return render_template('admin/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('public.index'))

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            if send_password_reset_email(user):
                flash('A password reset link has been sent to your email.', 'info')
            else:
                flash('There was a problem sending the reset email. Please try again later.', 'danger')
        else:
            # Don't reveal whether an email exists
            flash('If that email address is in our system, a password reset link has been sent.', 'info')
        
        return redirect(url_for('auth.login'))
    
    return render_template('admin/reset_password.html', request_type='forgot')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()
    
    # Check if token is valid and not expired
    if not user or not user.reset_token_expiry or user.reset_token_expiry < datetime.datetime.utcnow():
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('admin/reset_password.html', token=token, request_type='reset')
        
        # Update password and clear reset token
        user.set_password(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()
        
        flash('Your password has been updated! You can now log in with your new password.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('admin/reset_password.html', token=token, request_type='reset')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Admin registration with email confirmation to primary admin"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        full_name = request.form.get('full_name', username)
        
        # Validation
        if not all([username, email, password, confirm_password]):
            flash('All fields are required.', 'danger')
            return render_template('admin/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('admin/register.html')
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email address already registered.', 'danger')
            return render_template('admin/register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return render_template('admin/register.html')
        
        # Create new admin user (pending approval)
        new_admin = User(
            username=username,
            email=email,
            is_admin=False  # Will be activated after approval
        )
        new_admin.set_password(password)
        
        db.session.add(new_admin)
        db.session.commit()
        
        # Send confirmation email to primary admin
        if send_admin_confirmation_email(email, full_name):
            flash('Registration successful! Your account is pending approval. The primary admin has been notified.', 'success')
        else:
            flash('Registration successful! However, email notification failed. Please contact the primary admin.', 'warning')
        
        return redirect(url_for('auth.login'))
    
    return render_template('admin/register.html')
