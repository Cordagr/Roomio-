from flask import Blueprint, render_template, redirect, url_for, flash, session, jsonify, current_app
from flask_mail import Mail, Message
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField
from wtforms.validators import InputRequired, Length, Email
from werkzeug.security import generate_password_hash
import psycopg2
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
import sys
import uuid


auth_bp = Blueprint('auth', __name__)
mail = Mail()
s = None  # Will be initialized in app context

# Add the path to the folder containing helper.py to sys.path
sys.path.insert(0, './microservices')
# Now import the module
import userProfileManager


# Database connection function
def get_db_connection():
    conn = psycopg2.connect(
        database="userDb",  
        user="postgres",                 
        password="",             
        host="35.184.188.68",
        port="5432"
    )
    return conn

# Function to update last active timestamp
def update_last_active():
    user_id = session.get('user_id')
    if user_id:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET last_active = %s WHERE id = %s", (datetime.now(), user_id))
        conn.commit()
        cursor.close()
        conn.close()

def generate_unique_url():
    return str(uuid.uuid4())



# Register before_request handler to update last active timestamp
@auth_bp.before_request
def before_request():
    if 'user_id' in session:
        update_last_active()


# Registration form
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=80)])
    submit = SubmitField('Register')

# Login form
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=4, max=15)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=8, max=80)])
    submit = SubmitField('Login')

# Email verification function
def send_verification_email(email):
    with current_app.app_context():
        token = s.dumps(email)
        verification_link = f"http://localhost:5000/auth/verify_email/{token}"
        subject = "Please confirm your email"
        body = f"Hello, please click the following link to verify your email: {verification_link}"
        msg = Message(subject, recipients=[email])
        msg.body = body
        try:
            mail.send(msg)
            return "Verification email sent!", 200
        except Exception as e:
            return f"Error sending email: {str(e)}", 500

# Registration route
#DONE
@auth_bp.route('/registerUser', methods=['GET', 'POST'])
def registerUser():
    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        #hashed_password = generate_password_hash(password)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                try:
                    # Check if the username already exists
                    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                    existing_user = cur.fetchone()
                    if existing_user:
                        flash("Username is already taken. Please choose another.", "error")
                        return redirect(url_for('auth.registerUser'))

                    # Insert new user into the users table
                    cur.execute(
                        "INSERT INTO users (username, password, emailVerified) VALUES (%s, %s, %s) RETURNING id",
                        (username, password, True)
                    )
                    user_id = cur.fetchone()[0]
                    session['username'] = username
                    session['user_id'] = user_id

                
                    return redirect(url_for('userProfile.setUpUserProfile'))
                    

                    # If profile exists (shouldn't happen for new users), redirect to home
                    flash("Registration completed successfully!", "success")
                    #return render_template('home.html')

                except Exception as e:
                    conn.rollback()
                    flash("An error occurred during registration. Please try again.", "error")
                    return redirect(url_for('auth.registerUser'))

    return render_template('registerUser.html', form=form)


# Login route
#DONE
@auth_bp.route('/loginUser', methods=['GET', 'POST'])
def loginUser():
    form = LoginForm()
    
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                try:
                    
                    cur.execute(
                        "SELECT id, password FROM users WHERE username = %s",
                        (username,)
                    )
                    
                    
                    user = cur.fetchone()
                    # Now, user is guaranteed to be a tuple
                    user_password = user[1]

                    if user and user_password == password:  # Directly compare passwords
                        print("W")
                        access_token = create_access_token(identity = user[0])
                        session['username'] = username
                        session['access_token'] = access_token
                        session['user_id'] = user[0]
                        flash("Login successful!", "success")
                        return render_template('home.html')
                    else:
                       
                        flash("Invalid username or password.", "danger")
                except Exception as e:
                    print(f"Error during login: {e}")  # Log the error for debugging
                    flash("An error occurred. Please try again.", "danger")

    return render_template('loginUser.html', form=form)



#DONE
@auth_bp.route('/logoutUser', methods=['GET','POST'])
def logoutUser():
# clear jwt token
    session.clear() 
    flash("Successful logout")
    return render_template('index.html')

# Email registration route
@auth_bp.route('/register_email', methods=['GET', 'POST'])
def register_email():
    form = EmailForm()
    if form.validate_on_submit():
        email = form.email.data
        session['verifiedEmail'] = email
        send_verification_email(email)
        flash("Verification email sent. Please check your inbox.", "success")
        return redirect(url_for('auth.loginUser'))

    return render_template('registerEmail.html', form=form)

# Success page route
@auth_bp.route('/success', methods=['GET'])
def success_page():
    return "Registration successful!", 200
