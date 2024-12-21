from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask import Blueprint
import psycopg2
from werkzeug.security import generate_password_hash

# Blueprint for settings
settings_bp = Blueprint('settings', __name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'



# Default user settings
settings = {
    'in_app_notifications': 'disabled',
    'out_of_app_notifications': 'disabled',
    'profile_visibility': 'enabled'
}


# Database connection utility
def get_db_connection():
    conn = psycopg2.connect(
        database="userSettingsDb",  # Your database name
        user="postgres",         # Your database username
        password="",  # Your database password
        host="35.184.188.68",
        port="5432"
    )
    return conn



def create_user_settings_table():
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Check if the user_settings table exists
        cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name='user_settings'")
        table_exists = cur.fetchone() is not None
        
        if table_exists:
            print("Table exists; modifying 'user_settings' table.")
            
            # Check if the required columns exist
            columns_to_check = ['user_id', 'key', 'value']
            for column in columns_to_check:
                cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='user_settings' AND column_name='{column}'")
                column_exists = cur.fetchone() is not None
                
                # If a column doesn't exist, add it
                if not column_exists:
                    print(f"Adding '{column}' column to 'user_settings' table.")
                    cur.execute(f"ALTER TABLE user_settings ADD COLUMN {column} VARCHAR(255)")
            
            # Optionally, ensure other columns are the correct type
            cur.execute(''' 
                ALTER TABLE user_settings 
                ALTER COLUMN user_id TYPE INTEGER,
                ALTER COLUMN key TYPE VARCHAR(255),
                ALTER COLUMN value TYPE VARCHAR(255);
            ''')
        else:
            # If table does not exist, create it
            print("Table does not exist; creating 'user_settings' table.")
            cur.execute('''
                CREATE TABLE user_settings (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,  -- User ID
                    key VARCHAR(255) NOT NULL,  -- Setting key
                    value VARCHAR(255) NOT NULL, -- Setting value
                    UNIQUE (user_id, key)  -- Ensure unique user settings
                );
            ''')
    
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    
    # Commit changes and close the connection
    conn.commit()
    cur.close()
    conn.close()

# Run the function to create or alter the table
create_user_settings_table()



# Initialize user settings
def initialize_user_settings(user_id):
    conn = get_db_connection()
    cur = conn.cursor()

    for key, value in settings.items():
        cur.execute("INSERT INTO user_settings (user_id, key, value) VALUES (%s, %s, %s)", (user_id, key, value))

    conn.commit()
    conn.close()


# Toggle any setting
def toggle_user_setting(user_id, setting_key, current_value, enable_value='enabled', disable_value='disabled'):
    conn = get_db_connection()
    cur = conn.cursor()

    new_value = disable_value if current_value == enable_value else enable_value

    if current_value:
        cur.execute("UPDATE user_settings SET value = %s WHERE user_id = %s AND key = %s", (new_value, user_id, setting_key))
    else:
        cur.execute("INSERT INTO user_settings (user_id, key, value) VALUES (%s, %s, %s)", (user_id, setting_key, new_value))

    conn.commit()
    conn.close()

    return new_value

# Fetch user settings from the db
def get_user_settings(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT key, value FROM user_settings WHERE user_id = %s", (user_id,))
    settings = dict(cur.fetchall())
    conn.close()
    return settings

@settings_bp.route('/userSettings', methods=['GET'])
def render_user_settings():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('auth.loginUser'))

    # Check if settings are initialized for the user
    settings = get_user_settings(user_id)
    if not settings:
        # Initialize settings if none exist
        initialize_user_settings(user_id)
        settings = get_user_settings(user_id)  # Re-fetch after initialization

    return render_template('userSettings.html', settings=settings)




# Toggle in-app notifications
@settings_bp.route('/notifications/in-app/toggle', methods=['POST'])
def toggle_in_app_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM user_settings WHERE user_id = %s AND key = 'in_app_notifications'", (user_id,))
    current_setting = cur.fetchone()

    toggle_user_setting(user_id, 'in_app_notifications', current_setting[0] if current_setting else None)

    return redirect(url_for('settings.render_user_settings'))

# Toggle out-of-app notifications
@settings_bp.route('/notifications/out-of-app/toggle', methods=['POST'])
def toggle_out_of_app_notifications():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM user_settings WHERE user_id = %s AND key = 'out_of_app_notifications'", (user_id,))
    current_setting = cur.fetchone()

    toggle_user_setting(user_id, 'out_of_app_notifications', current_setting[0] if current_setting else None)

    return redirect(url_for('settings.render_user_settings'))

# Toggle profile visibility
@settings_bp.route('/profile/visibility/toggle', methods=['POST'])
def toggle_profile_visibility():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM user_settings WHERE user_id = %s AND key = 'profile_visibility'", (user_id,))
    current_setting = cur.fetchone()

    toggle_user_setting(user_id, 'profile_visibility', current_setting[0] if current_setting else None)

    return redirect(url_for('settings.render_user_settings'))

# Register the Blueprint with the app
app.register_blueprint(settings_bp)

# Run the application
if __name__ == '__main__':
    app.run(debug=True)
