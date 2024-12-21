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



auth_bp = Blueprint('messagingService', __name__)
mail = Mail()
s = None  # Will be initialized in app context

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

def save_message(sender_id, receiver_id, message):
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Insert the message into the database
    cur.execute(
        "INSERT INTO messages (sender_id, receiver_id, message) VALUES (%s, %s, %s)",
        (sender_id, receiver_id, message)
    )
    
    # Commit the transaction and close the connection
    conn.commit()
    cur.close()
    conn.close()




#TODO: Implement chatting service for in between friends 
@auth_bp.route('/chat', methods=['GET', 'POST'])
def chat():
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to chat.", "error")
        return redirect(url_for('auth.login_user'))

    receiver_username = request.args.get('receiver')  # Retrieve receiver's username from query params
    if not receiver_username:
        flash("Receiver username is required.", "error")
        return redirect(url_for('home'))  # Redirect to home if no receiver is specified

    # Get receiver's user_id from the database
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = %s", (receiver_username,))
    receiver = cur.fetchone()
    cur.close()
    conn.close()

    if not receiver:
        flash(f"Receiver {receiver_username} not found.", "error")
        return redirect(url_for('home'))

    receiver_id = receiver[0]

    # Handle sending a message (POST request)
    if request.method == 'POST':
        message = request.form.get('message')
        if not message:
            flash("Message cannot be empty", "error")
            return redirect(url_for('auth.chat', receiver=receiver_username))

        # Save message in the database
        save_message(user_id, receiver_id, message)

        flash("Message sent successfully.", "success")
        return redirect(url_for('auth.chat', receiver=receiver_username))

    # Fetch chat history between the two users
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT sender_id, receiver_id, message, timestamp
        FROM messages
        WHERE (sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)
        ORDER BY timestamp ASC
    """, (user_id, receiver_id, receiver_id, user_id))
    chat_history = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('chat.html', chat_history=chat_history, receiver_username=receiver_username)




#TODO: Implement messaging service that will notify users in a in application inbox after things like succesffully sigining up 

#TODO: Implement in the same messaging service a notification seperate from from lets say signing up to show an interactable redirection link to a users profile if added as a freind

#TODO: Implement the ability to accept anothers users request to become friends 