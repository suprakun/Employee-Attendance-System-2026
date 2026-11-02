# Attendly — Employee Attendance Analysis System

A polished, dark-themed employee attendance management web application built with **Python, Flask, SQLite, HTML, CSS and JavaScript**. This is a local academic project prototype for the Employee Attendance Analysis System.

## Features
- Dark responsive admin dashboard with workforce KPIs, attendance distribution, department snapshot, recent activity and low-attendance watchlist.
- Employee directory: add, search, filter and delete employee records.
- Daily attendance entry: Present, Absent or Leave; an existing employee/date entry is updated rather than duplicated.
- Attendance records with date, employee and status filters.
- Reports: employee-wise attendance percentage, department summaries, configurable low-attendance threshold and CSV export.
- SQLite database is created automatically on first run.
- Demo records are inserted only when the employee table is empty.

## Requirements
- Python 3.9 or newer
- pip

## Run on Windows
1. Extract this project folder.
2. Open Command Prompt or the VS Code terminal inside the folder.
3. Create and activate a virtual environment:
   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   ```
4. Install dependencies:
   ```bat
   python -m pip install -r requirements.txt
   ```
5. Start the website:
   ```bat
   python app.py
   ```
6. Open **http://127.0.0.1:5000** in your browser.

If PowerShell blocks activation, skip activation and run `python -m pip install -r requirements.txt` followed by `python app.py`.

## Run on macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```
Then open **http://127.0.0.1:5000**.

## Project structure
```text
Employee_Attendance_Analysis_WebApp/
├── app.py
├── requirements.txt
├── README.md
├── attendance.db          # created automatically on first run
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── employees.html
│   ├── attendance.html
│   ├── records.html
│   ├── reports.html
│   └── 404.html
└── static/
    ├── style.css
    └── app.js
```

## Attendance calculation
Attendance percentage = (Present records ÷ all recorded statuses) × 100. The report does **not** infer unrecorded dates as absences. Record Present, Absent or Leave explicitly for each employee/date that should be included in analysis.

## Important notes for the project demonstration
- The initial six employees and attendance entries are illustrative demo data, not real employee information. Replace them with your own sample/project data before presenting final results.
- The prototype runs locally and stores data in `attendance.db` in this project folder.
- This academic prototype does not include user authentication, role-based access, biometric verification, holiday calendars, payroll integration, cloud backup or production security hardening.
- For a clean demo reset, stop the server and delete `attendance.db`; the next run recreates the database and sample data.

## GitHub upload
Upload `app.py`, `requirements.txt`, `README.md`, and the `templates/` and `static/` folders. Do not upload `.venv/`, `__pycache__/`, or real employee personal data. You may omit `attendance.db` so each evaluator gets a clean database with sample data.


## Vercel deployment note

The app uses `/tmp/attendance.db` when running on Vercel so the Flask function can initialize its demo database in a writable location. This is **temporary, non-persistent storage**: data can disappear when the serverless instance is recycled and may not be shared between instances. Use a hosted PostgreSQL database and update the database layer before using this deployment for real employee attendance records.
