from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import MySQLdb
from urllib.parse import unquote
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Database connection function
def get_db_connection():
    try:
        conn = MySQLdb.connect(
            host="localhost",
            user="root",
            password="tobe*04",
            database="aeas"
        )
        return conn
    except MySQLdb.Error as e:
        flash(f"Database connection error: {str(e)}")
        return None

# Home page
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form.get('role')

        if not email or not password or not role:
            flash('All fields are required!')
            return redirect(url_for('register'))

        conn = get_db_connection()
        if not conn:
            flash('Could not connect to the database.')
            return redirect(url_for('register'))

        cursor = conn.cursor()

        try:
            if role == 'Student':
                cursor.execute('INSERT INTO students (email, password) VALUES (%s, %s)', (email, password))
                session['loggedin'] = True
                session['role'] = 'Student'
                session['email'] = email
                flash('Student registered successfully!')
                return redirect(url_for('student_details_form'))

            elif role == 'Teacher':
                cursor.execute('INSERT INTO teachers (email, password) VALUES (%s, %s)', (email, password))
                session['loggedin'] = True
                session['role'] = 'Teacher'
                session['email'] = email
                flash('Teacher registered successfully!')
                return redirect(url_for('index'))

            conn.commit()

        except MySQLdb.Error as e:
            flash(f"An error occurred: {str(e)}")
            conn.rollback()

        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

@app.route('/student_details_form', methods=['GET', 'POST'])
def student_details_form():
    if 'loggedin' in session and session['role'] == 'Student':
        if request.method == 'POST':
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            class_name = request.form['class_name']
            section = request.form['section']
            phone_number = request.form['phone_number']
            email = session.get('email')

            conn = get_db_connection()
            if not conn:
                flash('Could not connect to the database.')
                return redirect(url_for('student_details_form'))

            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO student_details (first_name, last_name, class_name, section, phone_number, email) VALUES (%s, %s, %s, %s, %s, %s)',
                (first_name, last_name, class_name, section, phone_number, email)
            )
            conn.commit()
            cursor.close()
            conn.close()

            flash('Student details saved successfully!')
            return redirect(url_for('index'))

        return render_template('student_details_form.html')
    else:
        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        conn = get_db_connection()
        if not conn:
            return redirect(url_for('login'))

        cursor = conn.cursor()

        if role == 'Student':
            cursor.execute('SELECT * FROM students WHERE email = %s AND password = %s', (email, password))
            user = cursor.fetchone()
            if user:
                session['loggedin'] = True
                session['role'] = 'Student'
                session['email'] = email
                return redirect(url_for('student_dashboard'))

        elif role == 'Teacher':
            cursor.execute('SELECT * FROM teachers WHERE email = %s AND password = %s', (email, password))
            user = cursor.fetchone()
            if user:
                session['loggedin'] = True
                session['role'] = 'Teacher'
                session['email'] = email
                return redirect(url_for('teacher_dashboard'))

        cursor.close()
        conn.close()

        flash('Invalid credentials!')
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/teacher_dashboard')
def teacher_dashboard():
    if 'loggedin' in session and session['role'] == 'Teacher':
        return render_template('teacher_dashboard.html')
    return redirect(url_for('index'))

@app.route('/track_students', methods=['GET', 'POST'])
def track_students():
    if 'loggedin' in session and session['role'] == 'Teacher':
        if request.method == 'POST':
            class_name = request.form['class_name']
            section = request.form['section']

            conn = get_db_connection()
            if not conn:
                return redirect(url_for('track_students'))

            cursor = conn.cursor()
            cursor.execute('SELECT first_name, last_name, email, phone_number FROM student_details WHERE class_name = %s AND section = %s', (class_name, section))
            students = cursor.fetchall()
            cursor.close()
            conn.close()

            return render_template('display_students.html', students=students, class_name=class_name, section=section)

        return render_template('track_students.html')

    return redirect(url_for('index'))

@app.route('/student_dashboard')
def student_dashboard():
    if 'loggedin' in session and session['role'] == 'Student':
        conn = get_db_connection()
        if not conn:
            return redirect(url_for('student_dashboard'))

        cursor = conn.cursor()
        cursor.execute('SELECT * FROM student_details WHERE email = %s', (session['email'],))
        student = cursor.fetchone()

        if student:
            cursor.execute('SELECT * FROM assessments WHERE class_name = %s AND section = %s', (student[3], student[4]))
            assessments = cursor.fetchall()

            student_details = {
                'first_name': student[1],
                'last_name': student[2],
                'class_name': student[3],
                'section': student[4],
                'email': student[5],
                'phone_number': student[6],
                'assessments': assessments
            }
            cursor.close()
            conn.close()

            return render_template('student_dashboard.html', student_details=student_details)
    return redirect(url_for('index'))

@app.route('/upload_answer_sheet', methods=['POST'])
def upload_answer_sheet():
    if 'loggedin' in session and session['role'] == 'Student':
        subject = request.form['subject']
        file = request.files['file']

        if file and file.filename.endswith('.pdf'):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)

            flash('Answer sheet uploaded successfully!')
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid file format. Please upload a PDF.')
            return redirect(url_for('student_dashboard'))
    return redirect(url_for('index'))

@app.route('/upload_assessment', methods=['GET', 'POST'])
def upload_assessment():
    if 'loggedin' in session and session['role'] == 'Teacher':
        if request.method == 'POST':
            class_name = request.form['class_name']
            section = request.form['section']
            file = request.files['file']

            if file and file.filename.endswith('.pdf'):
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(file_path)

                conn = get_db_connection()
                if not conn:
                    flash('Could not connect to the database.')
                    return redirect(url_for('upload_assessment'))

                cursor = conn.cursor()
                try:
                    cursor.execute(
                        'INSERT INTO assessments (class_name, section, file_name, upload_date) VALUES (%s, %s, %s, NOW())',
                        (class_name, section, file.filename)
                    )
                    conn.commit()
                    flash('Assessment uploaded successfully!')
                except MySQLdb.Error as e:
                    flash(f'An error occurred: {str(e)}')
                    conn.rollback()
                finally:
                    cursor.close()
                    conn.close()

                return redirect(url_for('teacher_dashboard'))
            else:
                flash('Invalid file format. Please upload a PDF.')
                return redirect(url_for('upload_assessment'))

        return render_template('upload_assessment.html')

    return redirect(url_for('index'))

@app.route('/check_report_card')
def check_report_card():
    if 'loggedin' in session and session['role'] == 'Student':
        return render_template('report_card.html')
    return redirect(url_for('index'))

@app.route('/download/<path:filename>')
def download_file(filename):
    filename = unquote(filename)  # Decode the filename
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if os.path.exists(file_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    else:
        flash('The requested file was not found.')
        return redirect(url_for('student_dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
