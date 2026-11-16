import tempfile, unittest
from pathlib import Path
from datetime import date,timedelta
from app import app,db
class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); app.config.update(TESTING=True,DATABASE=str(Path(self.tmp.name)/'test.db')); self.client=app.test_client()
    def tearDown(self): self.tmp.cleanup()
    def test_circulation(self):
        for route in ('/','/books','/members','/loans'): self.assertEqual(self.client.get(route).status_code,200)
        self.client.post('/books',data=dict(title='Test book',author='Author',category='Fiction',copies=1)); self.client.post('/members',data=dict(name='Reader',email='reader@example.com'))
        data=dict(book_id=1,member_id=1,due=(date.today()+timedelta(days=7)).isoformat()); self.client.post('/loans',data=data); self.client.post('/loans',data=data)
        with app.app_context(): self.assertEqual(db().execute('SELECT COUNT(*) FROM loans').fetchone()[0],1)
        self.client.post('/loans/1/return'); self.client.post('/loans',data=data)
        with app.app_context(): self.assertEqual(db().execute('SELECT COUNT(*) FROM loans').fetchone()[0],2)
        self.assertIn(b'Test book',self.client.get('/').data)
    def test_bulk(self):
        self.client.post('/books/bulk',data={'csv':'title,author,category,isbn,copies\nOne,A,Fiction,,2\nTwo,B,Science,,3'})
        self.client.post('/books/bulk',data={'csv':'Three,A,Fiction,,1\nFour,B,Science,,0'})
        with app.app_context(): self.assertEqual(db().execute('SELECT COUNT(*) FROM books').fetchone()[0],2)
        self.assertEqual(self.client.get('/').status_code,200)
