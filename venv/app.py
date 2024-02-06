from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key' 

# Connect to MySQL database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",  
    database="registration_test"
)

# Route for registration page
@app.route('/')
def registration_form():
    return render_template('register.html')

# Route for lobby page
@app.route('/lobby_page')
def login_page():
    return render_template('lobby.html')

# Route for form submission (registration)
@app.route('/register', methods=['POST'])
def register():
    try:
        cursor = db.cursor()
        # Form
        username = request.form['username'].lower()
        password = request.form['password']
        rank = request.form['rank']
        first_name = request.form['first_name']
        middle_name = request.form['middle_name']
        surname = request.form['surname']
        afpsn = request.form['afpsn']
        afpos_mos = request.form['afpos_mos']
        gender = request.form['gender']
        age = request.form['age']
        # Insert into database
        cursor.execute("INSERT INTO user_credentials (username, password) VALUES (%s, %s)", (username, password))
        cursor.execute("INSERT INTO users (username, rank, first_name, middle_name, surname, afpsn, afpos_mos, gender, age) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", (username, rank, first_name, middle_name, surname, afpsn, afpos_mos, gender, age))
        db.commit()
        cursor.close()
        
        return redirect(url_for('login_page'))
    except Exception as e:
        return "An error occurred during registration: " + str(e)

# Route for login page
@app.route('/login_page')
def login_page():
    return render_template('loginpage.html')

# Route for form submission (login)
@app.route('/login', methods=['POST'])
def login():
    try:
        username = request.form['username'].lower()  
        password = request.form['password']
       
        cursor = db.cursor()
        cursor.execute("SELECT * FROM user_credentials WHERE (username = %s OR afpsn = %s) AND BINARY password = %s", (username, username, password))
        user = cursor.fetchone()
        cursor.close()
        if user:
            
            session['username'] = username
        
            return redirect(url_for('homepage'))
        else:
           
            return redirect(url_for('login_page'))
    except Exception as e:
        return "An error occurred during login: " + str(e)

# Route for homepage
@app.route('/homepage')
def homepage():
    if 'username' in session:
        return render_template('homepage.html')
    else:
        return redirect(url_for('login_page')) 

if __name__ == '__main__':
    app.run(debug=True)