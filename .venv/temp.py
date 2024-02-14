from flask import Flask, render_template, request, jsonify
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

@app.route('/suggest_usernames')
def suggest_usernames():
    afpsn = request.args.get('afpsn')

    cursor = db.cursor()
    cursor.execute("SELECT first_name FROM users_account WHERE afpsn LIKE %s", (afpsn + '%',))
    usernames = cursor.fetchall()

    suggestions = ''.join(f"<div onclick='fillSerialNumber(\"{first_name[0]}\")'>{first_name[0]}</div>" for first_name in usernames)
    return suggestions

@app.route('/get_serial_number')
def get_serial_number():
    first_name = request.args.get('first_name')

    cursor = db.cursor()
    cursor.execute("SELECT afpsn FROM users_account WHERE first_name = %s", (first_name,))
    afpsn = cursor.fetchone()

    if afpsn:
        return jsonify(afpsn[0])
    else:
        return jsonify(None)

@app.route('/search_serial', methods=['GET'])
def search_serial():
    afpsn = request.args.get('afpsn')

    # Check if serial number exists
    cursor = db.cursor()
    cursor.execute("SELECT first_name FROM users_account WHERE afpsn = %s", (afpsn,))
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
        #participant_number = request.form.get('participant_number')

        if not (raw_pushup and raw_situp and act_date ): #and participant_number
            return "Push-up count, sit-up count, date, or participant number is missing."

        try:
            act_date = datetime.strptime(act_date, '%Y-%m-%d').date()
        except ValueError:
            # Handle parsing error
            return "Error: Invalid date format"

        # Process push-up data
        cursor.execute("SELECT * FROM pushup_table_1 WHERE afpsn = %s AND date = %s", (afpsn, act_date))
        existing_pushup_data = cursor.fetchone()

        if existing_pushup_data:
            print("Pushup data already submitted for this date.")
        else:
            # Insert new pushup data
            cursor.execute("INSERT INTO pushup_table_1 (afpsn, name, participant_number, act_date, raw_pushup) VALUES (%s, %s, %s, %s)",
                           (afpsn, first_name[0], act_date, raw_pushup)) #afpsn, first_name[0], participant_number, date, raw_pushup

        # Process sit-up data
        cursor.execute("SELECT * FROM situp_table_1 WHERE afpsn = %s AND act_date = %s", (afpsn, act_date))
        existing_situp_data = cursor.fetchone()

        if existing_situp_data:
            print("Situp data already submitted for this date.")
        else:
            # Insert new situp data
            cursor.execute("INSERT INTO situp_table_1 (afpsn, name, participant_number, act_date, raw_situp) VALUES (%s, %s, %s, %s)",
                           (afpsn, first_name[0], act_date, raw_situp)) #afpsn, first_name[0], participant_number, date, raw_situp

        db.commit()

        return "Data submitted successfully."

    return render_template('proctor_access.html')


if __name__ == '__main__':
    app.run(debug=True)