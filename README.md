# HireConnect

A full-stack job portal web application built with Flask and MySQL, connecting job seekers with recruiters.

## Features

### Authentication
- User registration with role selection (Job Seeker / Recruiter)
- Secure login with password hashing (Werkzeug)
- Session-based authentication

### Job Seeker Features
- Browse and search jobs by title, company, or location
- Apply to jobs with duplicate-application prevention
- Track application status (Pending / Shortlisted / Rejected)
- Build profile with skills, education, experience
- Upload resume (PDF)

### Recruiter Features
- Post new job listings
- Edit and delete posted jobs
- View applicants per job with full profile details (skills, education, resume)
- Update applicant status

## Tech Stack
- **Backend:** Python, Flask
- **Database:** MySQL (pymysql)
- **Frontend:** HTML, CSS, Jinja2 templating
- **Auth:** Werkzeug password hashing

## Database Schema
- `idusers` — user accounts (id, name, email, password, role, skills, education, experience, resume_path)
- `jobs` — job postings (id, recruiter_id, title, description, company_name, location, salary_range)
- `applications` — job applications (id, user_id, job_id, status, applied_at)

## Setup

1. Clone the repo 
