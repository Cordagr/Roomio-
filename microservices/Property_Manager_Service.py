from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask import Blueprint
import psycopg2
from werkzeug.security import generate_password_hash
import tkinter as tk
from tkinter import messagebox
from flask_jwt_extended import decode_token


# Blueprint for property-related routes
property_bp = Blueprint('property', __name__)

# Database connection utility
def get_db_connection():
    conn = psycopg2.connect(
        database="propertyDb",  # Your database name
        user="postgres",         # Your database username
        password="",  # Your database password
        host="35.184.188.68",
        port="5432"
    )
    return conn

# Ensure 'properties' table has all necessary fields
def update_properties_table():
    conn = get_db_connection()  # Ensure this function works and connects to your database
    cur = conn.cursor()
    
    try:
        # Check if the 'properties' table exists
        cur.execute("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='properties')")
        table_exists = cur.fetchone()[0]
        
        if table_exists:
            print("Properties table exists; modifying as needed.")
            
            # Add 'price' column if it doesn't exist
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='properties' AND column_name='price'")
            if not cur.fetchone():
                print("Adding 'price' column to 'properties' table.")
                cur.execute("ALTER TABLE properties ADD COLUMN price DECIMAL(10, 2) DEFAULT 0.0")
            
            # Add 'utilities' column if it doesn't exist
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='properties' AND column_name='utilities'")
            if not cur.fetchone():
                print("Adding 'utilities' column to 'properties' table.")
                cur.execute("ALTER TABLE properties ADD COLUMN utilities VARCHAR(255)")
        else:
            print("Creating 'properties' table.")
            cur.execute('''
                CREATE TABLE properties (
                    id SERIAL PRIMARY KEY,
                    address VARCHAR(255) NOT NULL,
                    owner_name VARCHAR(255) NOT NULL,
                    description TEXT,
                    price DECIMAL(10, 2) DEFAULT 0.0,
                    utilities VARCHAR(255),
                    size INTEGER,
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id INTEGER
                );
            ''')
        
        # Commit changes
        conn.commit()
        print("Database update completed.")
        
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    
    finally:
        # Always close the cursor and connection
        cur.close()
        conn.close()

# Call the function
update_properties_table()

def validateHashedUserId():
    print("")
# Check hashed session user_id and validate for any pages which require showing information



def userHasProperties():
    # check database within properties db, and return if true
    # both check user id and current token
    # do not directly stor user ids but instead hash it can check
    user_id 
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM properties WHERE user_id = %s', (user_id,))
    properties = cursor.fetchall()
    if properties is None:
        print("")

    

@property_bp.route('/insertProperty', methods=['GET', 'POST'])
def insertProperty():
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = session.get('user_id')
    username = session.get('username')

    # Extract the token from the session
    access_token = session.get('access_token')
    if not access_token:
        flash("You need to log in to perform this action.", "danger")
        return redirect(url_for('auth.loginUser'))

    try:
        # Decode the token to retrieve the user identity (e.g., user_id)
        decoded_token = decode_token(access_token)
        user_id = decoded_token['sub']  # 'sub' typically holds the identity
    except Exception as e:
        flash("Invalid or expired token. Please log in again.", "danger")
        return redirect(url_for('auth.loginUser'))

    if request.method == 'POST':
        address = request.form['address']
        owner_name = username
        description = request.form.get('description', '')
        utilities = request.form['utilities']

        # Insert the property into the database
        cursor.execute('''
            INSERT INTO properties (address, owner_name, description, user_id)
            VALUES (%s, %s, %s, %s)
        ''', (address, owner_name, description, user_id))

        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('property.display_all_properties'))

    cursor.close()
    conn.close()
    return render_template('insertProperty.html')




#Route to display all properties
@property_bp.route('/displayAllProperties', methods=['GET'])
def display_all_properties():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM properties')
    properties = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('displayAllProperties.html', properties=properties)


@property_bp.route('/viewMyProperties', methods=['GET', 'POST'])
def viewMyProperties():
    # Retrieve the logged-in username from the session
    username = session.get('username')
    
    if not username:
        flash("You need to be logged in to view your properties.", "error")
        return redirect(url_for('auth.login'))

    try:
        # Establish a database connection
        conn = get_db_connection()
        cur = conn.cursor()

        # Fetch the user_id corresponding to the username
        cur.execute("SELECT user_id FROM properties WHERE owner_name = %s", (username,))
        user_id = cur.fetchone()

        if not user_id:
            flash("User not found.", "error")
            return redirect(url_for('auth.login'))


        # Retrieve all properties owned by this user
        cur.execute("SELECT * FROM properties WHERE user_id = %s", (user_id,))
        properties = cur.fetchall()

        conn.close()

        return render_template('viewMyProperties.html', username=username, properties=properties)

    except Exception as e:
        print(f"An error occurred: {e}")
        flash("An error occurred while retrieving your properties.", "error")
        return redirect(url_for('home'))



# Route for viewing property details and interested users
@property_bp.route('/property/<int:id>', methods=['GET', 'POST'])
def property_details(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM properties WHERE id = %s', (id,))
    property_data = cursor.fetchone()

    cursor.execute('SELECT * FROM interested_users WHERE property_id = %s', (id,))
    interested_users = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('property_details.html', property=property_data, interested_users=interested_users)



## Route for editing an existing property
@property_bp.route('/property/<int:id>/edit', methods=['GET', 'POST'])
def edit_property(id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        address = request.form['address']
        owner_name = request.form['owner_name']
        description = request.form['description']
        price = request.form['price']  # New field
        utilities = request.form['utilities']  # New field

        cursor.execute('''UPDATE properties
                          SET address = %s, owner_name = %s, description = %s, price = %s, utilities = %s
                          WHERE id = %s''', (address, owner_name, description, price, utilities, id))
        conn.commit()
        cursor.close()
        conn.close()
    
    return redirect(url_for('editProperties', id=id))

    cursor.execute('SELECT * FROM properties WHERE id = %s', (id,))
    property_data = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('editProperties.html', property=property_data)


# Route for deleting a property
@property_bp.route('/property/<int:id>/delete', methods=['POST','GET'])
def delete_property(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = session.get('user_id')  # Get the logged-in user's ID from the session

    # Check if the current user owns the property
    cursor.execute('SELECT user_id FROM properties WHERE id = %s', (id,))
    result = cursor.fetchone()

    if result and result[0] == user_id:
        # Proceed with deletion if the user owns the property
        cursor.execute('DELETE FROM properties WHERE id = %s', (id,))
        conn.commit()
    else:
        flash("You do not have permission to delete this property.", "error")

    cursor.close()
    conn.close()
    return redirect(url_for('property.viewMyProperties'))


# Route for applying to a property
@property_bp.route('/property/<int:property_id>/apply/<int:user_id>', methods=['GET', 'POST'])
def apply_for_property(property_id, user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
    user = cursor.fetchone()

    if request.method == 'POST':
        name = user[1]
        email = user[2]
        phone = user[3]

        cursor.execute('''INSERT INTO tenant_applications (name, email, phone, preferred_property_id)
                          VALUES (%s, %s, %s, %s) RETURNING id''', (name, email, phone, property_id))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect(url_for('property.property_details', id=property_id))

    cursor.execute('SELECT * FROM properties WHERE id = %s', (property_id,))
    property_data = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('apply.html', property=property_data, user=user)




# defines all building types that will be used
class ApartmentDesigner:
    def __init__(self,root):
        self.root = root
        self.root.title()
        self.root.title("Apartment Layout Simulator")
        self.canvas.pack()

        self.create_widgets() 



def createWidgets(self):
    self.add_room_button = tk.Canvas(root, width=800, height=600, bg="white")
    self.canvas.pack()

    self.create_widgets() 

    
def add_room(self):
    self.canvas.create_rectangle(50,50,200,200,fill="lightblue")

def make_draggable(widget):
    widget.bind("<Room>", on_drag_start)
    widget.bind("<Room-Motion>", on_drag_motion)

def on_drag_start(event):
    widget = event.widget
    widget._drag_start_x = event.x 
    widget._drag_start_y = event.y 

def on_drag_motion(event):
    widget = event.widget
    x = widget.winfo_x() - widget._drag_start_x + event.x
    y = widget.winfo_y() - wodget._drag_start_y + event.y
    widget.place(x=x,y=y)

def clear_canvas(self):
    self.canvas.delete("all")

if __name__ == '__main__':
    root = tk.Tk()
    app.run(debug=True)
    root.mainloop()

