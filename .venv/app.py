from flask import Flask, render_template, redirect, url_for, request, jsonify, session
from datetime import datetime
import mysql.connector

app = Flask(__name__)

# Connect to MySQL database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  
    database="registration_test"
)

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
        afpos_mos = request.form['afpos_mos']
        gender = request.form['gender']
        birth_date = request.form['birth_date']
        unit = request.form['unit']
        company = request.form['company']
        cursor = db.cursor()
        cursor.execute("INSERT INTO users_account (rank, first_name, middle_name, surname, afpsn, afpos_mos, gender, birth_date, unit, company) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", (rank, first_name, middle_name, surname, afpsn, afpos_mos, gender, birth_date, unit, company))
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
            # Store proctor information in session
            session['proctor_access'] = proctor_account # SESSION IS BROKEN ATM
            # Redirect to proctor_access.html
            return redirect(url_for('proctor_access'))
        else:
            # Redirect to proctor_login.html with error message
            return render_template('proctor_login.html', error="Invalid AFPSN or password. Please try again.")
    return render_template('proctor_login.html')

# Route for Proctor Registration Page
@app.route('/proctor_registration', methods=['GET', 'POST'])
def proctor_registration():
    if request.method == 'POST':
        name = request.form['name']
        afpsn = request.form['afpsn']
        password = request.form['password']
        rank = request.form['rank']
        afpos_mos = request.form['afpos_mos']

        cursor = db.cursor()
        cursor.execute("INSERT INTO proctor_registration (name, afpsn, password, rank, afpos_mos) VALUES (%s, %s, %s, %s, %s)", (name, afpsn, password, rank, afpos_mos))
        db.commit()
        cursor.close()
        
        return redirect(url_for('proctor_login'))
    return render_template('proctor_registration.html')

@app.route('/search_serial', methods=['GET'])
def search_serial():
    afpsn = request.args.get('afpsn')

    # Check if serial number exists
    cursor = db.cursor()
    cursor.execute("SELECT first_name FROM users_account WHERE afpsn = %s", (afpsn,)) #Adjust the output
    first_name = cursor.fetchone()

    if first_name:
        print(f"Serial number {afpsn} found. first_name: {first_name[0]}")
        return first_name[0]  # Return the first_name if found
    else:
        print(f"Serial number {afpsn} not found.")
        return ""  # Return empty string if not found

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

        if not (raw_pushup and raw_situp and act_date):
            return "Push-up count, sit-up count, or act_date is missing."

        try:
            act_date = datetime.strptime(act_date, '%Y-%m-%d').date()
        except ValueError:
            # Handle parsing error
            return "Error: Invalid date format"

        # Process push-up data
        cursor.execute("SELECT * FROM pft_pushup WHERE afpsn = %s AND act_date = %s", (afpsn, act_date))
        existing_raw_pushup = cursor.fetchone()

        if existing_raw_pushup:
            print("Pushup data already submitted for this act_date.")
        else:
            # Insert new pushup data
            cursor.execute("INSERT INTO pft_pushup (afpsn,act_date,raw_pushup) VALUES (%s, %s,%s)",
                           (afpsn, act_date, raw_pushup))

        # Process sit-up data
        cursor.execute("SELECT * FROM pft_situp WHERE afpsn = %s AND act_date = %s", (afpsn, act_date))
        existing_raw_situp = cursor.fetchone()

        if existing_raw_situp:
            print("Situp data already submitted for this act_date.")
        else:
            # Insert new situp data
            cursor.execute("INSERT INTO pft_situp (afpsn,act_date,raw_situp) VALUES (%s, %s,%s)",
                           (afpsn, act_date, raw_situp))

        db.commit()

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

# Route for Admin Login Page
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor = db.cursor()
        cursor.execute("SELECT * FROM admin_credentials WHERE username = %s AND password = %s", (username, password))
        admin = cursor.fetchone()
        cursor.close()
        
        if admin:
            # Store admin information in session
            session['admin'] = admin
            # Redirect to admin_access.html
            return redirect(url_for('admin_access'))
        else:
            # Redirect to admin_login.html with error message
            return render_template('admin_login.html', error="Invalid username or password. Please try again.")
    return render_template('admin_login.html')

# Route for Admin access page
@app.route('/admin_access')
def admin_access():
    return render_template('admin_access.html')

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

# Route for Run Page
@app.route('/pft_kmrun')
def pft_kmrun():
    return render_template('pft_kmrun.html')

# Route for Pushup Page
@app.route('/pft_pushup')
def pft_pushup():
    return render_template('pft_pushup.html')

# Route for Situp Page
@app.route('/pft_situp')
def pft_situp():
    return render_template('pft_situp.html')


@app.route('/record_pushup', methods=['POST'])
def record_pushup():
    if request.method == 'POST':
        pushup_reps = request.form['pushup_reps']
        
        cursor = db.cursor()
        cursor.execute("INSERT INTO pft_pushup_results (reps) VALUES (%s)", (pushup_reps,))
        db.commit()
        cursor.close()
        
        return redirect(url_for('proctor_access'))

@app.route('/record_situp', methods=['POST'])
def record_situp():
    if request.method == 'POST':
        situp_reps = request.form['situp_reps']
        
        cursor = db.cursor()
        cursor.execute("INSERT INTO pft_situp_results (reps) VALUES (%s)", (situp_reps,))
        db.commit()
        cursor.close()
        
        return redirect(url_for('proctor_access'))

@app.route('/record_kmrun', methods=['POST'])
def record_kmrun():
    if request.method == 'POST':
        km_run = request.form['km_run']
        
        cursor = db.cursor()
        cursor.execute("INSERT INTO pft_kmrun_results (distance) VALUES (%s)", (km_run,))
        db.commit()
        cursor.close()
        
        return redirect(url_for('proctor_access'))


if __name__ == '__main__':
    app.run(debug=True)