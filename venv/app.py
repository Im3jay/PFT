from flask import Flask, render_template, redirect, url_for, request, jsonify, session
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
        age = request.form['age']
        cursor = db.cursor()
        cursor.execute("INSERT INTO users (rank, first_name, middle_name, surname, afpsn, afpos_mos, gender, age) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", (rank, first_name, middle_name, surname, afpsn, afpos_mos, gender, age))
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
        cursor.execute("SELECT * FROM proctor WHERE afpsn = %s AND password = %s", (afpsn, password))
        proctor = cursor.fetchone()
        cursor.close()
        
        if proctor:
            # Store proctor information in session
            session['proctor'] = proctor
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
        
        cursor = db.cursor()
        cursor.execute("INSERT INTO proctor (name, afpsn, password) VALUES (%s, %s, %s)", (name, afpsn, password))
        db.commit()
        cursor.close()
        
        return redirect(url_for('proctor_login'))
    return render_template('proctor_registration.html')

# Route for Proctor Access Page
@app.route('/proctor_access')
def proctor_access():
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
    cursor.execute("SELECT * FROM users")
    user_data = cursor.fetchall()
    # Fetch data from proctor_credentials table
    cursor.execute("SELECT * FROM proctor_credentials")
    proctor_data = cursor.fetchall()
    cursor.close()
    return jsonify({"users": user_data, "proctors": proctor_data})


if __name__ == '__main__':
    app.run(debug=True)