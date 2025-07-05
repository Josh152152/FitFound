from flask import Blueprint, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

bp = Blueprint('auth', __name__)

# User registration
@bp.route('/signup', methods=['POST'])
def signup():
    email = request.form['email']
    password = request.form['password']
    hashed_pw = generate_password_hash(password, method='sha256')
    user_type = request.form['type']  # candidate or employer
    # Add to Users2 sheet or local DB
    db.session.add(User(email=email, password=hashed_pw, type=user_type))
    db.session.commit()
    return redirect(url_for('auth.login'))

# User login
@bp.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    # Check password from Users2 sheet or local DB
    return redirect(url_for('dashboard'))
