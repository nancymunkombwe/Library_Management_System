import os, sqlite3, csv, io
from datetime import date, timedelta
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, g
app = Flask(__name__)
app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY', 'local-development-only'), DATABASE=os.environ.get('DATABASE', str(Path(__file__).with_name('library.db'))))
def db():
    if 'db' not in g:
        g.db=sqlite3.connect(app.config['DATABASE']); g.db.row_factory=sqlite3.Row; g.db.execute('PRAGMA foreign_keys=ON')
    return g.db
@app.teardown_appcontext
def close(_):
    if 'db' in g: g.db.close()
def init():
    db().executescript('''CREATE TABLE IF NOT EXISTS books(id INTEGER PRIMARY KEY, title TEXT NOT NULL, author TEXT NOT NULL, category TEXT NOT NULL, isbn TEXT, copies INTEGER NOT NULL CHECK(copies>0)); CREATE TABLE IF NOT EXISTS members(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT NOT NULL UNIQUE); CREATE TABLE IF NOT EXISTS loans(id INTEGER PRIMARY KEY, book_id INTEGER NOT NULL REFERENCES books(id), member_id INTEGER NOT NULL REFERENCES members(id), issued TEXT NOT NULL, due TEXT NOT NULL, returned TEXT);''')
    db().commit()
@app.before_request
def setup(): init()
BOOKS='''SELECT b.*, b.copies-(SELECT COUNT(*) FROM loans l WHERE l.book_id=b.id AND l.returned IS NULL) available FROM books b'''
LOANS='''SELECT l.*, b.title, m.name FROM loans l JOIN books b ON b.id=l.book_id JOIN members m ON m.id=l.member_id'''
@app.get('/')
def dashboard():
    c=db(); today=date.today().isoformat(); stats=[('Book titles',c.execute('SELECT COUNT(*) FROM books').fetchone()[0]),('Members',c.execute('SELECT COUNT(*) FROM members').fetchone()[0]),('Active loans',c.execute('SELECT COUNT(*) FROM loans WHERE returned IS NULL').fetchone()[0]),('Overdue',c.execute('SELECT COUNT(*) FROM loans WHERE returned IS NULL AND due < ?', (today,)).fetchone()[0])]; return render_template('index.html',page='Dashboard',stats=stats,loans=c.execute(LOANS+' ORDER BY l.id DESC LIMIT 6').fetchall(),today=today, categories=c.execute('SELECT category, SUM(copies) total FROM books GROUP BY category ORDER BY total DESC LIMIT 7').fetchall(), inventory=c.execute('SELECT COALESCE(SUM(copies),0) FROM books').fetchone()[0], activity=[(d.strftime('%a'),c.execute('SELECT COUNT(*) FROM loans WHERE issued=?',(d.isoformat(),)).fetchone()[0]) for d in [date.today()-timedelta(days=i) for i in range(6,-1,-1)]])
@app.route('/books',methods=['GET','POST'])
def books():
    c=db()
    if request.method=='POST':
        try:
            title,author,category=[request.form[k].strip() for k in ('title','author','category')]; copies=int(request.form['copies']); assert title and author and category and copies>0
            c.execute('INSERT INTO books(title,author,category,isbn,copies) VALUES(?,?,?,?,?)',(title,author,category,request.form.get('isbn','').strip(),copies)); c.commit(); flash('Book added.')
        except (ValueError,AssertionError,sqlite3.IntegrityError): flash('Enter valid book details and a positive copy count.','error')
        return redirect(url_for('books'))
    q=request.args.get('q',''); term='%'+q+'%'; rows=c.execute(BOOKS+' WHERE b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ? ORDER BY b.title',(term,term,term)).fetchall(); return render_template('books.html',page='Books',books=rows,q=q)
@app.post('/books/bulk')
def bulk_books():
    c=db()
    try:
        raw=request.form.get('csv','').strip()
        if raw:
            if len(raw)>250000: raise ValueError('Import is too large.')
            reader=csv.reader(io.StringIO(raw), strict=True)
            rows=[r for r in reader if any(v.strip() for v in r)]
            if rows and [v.strip().lower() for v in rows[0]]==['title','author','category','isbn','copies']: rows.pop(0)
        else:
            cols=[request.form.getlist(k) for k in ('title','author','category','isbn','copies')]
            if len(set(map(len,cols)))!=1: raise ValueError('Incomplete rows.')
            rows=list(zip(*cols))
        if not 1<=len(rows)<=500: raise ValueError('Enter between 1 and 500 books.')
        records=[]
        for i,row in enumerate(rows,1):
            if len(row)!=5: raise ValueError(f'Row {i}: expected five columns.')
            title,author,category,isbn,copies=[v.strip() for v in row]
            try: copies=int(copies)
            except ValueError: raise ValueError(f'Row {i}: copies must be a whole number.')
            if not all((title,author,category)) or not 1<=copies<=1000000: raise ValueError(f'Row {i}: complete title, author and category; copies must be positive (up to 1,000,000).')
            records.append((title,author,category,isbn,copies))
        c.executemany('INSERT INTO books(title,author,category,isbn,copies) VALUES(?,?,?,?,?)',records); c.commit(); flash(f'{len(records)} book entries added successfully.')
    except (ValueError,csv.Error,sqlite3.Error) as e:
        c.rollback(); flash(f'Nothing imported. {e}','error')
    return redirect(url_for('books'))
@app.post('/books/<int:id>/delete')
def delete_book(id):
    try: db().execute('DELETE FROM books WHERE id=?',(id,)); db().commit(); flash('Book removed.')
    except sqlite3.IntegrityError: flash('Books with loan history cannot be removed.','error')
    return redirect(url_for('books'))
@app.route('/books/<int:id>/edit',methods=['GET','POST'])
def edit_book(id):
    c=db(); book=c.execute(BOOKS+' WHERE b.id=?',(id,)).fetchone()
    if not book: return redirect(url_for('books'))
    if request.method=='POST':
        try:
            vals=[request.form[k].strip() for k in ('title','author','category')]; copies=int(request.form['copies']); assert all(vals) and copies>0 and copies>=book['copies']-book['available']; c.execute('UPDATE books SET title=?,author=?,category=?,isbn=?,copies=? WHERE id=?',(*vals,request.form.get('isbn','').strip(),copies,id)); c.commit(); flash('Book updated.'); return redirect(url_for('books'))
        except (ValueError,AssertionError): flash('Invalid details or fewer copies than active loans.','error')
    return render_template('edit.html',page='Edit book',book=book)
@app.route('/members',methods=['GET','POST'])
def members():
    c=db()
    if request.method=='POST':
        try:
            name=request.form['name'].strip(); email=request.form['email'].strip().lower(); assert name and '@' in email; c.execute('INSERT INTO members(name,email) VALUES(?,?)',(name,email)); c.commit(); flash('Member registered.')
        except (AssertionError,sqlite3.IntegrityError): flash('Invalid or duplicate member details.','error')
        return redirect(url_for('members'))
    return render_template('members.html',page='Members',members=c.execute('SELECT m.*, (SELECT COUNT(*) FROM loans WHERE member_id=m.id AND returned IS NULL) active FROM members m ORDER BY name').fetchall())
@app.post('/members/<int:id>/delete')
def delete_member(id):
    try: db().execute('DELETE FROM members WHERE id=?',(id,)); db().commit(); flash('Member removed.')
    except sqlite3.IntegrityError: flash('Members with loan history cannot be removed.','error')
    return redirect(url_for('members'))
@app.route('/loans',methods=['GET','POST'])
def loans():
    c=db(); today=date.today().isoformat()
    if request.method=='POST':
        try:
            c.execute('BEGIN IMMEDIATE'); book=c.execute(BOOKS+' WHERE b.id=?',(request.form['book_id'],)).fetchone(); due=date.fromisoformat(request.form['due']).isoformat(); assert book and book['available']>0 and due>=today; c.execute('INSERT INTO loans(book_id,member_id,issued,due) VALUES(?,?,?,?)',(book['id'],request.form['member_id'],today,due)); c.commit(); flash('Book issued.')
        except (AssertionError,ValueError,sqlite3.IntegrityError): c.rollback(); flash('Book unavailable, invalid member or invalid due date.','error')
        return redirect(url_for('loans'))
    return render_template('loans.html',page='Loans',loans=c.execute(LOANS+' ORDER BY l.id DESC').fetchall(),books=[b for b in c.execute(BOOKS).fetchall() if b['available']>0],members=c.execute('SELECT * FROM members ORDER BY name').fetchall(),today=today,due=(date.today()+timedelta(days=14)).isoformat())
@app.post('/loans/<int:id>/return')
def return_book(id):
    db().execute('UPDATE loans SET returned=? WHERE id=? AND returned IS NULL',(date.today().isoformat(),id)); db().commit(); flash('Return recorded.'); return redirect(url_for('loans'))
if __name__=='__main__': app.run(debug=False)
