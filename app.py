import pymysql
from flask import Flask, request, render_template, redirect, url_for, session
from database_manager import get_db_connection, USE_MYSQL, PLACEHOLDER
import plotly_graphs
import os
from sms_gateway import send_custom_sms

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecret")

# ---------- NEW: Ensure DB + tables exist ----------
def ensure_database():
    """Create the MySQL database if it does not exist (only if USE_MYSQL)."""
    if USE_MYSQL:
        db_name = os.getenv("MYSQL_DB", "wecare")
        connection = pymysql.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            user=os.getenv("MYSQL_USER", "root"),
            password=os.getenv("MYSQL_PASSWORD", "")
        )
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}`")
        connection.close()

def create_tables():
    """Create required tables if they don't exist."""
    conn = get_db_connection()
    cur = conn.cursor()

    # hospitals table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS hospitals (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255),
        phone VARCHAR(50),
        state VARCHAR(100),
        lga VARCHAR(100),
        country VARCHAR(100)
    )
    """ if USE_MYSQL else """
    CREATE TABLE IF NOT EXISTS hospitals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        state TEXT,
        lga TEXT,
        country TEXT
    )
    """)

    # pregnant_women table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pregnant_women (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(255),
        assigned_hospital INT,
        FOREIGN KEY (assigned_hospital) REFERENCES hospitals(id)
    )
    """ if USE_MYSQL else """
    CREATE TABLE IF NOT EXISTS pregnant_women (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        assigned_hospital INTEGER,
        FOREIGN KEY (assigned_hospital) REFERENCES hospitals(id)
    )
    """)

    # risk_assessments table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS risk_assessments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        woman_id INT,
        risk_score INT,
        FOREIGN KEY (woman_id) REFERENCES pregnant_women(id)
    )
    """ if USE_MYSQL else """
    CREATE TABLE IF NOT EXISTS risk_assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        woman_id INTEGER,
        risk_score INTEGER,
        FOREIGN KEY (woman_id) REFERENCES pregnant_women(id)
    )
    """)

    # antenatal_visits table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS antenatal_visits (
        id INT AUTO_INCREMENT PRIMARY KEY,
        woman_id INT,
        visit_date DATE,
        FOREIGN KEY (woman_id) REFERENCES pregnant_women(id)
    )
    """ if USE_MYSQL else """
    CREATE TABLE IF NOT EXISTS antenatal_visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        woman_id INTEGER,
        visit_date TEXT,
        FOREIGN KEY (woman_id) REFERENCES pregnant_women(id)
    )
    """)

    # delivery_records table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS delivery_records (
        id INT AUTO_INCREMENT PRIMARY KEY,
        woman_id INT,
        delivery_date DATE,
        delivery_type VARCHAR(20),
        child_sex VARCHAR(10),
        birth_type VARCHAR(20),
        complication TEXT,
        note TEXT,
        FOREIGN KEY (woman_id) REFERENCES pregnant_women(id)
    )
    """ if USE_MYSQL else """
    CREATE TABLE IF NOT EXISTS delivery_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        woman_id INTEGER,
        delivery_date TEXT,
        delivery_type TEXT,
        child_sex TEXT,
        birth_type TEXT,
        complication TEXT,
        note TEXT,
        FOREIGN KEY (woman_id) REFERENCES pregnant_women(id)
    )
    """)

    conn.commit()
    cur.close()
    conn.close()

# Call at startup
ensure_database()
create_tables()
# ---------- END NEW ----------


# Middleware to set up database connection and session management
@app.before_request
def before_request():
    if 'hospital_id' not in session:
        session['hospital_id'] = None

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    return response

# Route to handle the main page and redirect to login if not authenticated
@app.route('/')
def index():
    if 'hospital_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

#Login and registration routes for hospital
#Register
@app.route('/hospital/register', methods=['GET', 'POST'])
def hospital_register():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        state = request.form['state']
        lga = request.form['lga']
        country = request.form['country']
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"""
            INSERT INTO hospitals (name, phone, state, lga, country)
            VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})
        """, (name, phone, state, lga, country))
        conn.commit()
        conn.close()
        
        return redirect(url_for('login'))
    return render_template('register.html')
#Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form['phone']
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute(f"SELECT * FROM hospitals WHERE phone = {PLACEHOLDER}", (phone,))
        hospital = cur.fetchone()
        cur.close()
        conn.close()

        if hospital:
            session['hospital_id'] = hospital['id']
            return redirect(url_for('dashboard'))

        return "Invalid login"
    return render_template('login.html')

# Dashboard route to display pregnant
@app.route('/dashboard')
def dashboard():
    if 'hospital_id' not in session:
        return redirect(url_for('index'))
    conn = get_db_connection()
    hospital_id = session['hospital_id']
    cur = conn.cursor()
    cur.execute(
        f"SELECT * FROM pregnant_women WHERE assigned_hospital = {PLACEHOLDER}",
        (hospital_id,)
    )
    women = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('dashboard.html', women=women)

#Custom message route to send SMS
@app.route('/custom_message', methods=['GET', 'POST'])
def custom_message_form():
    if request.method == 'POST':
        message = request.form['message']
        phone = request.form['phone']
        send_custom_sms(phone, message)
        return redirect(url_for('dashboard'))
    return render_template('custom_message.html')

# Risk assessment and antenatal visit routes
@app.route('/risk_assessment', methods=['GET', 'POST'])
def risk_assessment():
    if request.method == 'POST':
        # Process the form data
        data = request.form
        # Save the data to the database or perform any necessary actions
        return redirect(url_for('dashboard'))
    return render_template('risk_assessment.html')

#plotly graphs route to display risk and antenatal visit data
@app.route('/plotly_graphs')
def plotly_graphs():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM risk_assessments")
    risk_data = cur.fetchall()

    cur.execute("SELECT * FROM antenatal_visits")
    attended = cur.fetchall()

    cur.close()
    conn.close()

    risk_fig = plotly_graphs.plot_monthly_risks(risk_data)
    visits_fig = plotly_graphs.plot_weekly_antenatal_visits(attended)

    return render_template('plotly_graphs.html', risk_fig=risk_fig, visits_fig=visits_fig)


# Delivery records route to add record to sql
@app.route('/delivery_report', methods=['GET', 'POST'])
def delivery_report():
    if request.method == 'POST':
        # Process the form data
        data = request.form
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"""
            INSERT INTO delivery_records 
            (woman_id, delivery_date, delivery_type, child_sex, birth_type, complication, note)
            VALUES ({PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER}, {PLACEHOLDER})
        """, (
            data['woman_id'],
            data['delivery_date'],
            data['delivery_type'],
            data['child_sex'],
            data['birth_type'],
            data['complication'],
            data['note']
        ))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('dashboard'))
    return render_template('delivery_records.html')


#Logout route to clear session
@app.route('/logout')
def logout():
    session.pop('hospital_id', None)
    return redirect(url_for('index'))

# Error handling for 404 and 500
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404
@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

#Main execution block
if __name__ == '__main__':
    try:
        print("Starting Flask app...")
        app.run(debug=True)
    except Exception as e:
        print("Error:", e)