from flask import Flask, render_template, request, redirect, session
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "hireconnect_secret_key")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db_connection():
    return pymysql.connect(**db_config, cursorclass=pymysql.cursors.DictCursor)

db_config = {
    'host': os.getenv("MYSQLHOST"),
    'user': os.getenv("MYSQLUSER"),
    'password': os.getenv("MYSQLPASSWORD"),
    'database': os.getenv("MYSQLDATABASE"),
    'port': int(os.getenv("MYSQLPORT", 3306))
}



@app.route('/')
def home():
    query = request.args.get('q', '')
    location = request.args.get('location', '')

    conn = get_db_connection()
    cursor = conn.cursor()

    sql = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if query:
        sql += " AND (title LIKE %s OR company_name LIKE %s)"
        params.extend([f"%{query}%", f"%{query}%"])

    if location:
        sql += " AND location LIKE %s"
        params.append(f"%{location}%")

    cursor.execute(sql, params)
    jobs = cursor.fetchall()
    conn.close()
    return render_template('home.html', jobs=jobs)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO idusers (name, email, password, role) VALUES (%s, %s, %s, %s)",
            (name, email, hashed_password, role)
        )
        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM idusers WHERE email=%s", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['role'] = user['role']
            return redirect('/')
        else:
            return "Invalid email or password"

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/apply/<int:job_id>')
def apply(job_id):
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM applications WHERE user_id=%s AND job_id=%s",
        (session['user_id'], job_id)
    )
    existing = cursor.fetchone()

    if existing:
        conn.close()
        return render_template('message.html', message="You already applied for this job.", link_text="Back to Jobs", link_url="/")

    cursor.execute(
        "INSERT INTO applications (user_id, job_id, status) VALUES (%s, %s, %s)",
        (session['user_id'], job_id, 'pending')
    )
    conn.commit()
    conn.close()
    return render_template('message.html', message="Application submitted successfully!", link_text="Back to Jobs", link_url="/")


@app.route('/my-applications')
def my_applications():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT applications.id, applications.status, applications.applied_at,
               jobs.title, jobs.company_name, jobs.location
        FROM applications
        JOIN jobs ON applications.job_id = jobs.id
        WHERE applications.user_id = %s
    """, (session['user_id'],))
    applications = cursor.fetchall()
    conn.close()
    return render_template('my_applications.html', applications=applications)


@app.route('/post-job', methods=['GET', 'POST'])
def post_job():
    if session.get('role') != 'recruiter':
        return "Only recruiters can post jobs."

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        company_name = request.form['company_name']
        location = request.form['location']
        salary_range = request.form['salary_range']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO jobs (recruiter_id, title, description, company_name, location, salary_range) VALUES (%s, %s, %s, %s, %s, %s)",
            (session['user_id'], title, description, company_name, location, salary_range)
        )
        conn.commit()
        conn.close()
        return redirect('/my-jobs')

    return render_template('post_job.html')


@app.route('/my-jobs')
def my_jobs():
    if session.get('role') != 'recruiter':
        return "Only recruiters can view this page."

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT jobs.*, 
               (SELECT COUNT(*) FROM applications WHERE applications.job_id = jobs.id) AS applicant_count
        FROM jobs WHERE recruiter_id = %s
    """, (session['user_id'],))
    jobs = cursor.fetchall()
    conn.close()
    return render_template('my_jobs.html', jobs=jobs)


@app.route('/job/<int:job_id>/applicants')
def job_applicants(job_id):
    if session.get('role') != 'recruiter':
        return "Only recruiters can view this page."

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id=%s AND recruiter_id=%s", (job_id, session['user_id']))
    job = cursor.fetchone()
    if not job:
        conn.close()
        return "Job not found or not yours."

    cursor.execute("""
    SELECT applications.id, applications.status, applications.applied_at,
           idusers.name, idusers.email, idusers.skills, idusers.education, idusers.experience, idusers.resume_path
    FROM applications
    JOIN idusers ON applications.user_id = idusers.id
    WHERE applications.job_id = %s
""", (job_id,))
    applicants = cursor.fetchall()
    conn.close()
    return render_template('applicants.html', job=job, applicants=applicants)

@app.route('/edit-job/<int:job_id>', methods=['GET', 'POST'])
def edit_job(job_id):
    if session.get('role') != 'recruiter':
        return "Only recruiters can edit jobs."

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs WHERE id=%s AND recruiter_id=%s", (job_id, session['user_id']))
    job = cursor.fetchone()

    if not job:
        conn.close()
        return "Job not found or not yours."

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        company_name = request.form['company_name']
        location = request.form['location']
        salary_range = request.form['salary_range']

        cursor.execute("""
            UPDATE jobs SET title=%s, description=%s, company_name=%s, location=%s, salary_range=%s
            WHERE id=%s AND recruiter_id=%s
        """, (title, description, company_name, location, salary_range, job_id, session['user_id']))
        conn.commit()
        conn.close()
        return redirect('/my-jobs')

    conn.close()
    return render_template('edit_job.html', job=job)


@app.route('/delete-job/<int:job_id>')
def delete_job(job_id):
    if session.get('role') != 'recruiter':
        return "Only recruiters can delete jobs."

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM jobs WHERE id=%s AND recruiter_id=%s", (job_id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect('/my-jobs')


@app.route('/update-status/<int:application_id>', methods=['POST'])
def update_status(application_id):
    if session.get('role') != 'recruiter':
        return "Only recruiters can update status."

    new_status = request.form['status']

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE applications SET status=%s WHERE id=%s", (new_status, application_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer or '/my-jobs')


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        skills = request.form['skills']
        education = request.form['education']
        experience = request.form['experience']

        resume_file = request.files.get('resume')
        if resume_file and resume_file.filename != '':
            filename = secure_filename(f"user{session['user_id']}_{resume_file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume_file.save(filepath)

            cursor.execute("""
                UPDATE idusers SET skills=%s, education=%s, experience=%s, resume_path=%s WHERE id=%s
            """, (skills, education, experience, filename, session['user_id']))
        else:
            cursor.execute("""
                UPDATE idusers SET skills=%s, education=%s, experience=%s WHERE id=%s
            """, (skills, education, experience, session['user_id']))

        conn.commit()

    cursor.execute("SELECT * FROM idusers WHERE id=%s", (session['user_id'],))
    user = cursor.fetchone()
    conn.close()
    return render_template('profile.html', user=user)


if __name__ == '__main__':
    app.run(debug=True)