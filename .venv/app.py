from flask import Flask, render_template, redirect, url_for, request, jsonify, session
from datetime import date, datetime
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
        #return redirect(url_for('lobby'))
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
            # Display alert and redirect to the same page
            return render_template('proctor_login.html', alert="Incorrect credentials!")
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
    today = date.today().isoformat()  # Get today's date in ISO format (YYYY-MM-DD)
    cursor.execute("SELECT first_name FROM users_pft WHERE afpsn LIKE %s AND activity_date = %s", (afpsn + '%',today))
    first_names = cursor.fetchall()

    suggestions = ''.join(f"<div onclick='fillSerialNumber(\"{first_name[0]}\")'>{first_name[0]}</div>" for first_name in first_names)
    return suggestions

@app.route('/get_serial_number')
def get_serial_number():
    first_name = request.args.get('username')

    cursor = db.cursor(dictionary=True)  # Set dictionary=True
    today = date.today().isoformat()  # Get today's date in ISO format (YYYY-MM-DD)
    cursor.execute("SELECT * FROM users_pft WHERE first_name = %s AND activity_date = %s", (first_name, today,))
    afpsn_record = cursor.fetchone()

    if afpsn_record:
        afpsn = afpsn_record['afpsn'].strip('"')  # Remove quotation marks
        return jsonify(afpsn)
    else:
        return jsonify(None)

@app.route('/search_serial', methods=['GET'])
def search_serial():
    afpsn = request.args.get('afpsn')
    afpsn = afpsn.strip('"')
    # Check if serial number exists
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users_pft WHERE afpsn = %s", (afpsn,))
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
        act_date = datetime.now().date()
        #participant_number = request.form.get('participant_number')

        if not (raw_pushup and raw_situp and act_date ): #and participant_number
            return "Push-up count is missing."

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
                cursor.execute("SELECT firstname FROM users_pft WHERE afpsn = %s", (afpsn,))
                name = cursor.fetchone()
                
                insert_query = f"INSERT INTO pft_situp (afpsn, name, act_date, raw_situp, situp) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(insert_query, (afpsn, name, act_date, raw_pushup, participant_score))
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

# # Route for Admin registration page
# @app.route('/admin_registration', methods=['GET', 'POST'])
# def admin_registration():
#     if request.method == 'POST':
#         username = request.form['username']
#         password = request.form['password']
        
#         cursor = db.cursor()
#         # Insert data into admin_credentials table
#         cursor.execute("INSERT INTO admin_credentials (username, password) VALUES (%s, %s)", (username, password))
#         db.commit()
#         cursor.close()
        
#         return redirect(url_for('admin_login'))  # Redirect to Admin login page after registration
#     else:
#         return render_template('admin_registration.html')

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
            # Display alert and redirect to the same page
            return render_template('admin_login.html', alert="Incorrect credentials!")
    return render_template('admin_login.html')


# Route for Admin Access Page
@app.route('/admin_access')
@require_admin_session(['admin_access'])
def admin_access():
    return render_template('admin_access.html')

#Code for the proctor list

@app.route('/passed_proctors_list')
def passed_proctors_list():
    cursor = db.cursor(dictionary=True)
    
    # Fetch data from proctor_account table
    query = "SELECT name, afpsn, rank, afp_mos, date_added FROM proctor_account"
    cursor.execute(query)
    proctor_list = cursor.fetchall()

    return render_template('passedProctor.html', proctor_list=proctor_list)

@app.route('/delete_proctor_list/<int:afpsn>')
def delete_proctor(afpsn):
    cursor = db.cursor()
    
    # Delete the proctor with the given ID
    query = "DELETE FROM proctor_account WHERE afpsn = %s"
    cursor.execute(query, (afpsn,))
    db.commit()
    
    return redirect('/passed_proctors_list')  # Redirect to the page with the updated proctor list

## @require_admin_session(['admin_access'])    
@app.route("/accept-proctor/<int:id>")
def accept_proctor(id):
    try:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM proctor_registration WHERE id = %s", (id,))
        proctor_account_reg=cursor.fetchone() #     
        act_date = datetime.now().date()
        cursor.execute("INSERT INTO proctor_account (name,afpsn,password,rank,afp_mos,date_added) VALUES (%s, %s,%s, %s,%s,%s)", (proctor_account_reg[1],proctor_account_reg[2],proctor_account_reg[3],proctor_account_reg[4],proctor_account_reg[5],act_date))
        cursor.execute("DELETE FROM proctor_registration WHERE id = %s", (id,))
        db.commit()
        cursor.close()
        return redirect("/proctor_approval")  # Redirect to the appropriate route
    except Exception as e:
        return jsonify({"error": str(e)}), 500

#end of code for proctor list

# Routes for Admin-specific pages
@app.route('/admin_approval')
# @require_admin_session(['admin_access'])
def admin_approval():
    return render_template('admin_approval.html')

from datetime import datetime

from datetime import datetime

from datetime import datetime

@app.route('/pft_results', methods=['GET', 'POST'])
def pft_results():
    if request.method == 'POST':
        search_query = request.form['search_query']
        cursor = db.cursor()
        query = "SELECT * FROM PFT_summary WHERE Participant_Number LIKE %s OR First_Name LIKE %s OR Last_Name LIKE %s"
        cursor.execute(query, ('%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%'))
        pft_data = cursor.fetchall()
        cursor.close()
        # Add age to pft_data
        pft_data_with_age = []
        for row in pft_data:
            afpsn = row[5]  # Assuming afpsn is the 6th column in the PFT_summary table
            cursor = db.cursor()
            try:
                cursor.execute("SELECT CASE WHEN birth_date IS NULL THEN NULL ELSE DATEDIFF(CURDATE(), birth_date) DIV 365 END FROM users_account WHERE afpsn = %s", (afpsn,))
                age_result = cursor.fetchone()
                if age_result:
                    age = age_result[0]
                else:
                    age = None
                # Insert age at 9th index in the tuple
                row_with_age = row[:8] + (age,) + row[8:]
                pft_data_with_age.append(row_with_age)
            except Exception as e:
                print("Error fetching age for afpsn:", afpsn)
                print(e)
            finally:
                cursor.close()
        return render_template("pft_results.html", pft_data=pft_data_with_age, search_query=search_query)
    else:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM PFT_summary")
        pft_data = cursor.fetchall()
        cursor.close()
        # Add age to pft_data
        pft_data_with_age = []
        for row in pft_data:
            afpsn = row[5]  # Assuming afpsn is the 6th column in the PFT_summary table
            cursor = db.cursor()
            try:
                cursor.execute("SELECT CASE WHEN birth_date IS NULL THEN NULL ELSE DATEDIFF(CURDATE(), birth_date) DIV 365 END FROM users_account WHERE afpsn = %s", (afpsn,))
                age_result = cursor.fetchone()
                if age_result:
                    age = age_result[0]
                else:
                    age = None
                # Insert age at 9th index in the tuple
                row_with_age = row[:8] + (age,) + row[8:]
                pft_data_with_age.append(row_with_age)
            except Exception as e:
                print("Error fetching age for afpsn:", afpsn)
                print(e)
            finally:
                cursor.close()
        return render_template("pft_results.html", pft_data=pft_data_with_age)

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

## @require_admin_session(['admin_access'])
@app.route('/participant_registration/<int:id>', methods=['GET', 'POST'])
def participant_registration(id):
    try:
        cursor = db.cursor(dictionary=True)
        query = "SELECT * FROM users_account WHERE id = %s"
        cursor.execute(query, (id,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            return render_template("admin_participants.html",user=user) #, applications=applications
        else:
            return "User not found", 404  # Return a 404 error if the user is not found
    except Exception as e:
        return f"An error occurred: {str(e)}", 500  # Return a 500 error for any exception
    
    #  participant_number = request.form['participant_number_id']
    #  activity_date = request.form['activity_date_id']
    
    #  cursor = db.cursor()
    #  cursor.execute("SELECT * FROM users_account WHERE id = %s", (id,))
    #   applications = cursor.fetchone()
      #cursor.execute("INSERT INTO participant_registration (rank,first_name, middle_name,surname,afpsn,afp_mos, gender,birthdate,unit,company,participant_number,activity_date) VALUES (%s, %s,%s, %s,%s,%s, %s,%s, %s,%s,%s,%s)", (applications[1],applications[2],applications[3],applications[4],applications[5],applications[6],applications[7],applications[8],applications[9],applications[10],participant_number,activity_date))
    #   cursor.execute("DELETE FROM users_account WHERE id = %s", (id,))    
    #   db.commit()

    #   cursor.close()

@app.route('/register-pft/<int:id>', methods=['POST'])
def register_pft(id):
    try:
        # Fetch user data from users_account table
        cursor = db.cursor(dictionary=True)
        query = "SELECT * FROM users_account WHERE id = %s"
        cursor.execute(query, (id,))
        user = cursor.fetchone()

        # Extract data from the form
        participant_number = request.form['participant_number']
        activity_date = request.form['activity_date']

        if not (participant_number):
            return "Participant number or activity date is missing."

        # Check if participant already exists in users_pft
        query_check = "SELECT * FROM users_pft WHERE afpsn = %s AND activity_date = %s"
        cursor.execute(query_check, (user['afpsn'], activity_date))
        existing_participant = cursor.fetchone()

        if existing_participant:
            return "<script>alert('Participant already registered for the given activity date'); window.location.href = '/participant_registration/24';</script>"

        # Insert data into users_pft table
        query_insert = "INSERT INTO users_pft (rank, first_name, middle_name, surname, afpsn, afp_mos, gender, birth_date, unit, company, activity_date, participant_number) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        values = (user['rank'], user['first_name'], user['middle_name'], user['surname'], user['afpsn'], user['afp_mos'], user['gender'], user['birth_date'], user['unit'], user['company'], activity_date, participant_number)
        cursor.execute(query_insert, values)
        db.commit()

        # Close the cursor after executing the insert query
        cursor.close()

        # Reopen the cursor to execute the next query
        cursor = db.cursor(dictionary=True)

        # Fetch data from users_pft table
        cursor.execute("SELECT * FROM users_pft WHERE afpsn = %s", (user['afpsn'],))
        users_pft_data = cursor.fetchall()[0]

        # Insert data into pft_summary table
        summary_query = "INSERT INTO pft_summary (participant_number, rank, first_name, middle_name, last_name, afpsn, afp_mos, gender, raw_pushup, pushup, situp, kmrun, unit, act_date) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(summary_query, (users_pft_data['participant_number'], users_pft_data['rank'], users_pft_data['first_name'], users_pft_data['middle_name'], users_pft_data['surname'], users_pft_data['afpsn'], users_pft_data['afp_mos'], users_pft_data['gender'], 0, 0, 0, 0, users_pft_data['unit'], activity_date))
        db.commit()

        cursor.close()  # Close the cursor after executing the second set of queries

        return redirect("/participant_approval")  # Redirect to success page after registration
    except Exception as e:
        return f"An error occurred: {str(e)}", 500  # Return a 500 error for any exception



# Route to render the edit user page
@app.route('/edit-user/<int:user_id>')
def edit_user(user_id):
    try:
        cursor = db.cursor(dictionary=True)
        query = "SELECT * FROM users_account WHERE id = %s"
        cursor.execute(query, (user_id,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            return render_template('edit_user.html', user=user)
        else:
            return "User not found", 404  # Return a 404 error if the user is not found
    except Exception as e:
        return f"An error occurred: {str(e)}", 500  # Return a 500 error for any exception

# Route to update user account information
@app.route('/update-user/<int:user_id>', methods=['POST'])  # Allow only POST method for this route
def update_user(user_id):
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
        query = "UPDATE users_account SET rank=%s, first_name=%s, middle_name=%s, surname=%s, afpsn=%s, afp_mos=%s, gender=%s, birth_date=%s, unit=%s, company=%s WHERE id=%s"
        cursor.execute(query, (rank, first_name, middle_name, surname, afpsn, afp_mos, gender, birth_date, unit, company, user_id))
        db.commit()
        cursor.close()
        return redirect("/participant_approval")  # Redirect to the appropriate route


# Route to render the edit summary page ADD LAST NAME
@app.route('/edit-summary/<string:afpsn>/<string:act_date>')
def edit_summary(afpsn, act_date):
    try:
        cursor = db.cursor(dictionary=True)
        query = "SELECT * FROM pft_summary WHERE afpsn = %s AND act_date = %s"
        cursor.execute(query, (afpsn, act_date))
        summary = cursor.fetchone()
        cursor.close()
        if summary:
            return render_template('edit_summary.html', summary=summary)
        else:
            return "Summary not found", 404  # Return a 404 error if the user is not found
    except Exception as e:
        return f"An error occurred: {str(e)}", 500  # Return a 500 error for any exception

# Route to update summary account information
@app.route('/update-summary/<string:afpsn_value>/<string:act_date_value>', methods=['POST'])  # Allow only POST method for this route
def update_summary(afpsn_value, act_date_value):
    if request.method == 'POST':
        # Your update logic here using afpsn and act_date
        rank = request.form['rank']
        first_name = request.form['first_name']
        middle_name = request.form['middle_name']
        last_name = request.form['last_name']
        afpsn = request.form['afpsn']
        afp_mos = request.form['afp_mos']
        gender = request.form['gender']
        # age = request.form['age']
        raw_pushup = request.form['raw_pushup']
        pushup = request.form['pushup']
        raw_situp = request.form['raw_situp']
        situp = request.form['situp']
        raw_kmrun = request.form['raw_kmrun']

        kmrun = request.form['kmrun']
        total = request.form['total']
        average = request.form['average']
        remarks = request.form['remarks']
        unit = request.form['unit']

        cursor = db.cursor()
        query = "UPDATE pft_summary SET rank=%s, first_name=%s, middle_name=%s, last_name=%s, afpsn=%s, afp_mos=%s, gender=%s, raw_pushup=%s, pushup=%s, raw_situp=%s, situp=%s, raw_kmrun=%s, kmrun=%s, total=%s, average=%s, remarks=%s, unit=%s WHERE afpsn=%s AND act_date=%s"
        cursor.execute(query, (rank, first_name, middle_name, last_name, afpsn, afp_mos, gender, raw_pushup, pushup, raw_situp, situp, raw_kmrun, kmrun, total, average, remarks, unit, afpsn_value, act_date_value))
        db.commit()
        cursor.close()
        return redirect("/pft_results")  # Redirect to the appropriate route

@app.route('/add-kmrun/<string:afpsn>/<string:act_date>')
def add_kmrun(afpsn, act_date):
    try:
        cursor = db.cursor(dictionary=True)
        query = "SELECT * FROM pft_summary WHERE afpsn = %s AND act_date = %s"
        cursor.execute(query, (afpsn, act_date))
        summary = cursor.fetchone()
        cursor.close()
        if summary:
            return render_template('addKMrun.html', summary=summary)
        else:
            return "Summary not found", 404  # Return a 404 error if the user is not found
    except Exception as e:
        return f"An error occurred: {str(e)}", 500  # Return a 500 error for any exception

# Route to update summary account information
@app.route('/update-kmrun/<string:afpsn_value>/<string:act_date_value>', methods=['POST'])
def update_kmrun(afpsn_value, act_date_value):
    if request.method == 'POST':
        try:
            km_minutes = request.form['km_minutes']
            km_seconds = request.form['km_seconds']
            raw_kmrun_text = f"{km_minutes}:{km_seconds}"  # Combine minutes and seconds with a colon
            raw_kmrun = int(km_minutes + km_seconds)

            cursor = db.cursor(dictionary=True)

            switch_male = {
                (21, 25): "age21-25_male",
                (26, 30): "age26-30_male",
                (31, 35): "age31-35_male",
                (36, 40): "age36-40_male",
                (41, 45): "age41-45_male",
                (46, 50): "age46-50_male",
                (51, 55): "age51-55_male",
                (56, float('inf')): "age56-60_male",
            }

            switch_female = {
                (21, 25): "age21-25_female",
                (26, 30): "age26-30_female",
                (31, 35): "age31-35_female",
                (36, 40): "age36-40_female",
                (41, 45): "age41-45_female",
                (46, 50): "age46-50_female",
                (51, 55): "age51-55_female",
                (56, float('inf')): "age56-60_female",
            }

            switch_kmrun = {
                (1108, 1123): "11:08 - 11:23",
                (1124, 1140): "11:24 - 11:40",
                (1141, 1157): "11:41 - 11:56",
                (1158, 1214): "11:58 - 12:14",
                (1215, 1231): "12:15 - 12:31",
                (1232, 1248): "12:32 - 12:48",
                (1249, 1305): "12:49 - 13:05",
                (1306, 1322): "13:06 - 13:22",
                (1323, 1339): "13:23 - 13:39",
                (1340, 1356): "13:40 - 13:56",
                (1357, 1413): "13:57 - 14:13",
                (1414, 1430): "14:14 - 14:30",
                (1431, 1447): "14:31 - 14:47",
                (1448, 1504): "14:48 - 15:04",
                (1505, 1521): "15:05 - 15:21",
                (1522, 1538): "15:22 - 15:38",
                (1539, 1555): "15:39 - 15:55",
                (1556, 1612): "15:56 - 16:12",
                (1613, 1629): "16:13 - 16:29",
                (1630, 1646): "16:30 - 16:46",
                (1647, 1703): "16:47 - 17:03",
                (1704, 1720): "17:04 - 17:20",
                (1721, 1737): "17:21 - 17:37",
                (1738, 1754): "17:38 - 17:54",
                (1755, 1811): "17:55 - 18:11",
                (1812, 1828): "18:12 - 18:28",
                (1829, 1845): "18:29 - 18:45",
                (1846, 1902): "18:46 - 19:02",
                (1903, 1919): "19:03 - 19:19",
                (1920, 1936): "19:20 - 19:36",
                (1937, 1953): "19:37 - 19:53",
                (1954, 2010): "19:54 - 20:10",
                (2011, 2027): "20:11 - 20:27",
                (2028, 2044): "20:28 - 20:44",
                (2045, 2101): "20:45 - 21:01",
                (2102, 2118): "21:02 - 21:18",
                (2119, 2135): "21:19 - 21:35",
                (2136, 2152): "21:36 - 21:52",
                (2153, 2209): "21:53 - 22:09",
                (2210, 2226): "22:10 - 22:26",
                (2227, 2243): "22:27 - 22:43",
                (2244, 2300): "22:44 - 23:00",
                (2301, 2317): "23:01 - 23:17",
                (2318, 2334): "23:18 - 23:34",
                (2335, 2351): "23:35 - 23:51",
                (2351, 2352): "23:52"
            }

            # Adjust raw_kmrun if it's below the lowest or above the highest possible score
            if raw_kmrun < 1108: # Highest
                raw_kmrun = 1108
            elif raw_kmrun > 2352: # Lowest
                raw_kmrun = 2352

            # Execute the queries to get gender and age
            cursor.execute("SELECT gender FROM `users_account` WHERE afpsn = %s;", (afpsn_value,))
            gender_result = cursor.fetchone()

            cursor.execute("SELECT DATEDIFF(CURDATE(), birth_date) DIV 365 AS age FROM users_account WHERE afpsn = %s", (afpsn_value,))
            age_result = cursor.fetchone()

            # Check if gender and age results are fetched successfully
            if gender_result and 'age' in age_result:
                gender = gender_result['gender']
                age = age_result['age']  # accessing age by key

                # Determine which switch dictionary to use based on gender
                switch_dict = switch_male if gender == 'M' else switch_female

                # Determine the appropriate column in kmrun_reference based on age group
                selected_column = None
                for age_range, column in switch_dict.items():
                    if age_range[0] <= age <= age_range[1]:
                        selected_column = column
                        break

                # Convert raw_kmrun to time range
                selected_time_range = None
                for time_range, value in switch_kmrun.items():
                    if time_range[0] <= raw_kmrun <= time_range[1]:
                        selected_time_range = value
                        break

                if selected_column and selected_time_range:
                    # Query kmrun_reference table to get kmrun value
                    query_select_kmrun = f"SELECT `{selected_column}` FROM kmrun_reference WHERE `time` = %s;"
                    cursor.execute(query_select_kmrun, (selected_time_range,))
                    kmrun_result = cursor.fetchone()

                    if kmrun_result and selected_column in kmrun_result:
                        kmrun_value = kmrun_result[selected_column]
                        # Update pft_summary table
                        query_update_kmrun = "UPDATE pft_summary SET raw_kmrun = %s, kmrun = %s WHERE afpsn = %s AND act_date = %s"
                        cursor.execute(query_update_kmrun, (raw_kmrun_text, kmrun_value, afpsn_value, act_date_value))
                        db.commit()

                    else:
                        # Handle case when kmrun is not found or column is not in result
                        pass
                else:
                    # Handle case when selected column or time range is not found
                    pass
            else:
                # Handle case when gender or age is not found
                pass
            return redirect("/pft_results")

        except Exception as e:
            # Handle exceptions, log errors, and provide appropriate response
            print(f"An error occurred: {str(e)}")
            return "An error occurred while processing the request."

        # Fetch pushup, situp, and kmrun grades from pft_summary table
        #query_fetch_grades = "SELECT pushup, situp, kmrun FROM pft_summary WHERE afpsn = %s AND act_date = %s"
        #cursor.execute(query_fetch_grades, (afpsn_value, act_date_value))
        #grades_data = cursor.fetchone()

        # Calculate the average of pushup, situp, and kmrun grades
        #pushup_grade = grades_data['pushup']
        #situp_grade = grades_data['situp']
        #total_grade = pushup_grade + situp_grade + kmrun
        #average_grade = total_grade / 3

        # Determine pass or fail remark
        #remark = "Passed" if pushup_grade >= 75 and situp_grade >= 75 and kmrun >= 75 else "Failed"

        # Update total and average grades, and remark in pft_summary table
        #query_update_summary = "UPDATE pft_summary SET total = %s, average = %s, remarks = %s WHERE afpsn = %s AND act_date = %s"
        #cursor.execute(query_update_summary, (total_grade, average_grade, remark, afpsn_value, act_date_value))
        #db.commit()
    

# Route to update summary account information
@app.route('/compute-results/<string:afpsn_value>/<string:act_date_value>', methods=['POST'])
def compute_results(afpsn_value, act_date_value):
    if request.method == 'POST':
        try:
            cursor = db.cursor(dictionary=True)

        #Fetch pushup, situp, and kmrun grades from pft_summary table
            query_fetch_grades = "SELECT pushup, situp, kmrun FROM pft_summary WHERE afpsn = %s AND act_date = %s"
            cursor.execute(query_fetch_grades, (afpsn_value, act_date_value))
            grades_data = cursor.fetchone()

        # Calculate the average of pushup, situp, and kmrun grades
            kmrun = grades_data['kmrun']
            pushup_grade = grades_data['pushup']
            situp_grade = grades_data['situp']
            total_grade = pushup_grade + situp_grade + kmrun
            average_grade = total_grade / 3

        # Determine pass or fail remark
            remark = "Passed" if pushup_grade >= 70 and situp_grade >= 70 and kmrun >= 70 else "Failed"

        # Update total and average grades, and remark in pft_summary table
            query_update_summary = "UPDATE pft_summary SET total = %s, average = %s, remarks = %s WHERE afpsn = %s AND act_date = %s"
            cursor.execute(query_update_summary, (total_grade, average_grade, remark, afpsn_value, act_date_value))
            db.commit()
            cursor.close()
            return redirect("/pft_results")

        except Exception as e:
            # Handle exceptions, log errors, and provide appropriate response
            print(f"An error occurred: {str(e)}")
            return "An error occurred while processing the request."

## @require_admin_session(['admin_access'])    
#@app.route("/accept-participant/<int:id>")
#def accept_proctor(id):
#    try:
#        cursor = db.cursor()
#        cursor.execute("SELECT * FROM users_account WHERE id = %s", (id,))
#        proctor_account_reg=cursor.fetchone() #        
#        cursor.execute("INSERT INTO proctor_account (name,afpsn,password,rank,afp_mos) VALUES (%s, %s,%s, %s,%s)", (proctor_account_reg[1],proctor_account_reg[2],proctor_account_reg[3],proctor_account_reg[4],proctor_account_reg[5]))
#        cursor.execute("DELETE FROM proctor_registration WHERE id = %s", (id,))
#        db.commit()
#        cursor.close()
#        return redirect("/proctor_approval")  # Redirect to the appropriate route
#    except Exception as e:
#        return jsonify({"error": str(e)}), 500


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

@app.route('/pft_situp_record', methods=['GET', 'POST'])
@require_session(['proctor_access'])
def pft_situp_record():
    if request.method == 'POST':
        afpsn = request.form.get('afpsn')
        afpsn = afpsn.strip('"')
        # Check if serial number exists
        cursor = db.cursor()
        cursor.execute("SELECT first_name FROM users_account WHERE afpsn = %s", (afpsn,))
        first_name = cursor.fetchone()

        if not first_name:
            return "Serial number does not exist."

        # Serial number exists, process the rest of the form data
        raw_situp = request.form.get('raw_situp')
        act_date = datetime.now().date()
        #participant_number = request.form.get('participant_number')

        if not (raw_situp): #and participant_number
            # return "Sit-up count is missing."
            return "<script>alert('Sit-up count is missing!'); window.location.href = '/pft_situp_record';</script>"

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
                cursor.execute("SELECT first_name FROM users_pft WHERE afpsn = %s", (afpsn,))
                name = cursor.fetchone()
                
                insert_query = f"INSERT INTO pft_situp (afpsn, name, act_date, raw_situp, situp) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(insert_query, (afpsn, name[0], act_date, raw_situp, participant_score))
                db.commit()  # Commit the changes to the database




                cursor.execute("SELECT participant_number FROM users_pft WHERE afpsn = %s", (afpsn,))
                participant_number = cursor.fetchone()

                update_query = """
                    UPDATE pft_summary
                    SET  participant_number=%s, raw_situp=%s, situp = %s
                    WHERE afpsn = %s AND act_date=%s
                """
                cursor.execute(update_query, (participant_number[0],raw_situp, participant_score, afpsn,act_date))
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

        # return "Data submitted successfully."

    return render_template('pft_situp.html')

@app.route('/check_existing_situp_data', methods=['GET'])
def check_existing_situp_data():
    afpsn = request.args.get('afpsn')

    # Check if data exists for today's date for the specified afpsn
    cursor = db.cursor()
    today_date = datetime.now().date()
    cursor.execute("SELECT * FROM pft_situp WHERE afpsn = %s AND act_date = %s", (afpsn, today_date))
    existing_data = cursor.fetchone()

    cursor.execute("SELECT * FROM pft_pushup WHERE afpsn = %s AND act_date = %s", (afpsn, today_date))
    did_pushup = cursor.fetchone()


    if existing_data:
        return jsonify(True)  # Data exists
    else:
        if did_pushup:
            return jsonify(False)  # Data exists

        else:
            return jsonify(True)  # No data found

######

@app.route('/pft_pushup_record', methods=['GET', 'POST'])
@require_session(['proctor_access'])
def pft_pushup_record():
    if request.method == 'POST':
        afpsn = request.form.get('afpsn')
        afpsn = afpsn.strip('"')
        # Check if serial number exists
        cursor = db.cursor()
        cursor.execute("SELECT first_name FROM users_account WHERE afpsn = %s", (afpsn,))
        first_name = cursor.fetchone()

        if not first_name:
            return "Serial number does not exist."

        # Serial number exists, process the rest of the form data
        raw_pushup = request.form.get('raw_pushup')
        act_date = datetime.now().date()

        #participant_number = request.form.get('participant_number')

        if not (raw_pushup): #and participant_number
            # return "Push-up count is missing."
            return "<script>alert('Push-up count is missing!'); window.location.href = '/pft_pushup_record';</script>"
        
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
                cursor.execute("SELECT first_name FROM users_pft WHERE afpsn = %s", (afpsn,))
                name = cursor.fetchone()
                insert_query = f"INSERT INTO pft_pushup (afpsn, name, act_date, raw_pushup, pushup) VALUES (%s, %s,%s, %s, %s)"
                cursor.execute(insert_query, (afpsn, name[0],act_date, raw_pushup, participant_score))
                db.commit()  

                # Summary table insert data
                cursor.execute("SELECT rank, first_name, middle_name, surname, afpsn, afp_mos, gender, unit FROM users_account WHERE afpsn = %s", (afpsn,))
                user_data = cursor.fetchone()
                cursor.execute("SELECT participant_number FROM users_pft WHERE afpsn = %s", (afpsn,))
                participant_number = cursor.fetchone()
                # Insert data into pft_summary table
                # Summary table insert data
                
                update_query = """
                    UPDATE pft_summary
                    SET  raw_pushup=%s, pushup = %s
                    WHERE afpsn = %s AND act_date=%s
                """
                cursor.execute(update_query, (raw_pushup, participant_score, afpsn,act_date))
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

        # return "Data submitted successfully."
        
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
        afpsn = afpsn.strip('"')
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

        # return "Data submitted successfully."

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