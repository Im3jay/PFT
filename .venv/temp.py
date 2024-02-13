from flask import Flask, render_template, request
import mysql.connector
from datetime import datetime

app = Flask(__name__)

# Connect to MySQL database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  
    database="pftdatabase"
)

# Route for lobby page
@app.route('/')
def lobby():
    return render_template('proctor_access.html')

@app.route('/search_serial', methods=['GET'])
def search_serial():
    afpsn = request.args.get('afpsn')

    # Check if serial number exists
    cursor = db.cursor()
    cursor.execute("SELECT first_name FROM users WHERE afpsn = %s", (afpsn,))
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
        cursor.execute("SELECT first_name FROM user WHERE afpsn = %s", (afpsn,))
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
        cursor.execute("SELECT * FROM pft_situp WHERE afpsn = %s AND date = %s", (afpsn, act_date))
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


if __name__ == '__main__':
    app.run(debug=True)