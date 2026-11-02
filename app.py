from flask import Flask, render_template, request, redirect, url_for, flash, Response
import sqlite3, csv, io, os
from datetime import date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Vercel's application bundle is read-only. Use its temporary writable directory
# for a demo database; use the project folder for local development.
DB_PATH = os.environ.get(
    'DB_PATH',
    '/tmp/attendance.db' if os.environ.get('VERCEL') else os.path.join(BASE_DIR, 'attendance.db')
)
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key-for-production')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    with get_db() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            email TEXT DEFAULT '',
            designation TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present','Absent','Leave')),
            notes TEXT DEFAULT '',
            UNIQUE(employee_id, attendance_date),
            FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
        );
        ''')
        count = db.execute('SELECT COUNT(*) FROM employees').fetchone()[0]
        if count == 0:
            people = [
                ('EMP001','Aarav Sharma','Engineering','aarav@example.com','Software Engineer'),
                ('EMP002','Diya Reddy','Human Resources','diya@example.com','HR Executive'),
                ('EMP003','Ishaan Kumar','Design','ishaan@example.com','UI Designer'),
                ('EMP004','Meera Nair','Engineering','meera@example.com','QA Engineer'),
                ('EMP005','Kabir Singh','Finance','kabir@example.com','Accountant'),
                ('EMP006','Ananya Rao','Operations','ananya@example.com','Operations Associate'),
            ]
            db.executemany('INSERT INTO employees(employee_code,name,department,email,designation) VALUES(?,?,?,?,?)', people)
            today = date.today()
            rows = []
            for offset in range(29, -1, -1):
                day = today - timedelta(days=offset)
                if day.weekday() >= 5:
                    continue
                for emp_id in range(1, 7):
                    # Deterministic illustrative sample data, not real employee records.
                    status = 'Absent' if (day.day + emp_id * 3) % 17 == 0 else ('Leave' if (day.day + emp_id) % 23 == 0 else 'Present')
                    rows.append((emp_id, day.isoformat(), status, 'Demo record'))
            db.executemany('INSERT OR IGNORE INTO attendance(employee_id,attendance_date,status,notes) VALUES(?,?,?,?)', rows)


@app.context_processor
def inject_globals():
    return {'today': date.today().isoformat()}


def attendance_stats(start=None, end=None):
    where, params = [], []
    if start:
        where.append('a.attendance_date >= ?'); params.append(start)
    if end:
        where.append('a.attendance_date <= ?'); params.append(end)
    clause = ('WHERE ' + ' AND '.join(where)) if where else ''
    with get_db() as db:
        rows = db.execute(f'''SELECT a.status, COUNT(*) AS total FROM attendance a {clause} GROUP BY a.status''', params).fetchall()
        return {r['status']: r['total'] for r in rows}


@app.route('/')
def dashboard():
    month_start = date.today().replace(day=1).isoformat()
    end = date.today().isoformat()
    stats = attendance_stats(month_start, end)
    with get_db() as db:
        total_employees = db.execute('SELECT COUNT(*) FROM employees').fetchone()[0]
        today_rows = db.execute('''SELECT a.status, COUNT(*) total FROM attendance a WHERE a.attendance_date=? GROUP BY a.status''', (end,)).fetchall()
        today_stats = {r['status']: r['total'] for r in today_rows}
        recent = db.execute('''SELECT a.attendance_date,a.status,e.name,e.employee_code,e.department FROM attendance a JOIN employees e ON e.id=a.employee_id ORDER BY a.attendance_date DESC,a.id DESC LIMIT 7''').fetchall()
        dept_rows = db.execute('''SELECT e.department, COUNT(a.id) records,
            SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) present,
            SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) absent
            FROM employees e LEFT JOIN attendance a ON a.employee_id=e.id AND a.attendance_date BETWEEN ? AND ?
            GROUP BY e.department ORDER BY e.department''', (month_start,end)).fetchall()
        low = db.execute('''SELECT e.id,e.employee_code,e.name,e.department,
            ROUND(100.0*SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END)/COUNT(a.id),1) pct
            FROM employees e JOIN attendance a ON a.employee_id=e.id AND a.attendance_date BETWEEN ? AND ?
            GROUP BY e.id HAVING COUNT(a.id)>0 AND pct < 85 ORDER BY pct ASC LIMIT 5''',(month_start,end)).fetchall()
    total_records = sum(stats.values())
    present_pct = round(stats.get('Present',0)*100/total_records,1) if total_records else 0
    absent_pct = round(stats.get('Absent',0)*100/total_records,1) if total_records else 0
    leave_pct = max(0, round(100-present_pct-absent_pct,1)) if total_records else 0
    return render_template('dashboard.html', active='dashboard', total_employees=total_employees,
        today_stats=today_stats, stats=stats, present_pct=present_pct, absent_pct=absent_pct, leave_pct=leave_pct, recent=recent, departments=dept_rows, low=low,
        month_label=date.today().strftime('%B %Y'))


@app.route('/employees', methods=['GET','POST'])
def employees():
    if request.method == 'POST':
        code=request.form.get('employee_code','').strip().upper(); name=request.form.get('name','').strip()
        department=request.form.get('department','').strip(); email=request.form.get('email','').strip(); designation=request.form.get('designation','').strip()
        if not code or not name or not department:
            flash('Employee ID, full name and department are required.','error')
        else:
            try:
                with get_db() as db:
                    db.execute('INSERT INTO employees(employee_code,name,department,email,designation) VALUES(?,?,?,?,?)',(code,name,department,email,designation))
                flash(f'{name} was added to the employee directory.','success')
                return redirect(url_for('employees'))
            except sqlite3.IntegrityError:
                flash('That employee ID already exists. Use a unique ID.','error')
    q=request.args.get('q','').strip(); dept=request.args.get('department','').strip()
    sql='SELECT * FROM employees WHERE 1=1'; params=[]
    if q:
        sql+=' AND (name LIKE ? OR employee_code LIKE ? OR email LIKE ?)'; params += [f'%{q}%']*3
    if dept:
        sql+=' AND department=?'; params.append(dept)
    sql+=' ORDER BY name'
    with get_db() as db:
        rows=db.execute(sql,params).fetchall()
        depts=[r['department'] for r in db.execute('SELECT DISTINCT department FROM employees ORDER BY department').fetchall()]
    return render_template('employees.html',active='employees',employees=rows,departments=depts,q=q,selected_dept=dept)


@app.post('/employees/<int:employee_id>/delete')
def delete_employee(employee_id):
    with get_db() as db:
        db.execute('DELETE FROM employees WHERE id=?',(employee_id,))
    flash('Employee and associated attendance records deleted.','success')
    return redirect(url_for('employees'))


@app.route('/attendance', methods=['GET','POST'])
def attendance():
    if request.method=='POST':
        employee_id=request.form.get('employee_id'); day=request.form.get('attendance_date'); status=request.form.get('status'); notes=request.form.get('notes','').strip()
        if not employee_id or not day or status not in ('Present','Absent','Leave'):
            flash('Select an employee, date and valid attendance status.','error')
        else:
            with get_db() as db:
                db.execute('''INSERT INTO attendance(employee_id,attendance_date,status,notes) VALUES(?,?,?,?)
                    ON CONFLICT(employee_id,attendance_date) DO UPDATE SET status=excluded.status, notes=excluded.notes''',(employee_id,day,status,notes))
            flash('Attendance saved successfully.','success')
            return redirect(url_for('attendance', day=day))
    day=request.args.get('day',date.today().isoformat())
    with get_db() as db:
        people=db.execute('SELECT * FROM employees ORDER BY name').fetchall()
        marked=db.execute('''SELECT a.*,e.name,e.employee_code,e.department FROM attendance a JOIN employees e ON e.id=a.employee_id WHERE a.attendance_date=? ORDER BY e.name''',(day,)).fetchall()
    return render_template('attendance.html',active='attendance',employees=people,marked=marked,selected_day=day)


@app.route('/records')
def records():
    start=request.args.get('start',''); end=request.args.get('end',''); status=request.args.get('status',''); emp=request.args.get('employee','')
    sql='''SELECT a.*,e.name,e.employee_code,e.department FROM attendance a JOIN employees e ON e.id=a.employee_id WHERE 1=1'''; params=[]
    if start: sql+=' AND a.attendance_date>=?'; params.append(start)
    if end: sql+=' AND a.attendance_date<=?'; params.append(end)
    if status in ('Present','Absent','Leave'): sql+=' AND a.status=?'; params.append(status)
    if emp: sql+=' AND a.employee_id=?'; params.append(emp)
    sql+=' ORDER BY a.attendance_date DESC,e.name LIMIT 500'
    with get_db() as db:
        rows=db.execute(sql,params).fetchall(); people=db.execute('SELECT id,name,employee_code FROM employees ORDER BY name').fetchall()
    return render_template('records.html',active='records',records=rows,employees=people,start=start,end=end,status=status,selected_employee=emp)


@app.route('/reports')
def reports():
    start=request.args.get('start',date.today().replace(day=1).isoformat()); end=request.args.get('end',date.today().isoformat())
    threshold=int(request.args.get('threshold',85))
    with get_db() as db:
        summary=db.execute('''SELECT e.employee_code,e.name,e.department,COUNT(a.id) total,
            SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) present,
            SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) absent,
            SUM(CASE WHEN a.status='Leave' THEN 1 ELSE 0 END) leave_count
            FROM employees e LEFT JOIN attendance a ON a.employee_id=e.id AND a.attendance_date BETWEEN ? AND ?
            GROUP BY e.id ORDER BY e.name''',(start,end)).fetchall()
    report=[]
    for r in summary:
        pct=round((r['present'] or 0)*100/r['total'],1) if r['total'] else 0
        report.append({**dict(r),'pct':pct})
    dept={}
    for r in report:
        d=dept.setdefault(r['department'],{'total':0,'present':0})
        d['total']+=r['total']; d['present']+=r['present'] or 0
    for d in dept.values(): d['pct']=round(d['present']*100/d['total'],1) if d['total'] else 0
    return render_template('reports.html',active='reports',report=report,departments=dept,start=start,end=end,threshold=threshold)


@app.route('/reports/export')
def export_report():
    start=request.args.get('start',date.today().replace(day=1).isoformat()); end=request.args.get('end',date.today().isoformat())
    with get_db() as db:
        rows=db.execute('''SELECT e.employee_code,e.name,e.department,COUNT(a.id) total,
            SUM(CASE WHEN a.status='Present' THEN 1 ELSE 0 END) present,
            SUM(CASE WHEN a.status='Absent' THEN 1 ELSE 0 END) absent,
            SUM(CASE WHEN a.status='Leave' THEN 1 ELSE 0 END) leave_count
            FROM employees e LEFT JOIN attendance a ON a.employee_id=e.id AND a.attendance_date BETWEEN ? AND ? GROUP BY e.id ORDER BY e.name''',(start,end)).fetchall()
    out=io.StringIO(); writer=csv.writer(out); writer.writerow(['Employee ID','Name','Department','Recorded Days','Present','Absent','Leave','Attendance %'])
    for r in rows:
        total=r['total'] or 0; present=r['present'] or 0
        writer.writerow([r['employee_code'],r['name'],r['department'],total,present,r['absent'] or 0,r['leave_count'] or 0,round(present*100/total,1) if total else 0])
    return Response(out.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename=attendance-report-{start}-to-{end}.csv'})


@app.errorhandler(404)
def not_found(_):
    return render_template('404.html',active=''),404

init_db()
if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
