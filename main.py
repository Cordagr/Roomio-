from flask import Flask, Blueprint, render_template, request, redirect, url_for, jsonify, session
import psycopg2
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField 
from wtforms.validators import InputRequired, Length, Email
#from config import config
from flask_socketio import SocketIO, emit, join_room
#import emailVerification
import sys
import os
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import psycopg2
import uuid


your_application_ = app = Flask(__name__)
socketio = SocketIO(app)

# Add the path to the folder containing helper.py to sys.path
sys.path.insert(0, './microservices')
# Now import the module
import authentication_service
#from authentication_service import app 

from userProfileManager import userProfile_bp




def create_app():
    # Configuration
    app.config['SECRET_KEY'] = 'your_secret_key'
    jwt = JWTManager(app)

    #TODO: Implement socket rooms 
    # Initialize SocketIO
    # socketio.init_app(app)

    # Import and register blueprints or routes
    from microservices.authentication_service import auth_bp  # Assuming you create a Blueprint
    app.register_blueprint(auth_bp)

    from microservices.Property_Manager_Service import property_bp  # Assuming you create a Blueprint
    app.register_blueprint(property_bp)
   
    from microservices.settings_Manager import settings_bp
    app.register_blueprint(settings_bp)
    
    from microservices.userProfileManager import userProfile_bp 
    app.register_blueprint(userProfile_bp)

    return app


def get_db_connection():
    return psycopg2.connect(
        database="userDb",
        user="postgres",
        password="",
        host="35.184.188.68",
        port="5432"
    )




dbPassword = os.environ.get("DATABASE_PASSWORD")
app = create_app()


# Setting up sockets
#socketio = SocketIO(app)
#chats = {}

@app.route("/")
def index():
    return render_template("index.html")


def create_users_table():
    conn = psycopg2.connect(database='userDb', user='postgres', password='', host='35.184.188.68', port='5432')
    cur = conn.cursor()
    


    # Step 2: Create the table if it does not exist
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,         -- Increased length for username
            email VARCHAR(255) UNIQUE,                     -- Allow NULL for email
            password TEXT NOT NULL,                        -- Use TEXT type for long hashed passwords
            emailVerified BOOLEAN DEFAULT FALSE            -- Add email verification status
        );
    ''')
    


 # Create the friends table if it doesn't exist
    cur.execute('''
        CREATE TABLE IF NOT EXISTS friends (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            friend_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (user_id, friend_id)
            );
        ''')



    # Commit changes and close the connection
    conn.commit()
    cur.close()
    conn.close()

# Call this function to create or modify the table as necessary
create_users_table()


def modify_users_table():
    conn = psycopg2.connect(database='userDb', user='postgres', password='Coracx1234$@', host='35.184.188.68', port='5432')
    cur = conn.cursor()
    
    # Add the 'last_active' column if it does not already exist
    try:
        cur.execute('''
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
        ''')
    except Exception as e:
        print(f"Error modifying table: {e}")
    finally:
        conn.commit()
        cur.close()
        conn.close()

# Call this function to modify the table
modify_users_table()




@app.route('/home')
def home():

    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
    conn = get_db_connection()
    cursor = conn.cursor()
    unique_url = str(uuid.uuid4())
    # Fetch all columns for active users
    cursor.execute("SELECT * FROM users WHERE last_active >= %s", (ten_minutes_ago,))
    result = cursor.fetchall()  # Fetches all rows of active users

    # Debugging print to see the structure of results
    print("Query result:", result)

    # Get column names dynamically from the cursor description
    columns = [desc[0] for desc in cursor.description]

    # Convert results into a list of dictionaries for easier handling in the template
    active_users = [dict(zip(columns, row)) for row in result]

    cursor.close()
    conn.close()

    # Pass the active_users to the template
    return redirect(url_for('generated_home', unique_url=unique_url))



@app.route('/home/<unique_url>')
def generated_home(unique_url):
    # Render the page related to the dynamic UUID
    # You can use the unique_url to display data or fetch specific information tied to the UUID
    return render_template('home.html',unique_url=unique_url)






# SocketIO event to handle incoming messages
@socketio.on('connect')
def handle_connect():
    socketio.emit('status', {'message': 'Connected'}, room=request.sid)

@socketio.on('join')
def join_room(friend_id):
    socketio.join_room(friend_id)

@socketio.on('disconnect')
def handle_disconnect():
    print(f'{request.sid} disconnected')



#TODO: implement in messaging service
def get_chat_history(user_id_1, user_id_2):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT sender_id, receiver_id, message, timestamp
        FROM messages
        WHERE (sender_id = %s AND receiver_id = %s) OR (sender_id = %s AND receiver_id = %s)
        ORDER BY timestamp ASC
        """, (user_id_1, user_id_2, user_id_2, user_id_1))
    chat_history = cur.fetchall()
    cur.close()
    conn.close()
    return chat_history


def save_message(sender_id, receiver_id, message):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO messages (sender_id, receiver_id, message) 
        VALUES (%s, %s, %s)
        """, (sender_id, receiver_id, message))
    conn.commit()
    cur.close()
    conn.close()






#@socketio.on('join')
#ef on_join(data):
 #   code = data['code']
  #  username = data['username']
   # join_room(code)


if __name__ == '__main__':
    socketio.run(app,debug=True,allow_unsafe_werkzeug=True, host='0.0.0.0')
