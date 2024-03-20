from flask import Flask, render_template, redirect, url_for, request, jsonify, session
from datetime import datetime
import mysql.connector
import uuid
from functools import wraps
from flask import request


app = Flask(__name__)

app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
active_sessions = {}

# Connect to MySQL database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  
    database="registration_test"
)

# Custom middleware decorator to check for an active session
def require_session(session_keys):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            for key in session_keys:
                if key not in session:
                    # Redirect to the login page if any of the keys is not in the session
                    return redirect(url_for('proctor_login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_admin_session(route_names):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'admin_access' not in session:
                # Redirect to admin login if admin session not found
                return redirect(url_for('admin_login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Route for lobby page
@app.route('/')
def lobby():
    return render_template('lobby.html')

# Route for registration page
@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        rank = request.form['rank']
        first_name = request.form['first_name']
        middle_name = request.form['middle_name']
        surname = request.form['surname']
        afpsn = request.form['afpsn']
        afp_mos = request.form['afp_mos']
        gender = request.form['gender']
        birth_date = request.form['birth_date']
        unit = request.form['unit']
        company = request.form['company']
        cursor = db.cursor()
        cursor.execute("INSERT INTO users_account (rank, first_name, middle_name, surname, afpsn, afp_mos, gender, birth_date, unit, company) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (rank, first_name, middle_name, surname, afpsn, afp_mos, gender, birth_date, unit, company))
        db.commit()
        cursor.close()
        return redirect(url_for('lobby'))
    return render_template('register.html')

# Route for Proctor Login Page
@app.route('/proctor_login', methods=['GET', 'POST'])
def proctor_login():
    if request.method == 'POST':
        afpsn = request.form['afpsn']
        password = request.form['password']
        
        cursor = db.cursor()
        cursor.execute("SELECT * FROM proctor_account WHERE afpsn = %s AND password = %s", (afpsn, password))
        proctor_account = cursor.fetchone()
        cursor.close()

        if proctor_account:
            proctor_id = proctor_account[0]  # Assuming the first element is the ID
            proctor_name = proctor_account[1]  # Assuming the second element is the name
            # Check if the user has an active session
            if proctor_id in active_sessions.values():
                return render_template('proctor_login.html', error="Another session is already active for this account.")
            
            # Clear existing sessions for this user (in case of multiple logins)
            clear_sessions_for_user(proctor_id)
            
            # Store proctor information in session
            session['proctor_access'] = {'id': proctor_id, 'name': proctor_name}
            # Generate a unique session identifier using UUID
            session_id = str(uuid.uuid4())
            # Add session ID to active sessions
            active_sessions[session_id] = proctor_id
            # Store session ID in session cookie
            session['session_id'] = session_id
            # Redirect to proctor_welcome.html
            return redirect(url_for('proctor_welcome'))
        else:
            # Redirect to proctor_login.html with error message
            return render_template('proctor_login.html', error="Invalid AFPSN or password. Please try again.")
    return render_template('proctor_login.html')

@app.route('/proctor_logout', methods=['POST'])
def proctor_logout():
    # Remove session ID from active sessions
    if 'session_id' in session:
        active_sessions.pop(session['session_id'], None)     
    # Clear the entire session
    session.clear()
    return redirect(url_for('proctor_login'))


def clear_sessions_for_user(user_id):
    global active_sessions
    active_sessions = {sid: uid for sid, uid in active_sessions.items() if uid != user_id}

# New route to handle logout request from client-side JavaScript
@app.route('/logout', methods=['POST'])
def logout():
    # Remove session ID from active sessions
    if 'session_id' in session:
        active_sessions.pop(session['session_id'], None)
        # Clear session data
        session.clear()
    return 'Logged out successfully', 200

# Route for Proctor Registration Page
@app.route('/proctor_registration', methods=['GET', 'POST'])
def proctor_registration():
    if request.method == 'POST':
        name = request.form['name']
        afpsn = request.form['afpsn']
        password = request.form['password']
        rank = request.form['rank']
        afp_mos = request.form['afp_mos']

        cursor = db.cursor()
        cursor.execute("INSERT INTO proctor_registration (name, afpsn, password, rank, afp_mos) VALUES (%s, %s, %s, %s, %s)", (name, afpsn, password, rank, afp_mos))
        db.commit()
        cursor.close()
        
        return redirect(url_for('proctor_login'))
    return render_template('proctor_registration.html')

@app.route('/suggest_usernames')
def suggest_usernames():
    afpsn = request.args.get('afpsn')

    cursor = db.cursor()
    cursor.execute("SELECT first_name FROM users_account WHERE afpsn LIKE %s", (afpsn + '%',))
    first_names = cursor.fetchall()

    suggestions = ''.join(f"<div onclick='fillSerialNumber(\"{first_name[0]}\")'>{first_name[0]}</div>" for first_name in first_names)
    return suggestions

@app.route('/get_serial_number')
def get_serial_number():
    first_name = request.args.get('username')

    cursor = db.cursor()
    cursor.execute("SELECT afpsn FROM users_account WHERE first_name = %s", (first_name,))
    afpsn = cursor.fetchone()

    if afpsn:
        return jsonify(int(afpsn[0]))
    else:
        return jsonify(None)

@app.route('/search_serial', methods=['GET'])
def search_serial():
    afpsn = request.args.get('afpsn')

    # Check if serial number exists
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users_account WHERE afpsn = %s", (afpsn,))
    user_info = cursor.fetchone()

    if user_info:
        print(f"Serial number {afpsn} found. User info: {user_info}")
        # Combine first name, middle name, and surname
        full_name = f"{user_info['first_name']} {user_info['middle_name']} {user_info['surname']}"
        user_info['full_name'] = full_name
        return jsonify(user_info)  # Return user information if found
    else:
        print(f"Serial number {afpsn} not found.")
        return jsonify(None)  # Return None if serial number not found

@app.route('/proctor_access', methods=['GET', 'POST'])
def proctor_access():
    if request.method == 'POST':
        afpsn = request.form.get('afpsn')

        # Check if serial number exists
        cursor = db.cursor()
        cursor.execute("SELECT first_name FROM users_account WHERE afpsn = %s", (afpsn,))
        first_name = cursor.fetchone()

        if not first_name:
            return "Serial number does not exist."

        # Serial number exists, process the rest of the form data
        raw_pushup = request.form.get('raw_pushup')
        raw_situp = request.form.get('raw_situp')
        act_date = request.form.get('act_date')
        #participant_number = request.form.get('participant_number')

        if not (raw_pushup and raw_situp and act_date ): #and participant_number
            return "Push-up count, sit-up count, date, or participant number is missing."

        try:
            act_date = datetime.strptime(act_date, '%Y-%m-%d').date()
        except ValueError:
            # Handle parsing error
            return "Error: Invalid date format"
        
        cursor.execute("SELECT * FROM pft_pushup WHERE afpsn = %s AND act_date = %s", (afpsn, act_date))
        existing_raw_pushup = cursor.fetchone()

        if existing_raw_pushup:
            print("Pushup data already submitted for this act_date.")
        else:
            # Define the switch dictionary for male participants
            switch_male = {
                (21, 21): "age21_male",
                (22, 26): "age22_26_male",
                (27, 31): "age27_31_male",
                (32, 36): "age32_36_male",
                (37, 41): "age37_41_male",
                (42, 46): "age42_46_male",
                (47, 51): "age47_51_male",
                (52, 56): "age52_56_male",
                (57, 61): "age57_61_male",
                (62, float('inf')): "age62_male"
            }

            # Define the switch dictionary for female participants
            switch_female = {
                (21, 21): "age21_female",
                (22, 26): "age22_26_female",
                (27, 31): "age27_31_female",
                (32, 36): "age32_36_female",
                (37, 41): "age37_41_female",
                (42, 46): "age42_46_female",
                (47, 51): "age47_51_female",
                (52, 56): "age52_56_female",
                (57, 61): "age57_61_female",
                (62, float('inf')): "age62_female"
            }

            def execute_query(cursor, table_name, raw_pushup, afpsn, act_date):
                query = f"SELECT {table_name} FROM `pushup_reference` WHERE repetitions = %s;"
                cursor.execute(query, (raw_pushup,))
                participant_score = cursor.fetchone()[0]
                insert_query = f"INSERT INTO pft_pushup (afpsn, act_date, raw_pushup, pushup) VALUES (%s, %s, %s, %s)"
                cursor.execute(insert_query, (afpsn, act_date, raw_pushup, participant_score))
                db.commit()  # Commit the changes to the database

            def process_participant(cursor, afpsn, act_date):
                # Get participant's age
                cursor.execute("SELECT DATEDIFF(CURDATE(), birth_date) DIV 365 FROM users_account WHERE afpsn = %s", (afpsn,))
                participant_age = cursor.fetchone()[0]

                # Get participant's gender
                cursor.execute("SELECT gender FROM `users_account` WHERE afpsn = %s;", (afpsn,))
                participant_gender = cursor.fetchone()[0]

                if participant_gender == "M":
                    switch = switch_male
                else:
                    switch = switch_female

                for age_range, table_name in switch.items():
                    if age_range[0] <= participant_age <= age_range[1]:
                        print(f"Participant is {age_range[0]} - {age_range[1]}")
                        execute_query(cursor, table_name, raw_pushup, afpsn, act_date)
                        break

            process_participant(cursor, afpsn, act_date)

        # Process sit-up data
        cursor.execute("SELECT * FROM pft_situp WHERE afpsn = %s AND act_date = %s", (afpsn, act_date))
        existing_raw_situp = cursor.fetchone()

        if existing_raw_situp:
            print("Situp data already submitted for this act_date.")
        else:
            # Define the switch dictionary for male participants
            switch_male = {
                (21, 21): "age21_male",
                (22, 26): "age22_26_male",
                (27, 31): "age27_31_male",
                (32, 36): "age32_36_male",
                (37, 41): "age37_41_male",
                (42, 46): "age42_46_male",
                (47, 51): "age47_51_male",
                (52, 56): "age52_56_male",
                (57, 61): "age57_61_male",
                (62, float('inf')): "age62_male"
            }

            # Define the switch dictionary for female participants
            switch_female = {
                (21, 21): "age21_female",
                (22, 26): "age22_26_female",
                (27, 31): "age27_31_female",
                (32, 36): "age32_36_female",
                (37, 41): "age37_41_female",
                (42, 46): "age42_46_female",
                (47, 51): "age47_51_female",
                (52, 56): "age52_56_female",
                (57, 61): "age57_61_female",
                (62, float('inf')): "age62_female"
            }

            def execute_query(cursor, table_name, raw_situp, afpsn, act_date):
                query = f"SELECT {table_name} FROM `situp_reference` WHERE repetitions = %s;"
                cursor.execute(query, (raw_situp,))
                participant_score = cursor.fetchone()[0]
                insert_query = f"INSERT INTO pft_situp (afpsn, act_date, raw_situp, situp) VALUES (%s, %s, %s, %s)"
                cursor.execute(insert_query, (afpsn, act_date, raw_pushup, participant_score))
                db.commit()  # Commit the changes to the database

            def process_participant(cursor, afpsn, act_date):
                # Get participant's age
                cursor.execute("SELECT DATEDIFF(CURDATE(), birth_date) DIV 365 FROM users_account WHERE afpsn = %s", (afpsn,))
                participant_age = cursor.fetchone()[0]

                # Get participant's gender
                cursor.execute("SELECT gender FROM `users_account` WHERE afpsn = %s;", (afpsn,))
                participant_gender = cursor.fetchone()[0]

                if participant_gender == "M":
                    switch = switch_male
                else:
                    switch = switch_female

                for age_range, table_name in switch.items():
                    if age_range[0] <= participant_age <= age_range[1]:
                        print(f"Participant is {age_range[0]} - {age_range[1]}")
                        execute_query(cursor, table_name, raw_pushup, afpsn, act_date)
                        break

            process_participant(cursor, afpsn, act_date)

        return "Data submitted successfully."

    return render_template('proctor_access.html')

# Route for Admin registration page
@app.route('/admin_registration', methods=['GET', 'POST'])
def admin_registration():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor = db.cursor()
        # Insert data into admin_credentials table
        cursor.execute("INSERT INTO admin_credentials (username, password) VALUES (%s, %s)", (username, password))
        db.commit()
        cursor.close()
        
        return redirect(url_for('admin_login'))  # Redirect to Admin login page after registration
    else:
        return render_template('admin_registration.html')

# # Route for Admin Login Page
# @app.route('/admin_login', methods=['GET', 'POST'])
# def admin_login():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
        
#         cursor = db.cursor()
#         cursor.execute("SELECT * FROM admin_credentials WHERE username = %s AND password = %s", (username, password))
#         admin = cursor.fetchone()
#         cursor.close()
        
#         if admin:
#             # Store admin information in session
#             session['admin'] = admin
#             # Redirect to admin_access.html
#             return redirect(url_for('admin_access'))
#         else:
#             # Redirect to admin_login.html with error message
#             return render_template('admin_login.html', error="Invalid username or password. Please try again.")
#     return render_template('admin_login.html')

# Route for Admin Login Page
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor = db.cursor()
        cursor.execute("SELECT * FROM admin_credentials WHERE username = %s AND password = %s", (username, password))
        admin_account = cursor.fetchone()
        cursor.close()

        if admin_account:
            admin_id = admin_account[0]  # Assuming the first element is the ID
            admin_name = admin_account[1]  # Assuming the second element is the name

            if admin_id in active_sessions.values():
                return render_template('admin_login.html', error="Another session is already active for this account.")
            
            # Clear existing sessions for this user (in case of multiple logins)
            clear_sessions_for_user(admin_id)

            # Store admin information in session
            session['admin_access'] = {'id': admin_id, 'name': admin_name}
            # Generate a unique session identifier using UUID
            session_id = str(uuid.uuid4())
            # Add session ID to active sessions
            active_sessions[session_id] = admin_id
            # Store session ID in session cookie
            session['session_id'] = session_id
            # Redirect to admin_access.html
            return redirect(url_for('admin_access'))
        else:
            # Redirect to admin_login.html with error message
            return render_template('admin_login.html', error="Invalid Username or password. Please try again.")
    return render_template('admin_login.html')

# Route for Admin Access Page
@app.route('/admin_access')
@require_admin_session(['admin_access'])
def admin_access():
    return render_template('admin_access.html')

# Routes for Admin-specific pages
@app.route('/admin_approval')
# @require_admin_session(['admin_access'])
def admin_approval():
    return render_template('admin_approval.html')

@app.route('/pft_results', methods=['GET', 'POST'])
def pft_results():
    if request.method == 'POST':
        search_query = request.form['search_query']
        cursor = db.cursor()
        query = "SELECT * FROM PFT_summary WHERE Participant_Number LIKE %s OR First_Name LIKE %s OR Last_Name LIKE %s"
        cursor.execute(query, ('%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%'))
        pft_data = cursor.fetchall()
        cursor.close()
        return render_template("pft_results.html", pft_data=pft_data, search_query=search_query)
    else:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM PFT_summary")
        pft_data = cursor.fetchall()
        cursor.close()
        return render_template("pft_results.html", pft_data=pft_data)

    
## @require_admin_session(['admin_access'])
@app.route('/proctor_approval', methods=['GET', 'POST'])
def proctor_approval():
    if request.method == 'POST':
        search_query = request.form['search_query']
        cursor = db.cursor()
        query = "SELECT * FROM proctor_registration WHERE name LIKE %s OR afpsn LIKE %s OR rank LIKE %s OR afp_mos LIKE %s"
        cursor.execute(query, ('%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%'))
        applications = cursor.fetchall()
        cursor.close()
        return render_template("proctor_approval.html", applications=applications, search_query=search_query)
    else:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM proctor_registration")
        applications = cursor.fetchall()
        cursor.close()
        return render_template("proctor_approval.html", applications=applications)
## @require_admin_session(['admin_access'])    
@app.route("/reject-proctor/<int:id>")
def reject_proctor(id):
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM proctor_registration WHERE id = %s", (id,))
        db.commit()
        cursor.close()
        return redirect("/proctor_approval")  # Redirect to the appropriate route
    except Exception as e:
        return jsonify({"error": str(e)}), 500

## @require_admin_session(['admin_access'])
@app.route('/participant_approval', methods=['GET', 'POST'])
def participant_approval():
    if request.method == 'POST':
        search_query = request.form['search_query']
        cursor = db.cursor()
        query = "SELECT * FROM users_account WHERE first_name LIKE %s OR afpsn LIKE %s OR rank LIKE %s OR afp_mos LIKE %s"
        cursor.execute(query, ('%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%'))
        applications = cursor.fetchall()
        cursor.close()
        return render_template("participant_approval.html", applications=applications, search_query=search_query)
    else:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users_account")
        applications = cursor.fetchall()
        cursor.close()
        return render_template("participant_approval.html", applications=applications)

@app.route("/reject-participant/<int:id>")
def reject_participant(id):
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM users_account WHERE id = %s", (id,))
        db.commit()
        cursor.close()
        return redirect("/participant_approval")  # Redirect to the appropriate route
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@app.route('/admin_participants')
# @require_admin_session(['admin_access'])
def admin_participants():
    return render_template('admin_participants.html')

@app.route('/admin_pftresults')
# @require_admin_session(['admin_access'])
def admin_pftresults():
    return render_template('admin_pftresults.html')

@app.route('/admin_developers')
# @require_admin_session(['admin_access'])
def admin_developers():
    return render_template('admin_developers.html')

@app.route('/proctor_welcome')
@require_session(['proctor_access'])
def proctor_welcome():
    return render_template('proctor_welcome.html')

# # Route for viewing data (AJAX request)
# @app.route('/view_data')
# def view_data():
#     cursor = db.cursor()
#     cursor.execute("SELECT * FROM users")  # Example query to fetch data from 'users' table
#     data = cursor.fetchall()
#     cursor.close()
#     return jsonify(data)

# Route for adding data (AJAX request)
@app.route('/add_data', methods=['POST'])
def add_data():
    # Implement logic for adding data
    pass

# Route for editing data (AJAX request)
@app.route('/edit_data', methods=['POST'])
def edit_data():
    # Implement logic for editing data
    pass

# Route for deleting data (AJAX request)
@app.route('/delete_data', methods=['POST'])
def delete_data():
    # Implement logic for deleting data
    pass

# Route for viewing data (AJAX request)
@app.route('/view_data')
def view_data():
    cursor = db.cursor()
    # Fetch data from users table
    cursor.execute("SELECT * FROM users_account")
    user_data = cursor.fetchall()
    # Fetch data from proctor_credentials table
    cursor.execute("SELECT * FROM proctor_credentials")
    proctor_data = cursor.fetchall()
    cursor.close()
    return jsonify({"users_account": user_data, "proctors": proctor_data})

# # Route for Run Page
# @app.route('/pft_kmrun')
# def pft_kmrun():
#     return render_template('pft_kmrun.html')

# # Route for Pushup Page
# @app.route('/pft_pushup')
# def pft_pushup():
#     return render_template('pft_pushup.html')

# # Route for Situp Page
# @app.route('/pft_situp')
# def pft_situp():
#     return render_template('pft_situp.html')


# @app.route('/record_pushup', methods=['POST'])
# def record_pushup():
#     if request.method == 'POST':
#         pushup_reps = request.form['pushup_reps']
        
#         cursor = db.cursor()
#         cursor.execute("INSERT INTO pft_pushup_results (reps) VALUES (%s)", (pushup_reps,))
#         db.commit()
#         cursor.close()
        
#         return redirect(url_for('proctor_access'))

# @app.route('/record_situp', methods=['POST'])
# def record_situp():
#     if request.method == 'POST':
#         situp_reps = request.form['situp_reps']
        
#         cursor = db.cursor()
#         cursor.execute("INSERT INTO pft_situp_results (reps) VALUES (%s)", (situp_reps,))
#         db.commit()
#         cursor.close()
        
#         return redirect(url_for('proctor_access'))

# @app.route('/record_kmrun', methods=['POST'])
# def record_kmrun():
#     if request.method == 'POST':
#         km_run = request.form['km_run']
        
#         cursor = db.cursor()
#         cursor.execute("INSERT INTO pft_kmrun_results (distance) VALUES (%s)", (km_run,))
#         db.commit()
#         cursor.close()
        
#         return redirect(url_for('proctor_access'))

@app.route('/pft_situp_record', methods=['GET', 'POST'])
@require_session(['proctor_access'])
def pft_situp_record():
    if request.method == 'POST':
        afpsn = request.form.get('afpsn')

        # Check if serial number exists
        cursor = db.cursor()
        cursor.execute("SELECT first_name FROM users_account WHERE afpsn = %s", (afpsn,))
        first_name = cursor.fetchone()

        if not first_name:
            return "Serial number does not exist."

        # Serial number exists, process the rest of the form data
        raw_situp = request.form.get('raw_situp')
        act_date = request.form.get('act_date')
        #participant_number = request.form.get('participant_number')

        if not (raw_situp and act_date ): #and participant_number
            return "Sit-up count, date, or participant number is missing."

        try:
            act_date = datetime.strptime(act_date, '%Y-%m-%d').date()
        except ValueError:
            # Handle parsing error
            return "Error: Invalid date format"
    

        # Process sit-up data
        cursor.execute("SELECT * FROM pft_situp WHERE afpsn = %s AND act_date = %s", (afpsn, act_date))
        existing_raw_situp = cursor.fetchone()

        if existing_raw_situp:
            print("Situp data already submitted for this act_date.")
        else:
            # Define the switch dictionary for male participants
            switch_male = {
                (21, 21): "age21_male",
                (22, 26): "age22_26_male",
                (27, 31): "age27_31_male",
                (32, 36): "age32_36_male",
                (37, 41): "age37_41_male",
                (42, 46): "age42_46_male",
                (47, 51): "age47_51_male",
                (52, 56): "age52_56_male",
                (57, 61): "age57_61_male",
                (62, float('inf')): "age62_male"
            }

            # Define the switch dictionary for female participants
            switch_female = {
                (21, 21): "age21_female",
                (22, 26): "age22_26_female",
                (27, 31): "age27_31_female",
                (32, 36): "age32_36_female",
                (37, 41): "age37_41_female",
                (42, 46): "age42_46_female",
                (47, 51): "age47_51_female",
                (52, 56): "age52_56_female",
                (57, 61): "age57_61_female",
                (62, float('inf')): "age62_female"
            }

            def execute_query(cursor, table_name, raw_situp, afpsn, act_date):
                query = f"SELECT {table_name} FROM `situp_reference` WHERE repetitions = %s;"
                cursor.execute(query, (raw_situp,))
                participant_score = cursor.fetchone()[0]
                insert_query = f"INSERT INTO pft_situp (afpsn, act_date, raw_situp, situp) VALUES (%s, %s, %s, %s)"
                cursor.execute(insert_query, (afpsn, act_date, raw_situp, participant_score))
                db.commit()  # Commit the changes to the database

                update_query = """
                    UPDATE pft_summary
                    SET raw_situp=%s, situp = %s
                    WHERE afpsn = %s AND act_date=%s
                """
                cursor.execute(update_query, (raw_situp, participant_score, afpsn,act_date))
                db.commit()

            def process_participant(cursor, afpsn, act_date):
                # Get participant's age
                cursor.execute("SELECT DATEDIFF(CURDATE(), birth_date) DIV 365 FROM users_account WHERE afpsn = %s", (afpsn,))
                participant_age = cursor.fetchone()[0]

                # Get participant's gender
                cursor.execute("SELECT gender FROM `users_account` WHERE afpsn = %s;", (afpsn,))
                participant_gender = cursor.fetchone()[0]

                if participant_gender == "M":
                    switch = switch_male
                else:
                    switch = switch_female

                for age_range, table_name in switch.items():
                    if age_range[0] <= participant_age <= age_range[1]:
                        print(f"Participant is {age_range[0]} - {age_range[1]}")
                        execute_query(cursor, table_name, raw_situp, afpsn, act_date)
                        break

            process_participant(cursor, afpsn, act_date)

        return "Data submitted successfully."

    return render_template('pft_situp.html')

@app.route('/check_existing_situp_data', methods=['GET'])
def check_existing_situp_data():
    afpsn = request.args.get('afpsn')

    # Check if data exists for today's date for the specified afpsn
    cursor = db.cursor()
    today_date = datetime.now().date()
    cursor.execute("SELECT * FROM pft_situp WHERE afpsn = %s AND act_date = %s", (afpsn, today_date))
    existing_data = cursor.fetchone()

    if existing_data:
        return jsonify(True)  # Data exists
    else:
        return jsonify(False)  # No data found

######

@app.route('/pft_pushup_record', methods=['GET', 'POST'])
@require_session(['proctor_access'])
def pft_pushup_record():
    if request.method == 'POST':
        afpsn = request.form.get('afpsn')

        # Check if serial number exists
        cursor = db.cursor()
        cursor.execute("SELECT first_name FROM users_account WHERE afpsn = %s", (afpsn,))
        first_name = cursor.fetchone()

        if not first_name:
            return "Serial number does not exist."

        # Serial number exists, process the rest of the form data
        raw_pushup = request.form.get('raw_pushup')
        act_date = request.form.get('act_date')
        #participant_number = request.form.get('participant_number')

        if not (raw_pushup and act_date ): #and participant_number
            return "Push-up count, date, or participant number is missing."

        try:
            act_date = datetime.strptime(act_date, '%Y-%m-%d').date()
        except ValueError:
            # Handle parsing error
            return "Error: Invalid date format"
        
        cursor.execute("SELECT * FROM pft_pushup WHERE afpsn = %s AND act_date = %s", (afpsn, act_date))
        existing_raw_pushup = cursor.fetchone()

        if existing_raw_pushup:
            print("Pushup data already submitted for this act_date.")
        else:
            # Define the switch dictionary for male participants
            switch_male = {
                (21, 21): "age21_male",
                (22, 26): "age22_26_male",
                (27, 31): "age27_31_male",
                (32, 36): "age32_36_male",
                (37, 41): "age37_41_male",
                (42, 46): "age42_46_male",
                (47, 51): "age47_51_male",
                (52, 56): "age52_56_male",
                (57, 61): "age57_61_male",
                (62, float('inf')): "age62_male"
            }

            # Define the switch dictionary for female participants
            switch_female = {
                (21, 21): "age21_female",
                (22, 26): "age22_26_female",
                (27, 31): "age27_31_female",
                (32, 36): "age32_36_female",
                (37, 41): "age37_41_female",
                (42, 46): "age42_46_female",
                (47, 51): "age47_51_female",
                (52, 56): "age52_56_female",
                (57, 61): "age57_61_female",
                (62, float('inf')): "age62_female"
            }

            def execute_query(cursor, table_name, raw_pushup, afpsn, act_date):
                query = f"SELECT {table_name} FROM `pushup_reference` WHERE repetitions = %s;"
                cursor.execute(query, (raw_pushup,))
                participant_score = cursor.fetchone()[0]
                insert_query = f"INSERT INTO pft_pushup (afpsn, act_date, raw_pushup, pushup) VALUES (%s, %s, %s, %s)"
                cursor.execute(insert_query, (afpsn, act_date, raw_pushup, participant_score))
                db.commit()  

                # Summary table insert data
                cursor.execute("SELECT rank, first_name, middle_name, surname, afpsn, afp_mos, gender, unit FROM users_account WHERE afpsn = %s", (afpsn,))
                user_data = cursor.fetchone()
                # Insert data into pft_summary table
                summary_query = "INSERT INTO pft_summary (rank, first_name, middle_name, last_name, afpsn, afp_mos, gender, raw_pushup, pushup, situp, kmrun, unit, act_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                cursor.execute(summary_query, (user_data[0], user_data[1], user_data[2], user_data[3], user_data[4], user_data[5], user_data[6], raw_pushup, participant_score, 0, 0,user_data[7], act_date))
                db.commit() 

            def process_participant(cursor, afpsn, act_date):
                # Get participant's age
                cursor.execute("SELECT DATEDIFF(CURDATE(), birth_date) DIV 365 FROM users_account WHERE afpsn = %s", (afpsn,))
                participant_age = cursor.fetchone()[0]

                # Get participant's gender
                cursor.execute("SELECT gender FROM `users_account` WHERE afpsn = %s;", (afpsn,))
                participant_gender = cursor.fetchone()[0]

                if participant_gender == "M":
                    switch = switch_male
                else:
                    switch = switch_female

                for age_range, table_name in switch.items():
                    if age_range[0] <= participant_age <= age_range[1]:
                        print(f"Participant is {age_range[0]} - {age_range[1]}")
                        execute_query(cursor, table_name, raw_pushup, afpsn, act_date)
                        break

            process_participant(cursor, afpsn, act_date)

        return "Data submitted successfully."
        
    return render_template('pft_pushup.html')

@app.route('/check_existing_pushup_data', methods=['GET'])
def check_existing_pushup_data():
    afpsn = request.args.get('afpsn')

    # Check if data exists for today's date for the specified afpsn
    cursor = db.cursor()
    today_date = datetime.now().date()
    cursor.execute("SELECT * FROM pft_pushup WHERE afpsn = %s AND act_date = %s", (afpsn, today_date))
    existing_data = cursor.fetchone()

    if existing_data:
        return jsonify(True)  # Data exists
    else:
        return jsonify(False)  # No data found

######

@app.route('/pft_kmrun_record', methods=['GET', 'POST'])
@require_session(['proctor_access'])
def pft_kmrun_record():
    if request.method == 'POST':
        afpsn = request.form.get('afpsn')

        # Check if serial number exists
        cursor = db.cursor()
        cursor.execute("SELECT first_name FROM users_account WHERE afpsn = %s", (afpsn,))
        first_name = cursor.fetchone()

        if not first_name:
            return "Serial number does not exist."

        # Serial number exists, process the rest of the form data
        raw_kmrun = request.form.get('raw_kmrun')
        act_date = request.form.get('act_date')
        #participant_number = request.form.get('participant_number')

        if not (raw_kmrun and act_date ): #and participant_number
            return "KM run count, date, or participant number is missing."

        try:
            act_date = datetime.strptime(act_date, '%Y-%m-%d').date()
        except ValueError:
            # Handle parsing error
            return "Error: Invalid date format"
        
        cursor.execute("SELECT * FROM pft_kmrun WHERE afpsn = %s AND act_date = %s", (afpsn, act_date))
        existing_raw_kmrun = cursor.fetchone()

        if existing_raw_kmrun:
            print("KM run data already submitted for this act_date.")
        else:
             cursor.execute("INSERT INTO pft_kmrun (afpsn,raw_kmrun,act_date) VALUES (%s, %s,%s)",
                           (afpsn, raw_kmrun,act_date, ))
             db.commit()  

             update_query = """
                    UPDATE pft_summary
                    SET kmrun = %s
                    WHERE afpsn = %s AND act_date=%s
                """
             cursor.execute(update_query, ( raw_kmrun, afpsn,act_date))
             db.commit()

        return "Data submitted successfully."

    return render_template('pft_kmrun.html')

@app.route('/check_existing_kmrun_data', methods=['GET'])
def check_existing_kmrun_data():
    afpsn = request.args.get('afpsn')

    # Check if data exists for today's date for the specified afpsn
    cursor = db.cursor()
    today_date = datetime.now().date()
    cursor.execute("SELECT * FROM pft_kmrun WHERE afpsn = %s AND act_date = %s", (afpsn, today_date))
    existing_data = cursor.fetchone()

    if existing_data:
        return jsonify(True)  # Data exists
    else:
        return jsonify(False)  # No data found
######

if __name__ == '__main__':
    app.run(debug=True)