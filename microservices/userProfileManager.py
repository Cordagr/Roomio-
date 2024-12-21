
from flask import Flask, Blueprint, render_template, request, redirect, url_for, jsonify, session, flash
from flask import Blueprint
import psycopg2
from werkzeug.security import generate_password_hash
import sys
import uuid
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField, SelectField, BooleanField
from wtforms.validators import InputRequired, Length, Email, Optional
from flask_socketio import SocketIO, send
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import Optional



class UserFilterForm(FlaskForm):
    # Inclusion criteria
    allergies = StringField('Allergies')
    smoker = SelectField('Smoker', choices=[('yes', 'yes'), ('no', 'no')], default=None)
    chore_preferences = StringField('Chore Preferences')
    cooking = StringField('Cooking')
    owned_pets = StringField('Owned Pets')
    

    # Submit button
    apply_filters = SubmitField('Apply Filters')
    apply_exclusion_filters = SubmitField('Apply Filters (Exclusion)')



# Blueprint for user profile
userProfile_bp = Blueprint('userProfile', __name__, template_folder='templates')


app = Flask(__name__)


# Add the path to the folder containing helper.py to sys.path
sys.path.insert(0, './microservices')
# Now import the module
import Property_Manager_Service



# Seperate Friend table


# View for displaying active users
@userProfile_bp.route('/activeUsers', methods=['GET'])
def activeUsers():
    """
    Display a list of active users, excluding the logged-in user.
    """
    logged_in_user = session.get('username')
    if not logged_in_user:
        flash("You must be logged in to view active users.", "error")
        return redirect(url_for('auth.loginUser'))

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Fetch all active users except the logged-in user
        cur.execute('''
            SELECT username, profile_picture
            FROM userProfile
            WHERE username != %s
        ''', (logged_in_user,))
        users = cur.fetchall()
        print(active_users)

        return render_template('home.html', users=users)

    except Exception as e:
        print(f"Error fetching active users: {e}")
        flash("An error occurred while fetching active users.", "error")
        return redirect(url_for('home'))
    finally:
        cur.close()
        conn.close()



def get_user_db():
    conn = psycopg2.connect(
        database="userDb",  # Your database name
        user="postgres",         # Your database username
        password="",  # Your database password
        host="35.184.188.68",
        port="5432"
    )
    return conn


# Database connection utility
def get_db_connection():
    conn = psycopg2.connect(
        database="userProfileDb",  # Your database name
        user="postgres",         # Your database username
        password="",  # Your database password
        host="35.184.188.68",
        port="5432"
    )
    return conn


def get_userFriends_db_connection():
    conn = psycopg2.connect(
        database="userFriendDb",  # Your database name
        user="postgres",         # Your database username
        password="",  # Your database password
        host="35.184.188.68",
        port="5432"
    )
    return conn



def createUserProfileTable():
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Check if the 'userProfile' table exists
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE LOWER(table_name)='userprofile')")
        user_profile_exists = cur.fetchone()[0]

        if user_profile_exists:
            print("'userProfile' table exists. Checking for required columns...")

            # Check if 'profile_setup' column exists
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns 
                WHERE table_name = 'userprofile' AND column_name = 'profile_setup'
            """)
            profile_setup_column_exists = cur.fetchone()

            if not profile_setup_column_exists:
                print("'profile_setup' column does not exist in 'userProfile'. Adding it now.")
                cur.execute("ALTER TABLE userProfile ADD COLUMN profile_setup BOOLEAN DEFAULT FALSE;")
                print("'profile_setup' column added successfully.")
            else:
                print("'profile_setup' column already exists in 'userProfile'. No changes needed.")
        else:
            print("'userProfile' table does not exist. Creating it now.")
            cur.execute('''
                CREATE TABLE userProfile (
                    user_id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    allergies TEXT,
                    smoker BOOLEAN,
                    chore_preferences TEXT,
                    cooking VARCHAR(50),
                    owned_pets TEXT,
                    profile_picture TEXT,
                    profile_setup BOOLEAN DEFAULT FALSE  -- Token to track if profile is set up
                );
            ''')
            print("'userProfile' table created successfully.")

        # Check if the 'saved_properties' table exists
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE LOWER(table_name)='saved_properties')")
        saved_properties_exists = cur.fetchone()[0]

        if not saved_properties_exists:
            print("'saved_properties' table does not exist. Creating it now.")
            cur.execute('''
                CREATE TABLE saved_properties (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    property_id INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES userProfile(user_id),
                    FOREIGN KEY (property_id) REFERENCES properties(id),
                    UNIQUE (user_id, property_id)
                );
            ''')
            print("'saved_properties' table created successfully.")
        else:
            print("'saved_properties' table already exists. No changes needed.")

    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()

    finally:
        # Commit changes and close the connection
        conn.commit()
        cur.close()
        conn.close()

createUserProfileTable()

import psycopg2



def createFriendRequestsTable():
    """
    Ensure the 'friend_requests' table exists with all required columns.
    If the table or specific columns are missing, create/add them in the separate database.
    """
    conn = get_userFriends_db_connection()
    cur = conn.cursor()

    try:
        # Check if the 'friend_requests' table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' AND LOWER(table_name) = 'friend_requests'
            )
        """)
        friend_requests_exists = cur.fetchone()[0]

        if friend_requests_exists:
            print("'friend_requests' table exists. Checking for required columns...")

            # Required columns and their definitions for the 'friend_requests' table
            required_columns = {
                "id": "SERIAL PRIMARY KEY",
                "sender_id": "INTEGER NOT NULL",
                "receiver_id": "INTEGER NOT NULL",
                "message": "TEXT",
                "status": "VARCHAR(20) DEFAULT 'pending'",  # Status could be 'pending', 'accepted', or 'rejected'
                "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
            }

            for column, definition in required_columns.items():
                # Check if the column exists in the table
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns 
                        WHERE table_schema = 'public' AND table_name = 'friend_requests' AND column_name = %s
                    )
                """, (column,))
                column_exists = cur.fetchone()[0]

                if not column_exists:
                    print(f"'{column}' column does not exist in 'friend_requests'. Adding it now.")
                    cur.execute(f"ALTER TABLE friend_requests ADD COLUMN {column} {definition};")
                    print(f"'{column}' column added successfully.")
                else:
                    print(f"'{column}' column already exists in 'friend_requests'. No changes needed.")
        else:
            print("'friend_requests' table does not exist. Creating it now.")
            cur.execute('''
                CREATE TABLE friend_requests (
                    id SERIAL PRIMARY KEY,
                    sender_id INTEGER NOT NULL,
                    receiver_id INTEGER NOT NULL,
                    message TEXT,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            print("'friend_requests' table created successfully.")

        conn.commit()  # Commit changes to the friend requests DB
    except Exception as e:
        print(f"An error occurred: {e}")
        conn.rollback()  # Rollback in case of error
    finally:
        cur.close()
        conn.close()  # Close the connection to the friend requests DB



createFriendRequestsTable() 


def modify_userProfile_table():
    conn = psycopg2.connect(database='userProfileDb', user='postgres', password='', host='35.184.188.68', port='5432')
    cur = conn.cursor()
    
    # Add the 'profile_setup' column if it does not already exist
    try:
        cur.execute('''
            ALTER TABLE userProfile
            ADD COLUMN IF NOT EXISTS profile_setup BOOLEAN DEFAULT FALSE;
        ''')
    except Exception as e:
        print(f"Error modifying table: {e}")
    finally:
        conn.commit()
        cur.close()
        conn.close()

# Call this function to modify the table
modify_userProfile_table()

from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField




# Initialize user profile
def initialize_user_profile(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    username = session.get('username')
    # Insert default user profile data if not already present
    cur.execute("SELECT * FROM userProfile WHERE user_id = %s", (user_id,))
    if not cur.fetchone():
        cur.execute("INSERT INTO userProfile (user_id, allergies, smoker, chore_preferences, cooking, owned_pets, username) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (user_id, 'None', 'no', 'None', 'never', 'None', 'None'))

    conn.commit()
    conn.close()



# Defines if a user exists
# Fetch or Initialize User Profile
def get_user_profile(user_id, fields=None):
    """
    Fetch specific fields of a user's profile based on the user_id.

    Args:
        user_id (int): The ID of the user whose profile is being fetched.
        fields (list, optional): A list of column names to fetch. Fetches all columns if None.

    Returns:
        dict or None: A dictionary with the requested fields, or None if an error occurs.
    """
    try:
        # Default to fetching all fields if none are specified
        if not fields:
            fields = ['user_id', 'allergies', 'smoker', 'chore_preferences', 'cooking', 'owned_pets', 'profile_picture']

        # Convert fields to a comma-separated string for SQL query
        fields_str = ", ".join(fields)

        conn = get_db_connection()
        cur = conn.cursor()
        query = f"SELECT {fields_str} FROM userProfile WHERE user_id = %s"
        cur.execute(query, (user_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row:
            # Map fields to the corresponding values
            return dict(zip(fields, row))
        return None

    except Exception as e:
        print(f"Error fetching user profile: {e}")
        return None




# In the userProfile route
@userProfile_bp.route('/userProfile', methods=['GET'])
def userProfile():
    user_id = session.get('user_id')
    unique_url = str(uuid.uuid4())  # Generate the unique URL

    if not user_id:
        return redirect(url_for('auth.loginUser'))
    
    # Check if user profile is initialized
    profile = get_user_profile(user_id)
    if not profile:
        # Initialize profile if none exists
        initialize_user_profile(user_id)
        profile = get_user_profile(user_id)  # Re-fetch after initialization
    
    # Redirect to the generated URL route with unique URL
    return redirect(url_for('userProfile.generated_userProfile', unique_url=unique_url))  # <-- Correct this line



@userProfile_bp.route('/userProfile/<unique_url>')
def generated_userProfile(unique_url):
    """
    Display the generated user profile page based on a unique URL.
    """

    # Assuming user_id is stored in the session
    user_id = session.get('user_id')

    if not user_id:
        flash("You need to log in to view your profile.", "error")
        return redirect(url_for('auth.loginUser'))

    # Fetch the user profile from the database
    user_profile = get_user_profile(user_id)

    if not user_profile:
        flash("Profile not found. Please set up your profile.", "info")
        return redirect(url_for('userProfile.setUpUserProfile'))

    # Check if the user_profile is a tuple or a dictionary
    if isinstance(user_profile, tuple):
        profile = {
            "id": user_profile[0],
            "user_id": user_profile[1],
            "allergies": user_profile[2],
            "smoker": user_profile[3],
            "chore_preferences": user_profile[4],
            "cooking": user_profile[5],
            "owned_pets": user_profile[6],
            "profile_picture": user_profile[7],
        }
    elif isinstance(user_profile, dict):
        profile = {
            "id": user_profile.get('id'),
            "user_id": user_profile.get('user_id'),
            "allergies": user_profile.get('allergies'),
            "smoker": user_profile.get('smoker'),
            "chore_preferences": user_profile.get('chore_preferences'),
            "cooking": user_profile.get('cooking'),
            "owned_pets": user_profile.get('owned_pets'),
            "profile_picture": user_profile.get('profile_picture'),
        }
    else:
        # Handle other cases if necessary
        flash("Unexpected profile data structure.", "error")
        return redirect(url_for('auth.loginUser'))

    # Render the profile template
    return render_template('userProfile.html', profile=profile, unique_url=unique_url)





@userProfile_bp.route('/showUserProfile', methods=['GET'])
def show_user_profile():
    user_id = session.get('user_id')  # Retrieve user_id from session
    unique_url = str(uuid.uuid4())
    if not user_id:
        flash("You must be logged in to view your profile.", "error")
        return redirect(url_for('auth.loginUser'))

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Query the userProfile table for the given user_id
        cur.execute('''
            SELECT id, user_id, allergies, smoker, chore_preferences, cooking, owned_pets, profile_picture
            FROM userProfile
            WHERE user_id = %s
        ''', (user_id,))

        user_profile = cur.fetchone()
        #ERROR
        if not user_profile:
            flash(f"No profile found for user ID {user_id}", "error")
            return redirect(url_for('home'))

        # Transform tuple to dictionary for template rendering
        profile = {
            "id": user_profile[0],
            "user_id": user_profile[1],
            "allergies": user_profile[2],
            "smoker": user_profile[3],
            "chore_preferences": user_profile[4],
            "cooking": user_profile[5],
            "owned_pets": user_profile[6],
            "profile_picture": user_profile[7],
        }

        return render_template('userProfile.html', profile=profile)

    except Exception as e:
        print(f"Error fetching user profile: {e}")
        flash("An error occurred while fetching the user profile.", "error")
        return redirect(url_for('home'))

    finally:
        cur.close()
        conn.close()



# DEBUG
@userProfile_bp.route('/showOtherProfile/<username>', methods=['GET'])
def show_other_profile(username):
    """
    Display another user's profile based on their username.
    """
    print(username)
    logged_in_user = session.get('username')
    if not logged_in_user:
        flash("You must be logged in to view profiles.", "error")
        return redirect(url_for('auth.loginUser'))

    #if logged_in_user == username:
        #flash("You cannot view your own profile through this page.", "info")
        #return redirect(url_for('userProfile.userProfile'))  # Redirect to personal profile page

    conn = get_db_connection()
    cur = conn.cursor()
    print(username)
    try:
        # Fetch the profile for the given username, ensuring it is not the logged-in user's profile
        cur.execute('''
            SELECT id, allergies, smoker, chore_preferences, cooking, owned_pets, profile_picture, username
            FROM userProfile
            WHERE username = %s
        ''', (username,))
        profile = cur.fetchone()

        if not profile:
            flash(f"No profile found for user '{username}'", "error")
            return redirect(url_for('home'))


        return render_template('displayOtherUserProfile.html', profile=profile)


    except Exception as e:
        print(f"Error fetching user profile: {e}")
        flash("An error occurred while fetching the profile.", "error")
        return redirect(url_for('home'))
    finally:
        cur.close()
        conn.close()



@userProfile_bp.route('/editUserProfile/', methods=['GET', 'POST'])
def editUserProfile():
    unique_url = str(uuid.uuid4())
    user_id = session.get('user_id')


    if not user_id:
        return redirect(url_for('auth.loginUser'))

    # Check if the profile has been set up
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT profile_setup FROM userProfile WHERE user_id = %s', (user_id,))
            result = cur.fetchone()

           # if not result or not result[0]:  # If profile_setup is False or doesn't exist
                # return redirect(url_for('userProfile.setUpUserProfile'))

    if request.method == 'POST':
        # Get data from the form
        allergies = request.form.get('allergies')
        smoker = request.form.get('smoker') 
        chore_preferences = request.form.get('chore_preferences')
        cooking = request.form.get('cooking')
        owned_pets = request.form.get('owned_pets')

        # Update profile in database
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE userProfile
                    SET allergies = %s, smoker = %s, chore_preferences = %s, cooking = %s, owned_pets = %s, profile_setup = TRUE
                    WHERE user_id = %s
                ''', (allergies, smoker, chore_preferences, cooking, owned_pets, user_id))

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('userProfile.show_user_profile'))

    return render_template('userProfile.html')




@userProfile_bp.route('/setUpUserProfile', methods=['GET', 'POST'])
def setUpUserProfile():
    user_id = session.get('user_id')
    username = session.get('username')

    if not user_id:
        return redirect(url_for('auth.loginUser'))

    if request.method == 'POST':
        # Get data from the form
        allergies = request.form.get('allergies')
        smoker = request.form.get('smoker') == 'on'
        chore_preferences = request.form.get('chore_preferences')
        cooking = request.form.get('cooking')
        owned_pets = request.form.get('owned_pets')

        # Insert or update the profile and mark as setup
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE userProfile
                    SET allergies = %s, smoker = %s, chore_preferences = %s, cooking = %s, owned_pets = %s, profile_setup = TRUE
                    WHERE user_id = %s
                ''', (allergies, smoker, chore_preferences, cooking, owned_pets, user_id))

        flash('Profile setup completed successfully!', 'success')
        return render_template('home.html')

    return render_template('setUpUserProfile.html')



@userProfile_bp.route('/userProfile/filterPage', methods=['GET', 'POST'])
def filter_page():
    """
    Render the filter input page where users can specify criteria.
    """
    # Create an instance of the form
    form = UserFilterForm()  # Ensure UserFilterForm is imported

    return render_template('filterUsers.html', form=form)


def get_filtered_user_ids(filters, exclusion=False):
    """
    Fetch user ids based on filter criteria from the database.
    
    :param filters: Dictionary containing filter criteria.
    :param exclusion: Boolean indicating if exclusion logic should be applied.
    :return: List of user IDs matching the filters (or excluding them).
    """
    query = '''
        SELECT id
        FROM userProfile
        WHERE profile_setup = true
    '''
    params = []

    # Dynamically add filters to the query
    if filters.get("allergies"):
        query += " AND allergies = %s"
        params.append(filters["allergies"])

    if filters.get("smoker"):
        smoker_value = filters["smoker"]
        query += f" AND smoker = %s"
        params.append(smoker_value)

    if filters.get("chore_preferences"):
        query += " AND chore_preferences = %s"
        params.append(filters["chore_preferences"])

    if filters.get("cooking"):
        query += " AND cooking = %s"
        params.append(filters["cooking"])

    if filters.get("owned_pets"):
        query += " AND owned_pets = %s"
        params.append(filters["owned_pets"])

    # Apply exclusion logic if specified
    if exclusion:
        query = query.replace("AND", "AND NOT", 1)  # Change the first "AND" to "AND NOT"
    
    # Execute the query to get the list of ids
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(query, tuple(params))
        return [row[0] for row in cur.fetchall()]  # Return the ids as a list
    except Exception as e:
        print(f"Error fetching user ids: {e}")
        return []  # Return an empty list in case of error
    finally:
        cur.close()
        conn.close()


@userProfile_bp.route('/userProfile/filtersUsers', methods=['GET', 'POST'])
def filters_users():
    form = UserFilterForm()
    filtered_users = []  # Initialize empty list for filtered users

    # Check if the form was submitted
    if form.validate_on_submit():
        # Collect filter criteria from the form
        filters = {
            "allergies": form.allergies.data,
            "smoker": form.smoker.data,
            "chore_preferences": form.chore_preferences.data,
            "cooking": form.cooking.data,
            "owned_pets": form.owned_pets.data,
        }

        # Determine if the form is for exclusion filters or inclusion filters
        exclusion = False  # Default to False (inclusion filters)

        # You can add additional logic here to check if this is an exclusion filter form
        # For example, you might check for an exclusion-specific field or button state
        if 'exclude' in request.form:  # Check if an exclusion filter is triggered
            exclusion = True

        # Fetch filtered user IDs based on the criteria and exclusion flag
        filtered_user_ids = get_filtered_user_ids(filters, exclusion=exclusion)

        if filtered_user_ids:
            user_profiles = []  # Initialize the list to hold user profiles
            for user_id in filtered_user_ids:
                # Fetch detailed profile information for each user ID
                user_profile = get_user_profile_by_id(user_id)  # Assuming this function is correctly implemented
                if user_profile:
                    print(user_profile)  # Debugging: Check the structure of user_profile
                    user_profiles.append(user_profile)

            # Assign the collected profiles to `filtered_users`
            filtered_users = user_profiles

        # If no users match the filters, flash an informational message
        if not filtered_users:
            flash("No users found matching your filters.", "info")

    return render_template('filterUsers.html', form=form, filtered_users=filtered_users)



def get_user_profile_by_id(user_id):
    """
    Fetch detailed user profile information from the database by user ID.
    """
    query = '''
        SELECT id, user_id, allergies, smoker, chore_preferences, cooking, owned_pets, profile_picture, username
        FROM userProfile
        WHERE id = %s
    '''

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(query, (user_id,))
        row = cur.fetchone()
        if row:
            # Convert the row into a dictionary
            return {
                "id": row[0],
                "user_id": row[1],
                "allergies": row[2],
                "smoker": row[3],
                "chore_preferences": row[4],
                "cooking": row[5],
                "owned_pets": row[6],
                "profile_picture": row[7],
                "username": row[8],  # Ensure this key matches what the template expects
            }

         

        return None
    except Exception as e:
        print(f"Error fetching user profile: {e}")
        return None
    finally:
        cur.close()
        conn.close()



@userProfile_bp.route('/filter_users/<unique_url>')
def generated_filter_users(unique_url):
    """
    Display filtered users based on the unique URL.
    """
    # Fetch the filtered users using the unique URL from session or database if needed
    # Since the filtered users were passed via the redirect, you might want to fetch them from a session or store
    #filtered_users = request.args.get('filtered_users')
    filtered_users = 'Jack'
    # If no users are available, redirect to home or show a message
    if not filtered_users:
        flash("No users found matching the filters 55", "error")
        return redirect(url_for('home'))

    # Render the filtered users template
    return render_template('filterUsers.html', filtered_users=filtered_users, unique_url=unique_url)

    

@userProfile_bp.route('/userProfile/updatePicture/<username>', methods=['POST'])
def update_profile_picture(username):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    # Handle profile picture upload
    if 'profile_picture' not in request.files:
        flash('No file part')
        return redirect(request.url)
    
    file = request.files['profile_picture']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file:
        # Save file and update user profile picture in the database
        filename = file.filename
        file.save(f'./static/profile_pictures/{filename}')
        
        conn = get_db_connection()
        cur = conn.cursor()

        # Update profile picture path in the userProfile table
        cur.execute('''
            UPDATE userProfile
            SET profile_picture = %s
            WHERE user_id = %s
        ''', (filename, user_id))

        conn.commit()
        conn.close()

        flash('Profile picture updated successfully!')
        return redirect(url_for('userProfile.render_user_profile'))




#TODO: Implement a way to link users to posted properties (to be determined how)



#TODO: Implement a way for users to save properties to their userProfiles 
@userProfile_bp.route('/saveProperty/<int:property_id>', methods=['POST'])
def save_property(property_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to save properties.", "error")
        return redirect(url_for('auth.loginUser'))

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # Insert the saved property
        cur.execute('''
            INSERT INTO saved_properties (user_id, property_id)
            VALUES (%s, %s)
            ON CONFLICT (user_id, property_id) DO NOTHING
        ''', (user_id, property_id))

        conn.commit()
        flash("Property saved successfully!", "success")
    except Exception as e:
        conn.rollback()
        print(f"Error saving property: {e}")
        flash("An error occurred while saving the property.", "error")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('home'))  # Redirect to a relevant page


#TODO: Implement a way to show these properties on a unique user using userProfiles - Giancarlo


#TODO: Implement and test friend feature 

# Implement boolean checking for if two users are friends
def are_friends(user_id_1, user_id_2):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT status
        FROM friendships
        WHERE (user_id_1 = %s AND user_id_2 = %s) OR (user_id_1 = %s AND user_id_2 = %s)
        """, (user_id_1, user_id_2, user_id_2, user_id_1))
    friendship = cur.fetchone()
    cur.close()
    conn.close()
    return friendship is not None and friendship[0] == 'accepted'


# Implement getting list of friends to implement in other calls
def get_friends(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.username
        FROM users u
        JOIN friendships f ON (u.id = f.user_id_1 OR u.id = f.user_id_2)
        WHERE (f.user_id_1 = %s OR f.user_id_2 = %s) AND f.status = 'accepted'
        AND u.id != %s
        """, (user_id, user_id, user_id))
    friends = cur.fetchall()
    cur.close()
    conn.close()
    return friends



# Implement user inbox
@userProfile_bp.route('/api/friendRequestInbox', methods=['GET'])
def friendRequestInbox():
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to view your inbox.", "error")
        return redirect(url_for('auth.loginUser'))

    # Initialize the request_list
    request_list = []

    try:
        # Connect to the database
        conn = get_userFriends_db_connection()
        cur = conn.cursor()

        # Fetch pending friend requests for the logged-in user
        cur.execute('''
            SELECT id, sender_id, message, status, created_at
            FROM friend_requests
            WHERE receiver_id = %s AND status = 'pending'
            ORDER BY created_at DESC
        ''', (user_id,))
        requests = cur.fetchall()

        # Process the fetched data
        if requests:
            request_list = [{
                "id": req[0],
                "sender_id": req[1],
                "message": req[2],
                "status": req[3],
                "created_at": req[4].strftime("%Y-%m-%d %H:%M:%S")
            } for req in requests]
            
   

    except Exception as e:
        # Flash the error to the user
        flash(f"An error occurred while retrieving your inbox: {e}", "error")
    finally:
        for req in request_list:
            print(req)
        # Safely close the cursor and connection
        if 'cur' in locals() and cur is not None:
            cur.close()
        if 'conn' in locals() and conn is not None:
            conn.close()

    # Render the template and pass the request list
  

    return render_template('friendRequestInbox.html', requests=request_list)



# Implement friend request sending
@userProfile_bp.route('/sendFriendRequest', methods=['POST'])
def send_friend_request():
    current_user_id = session.get('user_id')
    if not current_user_id:
        flash("You must be logged in to send friend requests.", "error")
        return redirect(url_for('auth.loginUser'))

    receiver_username = request.form.get('receiver_username')  # The person to whom you're sending the request
    message = request.form.get('message')  # Custom message
    if not receiver_username:
        print("No username provided.", "error")
        return render_template('userProfile.html', profile=get_user_profile(current_user_id))

    try:
        conn = get_user_db()
        cur = conn.cursor()

        # Get the receiver's ID
        cur.execute("SELECT id FROM users WHERE username = %s", (receiver_username,))
        receiver = cur.fetchone()
        if not receiver:
            flash(f"User '{receiver_username}' not found.", "error")
            return render_template('userProfile.html', profile=get_user_profile(current_user_id))

        receiver_id = receiver[0]

        conn = get_userFriends_db_connection()
        cur = conn.cursor()
        # Insert a pending friend request with the message
        cur.execute('''
            INSERT INTO friend_requests (sender_id, receiver_id, message, status)
            VALUES (%s, %s, %s, 'pending');
        ''', (current_user_id, receiver_id, message))
        conn.commit()
        flash(f"Friend request sent to {receiver_username}.", "success")

        # Redirect to the sender's profile or home page after sending the request
        return redirect(url_for('home', user_id=current_user_id))  # Redirect to the sender's profile

    except Exception as e:
        conn.rollback()
        flash(f"An error occurred while sending the request: {e}", "error")
    finally:
        cur.close()
        conn.close()

    # If an error occurs, render the profile again
    return render_template('userProfile.html')


#Accept or Reject Friend Requests
@userProfile_bp.route('/friendRequests/acceptFriendRequest/<int:request_id>', methods=['POST'])
def accept_friend_request(request_id):
    print(request_id)
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to accept friend requests.", "error")
        return redirect(url_for('auth.loginUser'))

    try:
        conn = get_userFriends_db_connection()
        cur = conn.cursor()

        # Check if the friend request exists and is pending
        cur.execute("SELECT sender_id, receiver_id, message FROM friend_requests WHERE id = %s AND status = 'pending'", (request_id,))
        request = cur.fetchone()
        if not request:
            #flash("Friend request not found or already processed.", "error")
            return redirect(url_for('userProfile.inbox'))

        sender_id, receiver_id, message = request
        if sender_id == user_id:
           
            return redirect(url_for('userProfile.inbox'))

        # Update the request status to 'accepted'
        cur.execute("UPDATE friend_requests SET status = 'accepted' WHERE id = %s", (request_id,))
        
     
        conn.commit()
       # flash("Friend request accepted. You are now friends!", "success")

    except Exception as e:
        conn.rollback()
        #flash(f"An error occurred while accepting the request: {e}", "error")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('userProfile.friendRequestInbox'))


# queried by user inbox user inbox
@userProfile_bp.route('/friendRequests/rejectFriendRequest/<int:request_id>', methods=['POST'])
def reject_friend_request(request_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("You must be logged in to reject friend requests.", "error")
        return redirect(url_for('auth.loginUser'))

    try:
        conn = get_userFriends_db_connection()
        cur = conn.cursor()

        # Check if the friend request exists and is pending
        cur.execute("SELECT sender_id, receiver_id, message FROM friend_requests WHERE id = %s AND status = 'pending'", (request_id,))
        request = cur.fetchone()
        if not request:
            #flash("Friend request not found or already processed.", "error")
            return redirect(url_for('userProfile.inbox'))

        sender_id, receiver_id, message = request
        if receiver_id != user_id:
            #flash("This is not your friend request to reject.", "error")
            return redirect(url_for('userProfile.inbox'))

        # Update the request status to 'rejected'
        cur.execute("UPDATE friend_requests SET status = 'rejected' WHERE id = %s", (request_id,))
        conn.commit()
        #flash("Friend request rejected.", "info")

    except Exception as e:
        conn.rollback()
        #flash(f"An error occurred while rejecting the request: {e}", "error")
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('userProfile.friendRequestInbox'))


messages = {}


@userProfile_bp.route('/messageInbox', methods=['GET'])
def message_inbox():
    user_id = current_user.id
    
    # Fetch all friends with whom the user has chats
    user_chats = messages.get(user_id, {})
    friends_with_chats = [
        {'id': friend_id, 'username': User.query.get(friend_id).username}
        for friend_id in user_chats.keys()
    ]
    
    return render_template('messageInbox.html', friends=friends_with_chats)


@userProfile_bp.route('/messageInbox/<int:friend_id>', methods=['GET', 'POST'])
def messages_page(friend_id):
    user_id = current_user.id
    friend = User.query.get(friend_id)
    
    # Ensure the users are friends
    if not friend or friend_id not in [friend.id for friend in current_user.friends]:
        return redirect(url_for('message_inbox'))
    
    # Fetch the chat history
    if user_id not in messages:
        messages[user_id] = {}
    if friend_id not in messages[user_id]:
        messages[user_id][friend_id] = []
    
    chat_history = messages[user_id][friend_id]

    if request.method == 'POST':
        content = request.form['message']
        if content:
            # Save the message in both user's chats
            new_message = {
                'sender': current_user.username,
                'content': content,
                'timestamp': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            }
            messages[user_id][friend_id].append(new_message)
            if friend_id not in messages:
                messages[friend_id] = {}
            if user_id not in messages[friend_id]:
                messages[friend_id][user_id] = []
            messages[friend_id][user_id].append(new_message)

            # Emit the message to the friend
            socketio.emit('new_message', new_message, room=friend_id)
            return redirect(url_for('messages_page', friend_id=friend_id))

    return render_template('chat.html', messages=chat_history, friend=friend)





# Register the Blueprint with the app
#app.register_blueprint(userProfile_bp)

# Run the application
#if __name__ == '__main__':
    #socketio.run(debug=True)