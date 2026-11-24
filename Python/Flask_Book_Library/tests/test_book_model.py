import pytest
from sqlalchemy.exc import IntegrityError

from project.books.models import Book


def make_book(**overrides):
    data = {'name': 'Pan Tadeusz', 'author': 'Adam Mickiewicz', 'year_published': 1834, 'book_type': '2days'}
    data.update(overrides)
    return Book(**data)


def test_valid_book():
    book = make_book()
    assert book.name == 'Pan Tadeusz'
    assert book.author == 'Adam Mickiewicz'
    assert book.year_published == 1834
    assert book.book_type == '2days'
    assert book.status == 'available'


@pytest.mark.parametrize('name', ['Lalka', 'Zażółć gęślą jaźń', "O'Connor", 'Rok 1984', 'a' * 64])
def test_valid_names(name):
    assert make_book(name=name).name == name


@pytest.mark.parametrize('book_type', ['2days', '5days', '10days'])
def test_valid_book_types(book_type):
    assert make_book(book_type=book_type).book_type == book_type


def test_book_saved_in_db(session):
    session.add(make_book())
    session.flush()
    assert Book.query.filter_by(name='Pan Tadeusz').first().author == 'Adam Mickiewicz'


@pytest.mark.parametrize('field, value', [
    ('name', None),
    ('name', ''),
    ('name', '   '),
    ('name', 123),
    ('name', 'a' * 65),
    ('author', None),
    ('author', ''),
    ('author', 'a' * 65),
    ('year_published', 'abc'),
    ('year_published', None),
    ('year_published', -1),
    ('year_published', 3000),
    ('book_type', 'forever'),
    ('book_type', None),
    ('status', 'stolen'),
])
def test_invalid_data(field, value):
    with pytest.raises((ValueError, TypeError)):
        make_book(**{field: value})


def test_duplicate_name(session):
    session.add(make_book())
    session.flush()
    session.add(make_book())
    with pytest.raises(IntegrityError):
        session.flush()


SQL_PAYLOADS = ["' OR '1'='1", "'; DROP TABLE books; --", "' UNION SELECT * FROM books --", "admin'--"]


@pytest.mark.parametrize('payload', SQL_PAYLOADS)
@pytest.mark.parametrize('field', ['name', 'author', 'book_type'])
def test_sql_injection_rejected(field, payload):
    with pytest.raises((ValueError, TypeError)):
        make_book(**{field: payload})


@pytest.mark.parametrize('payload', SQL_PAYLOADS)
def test_sql_injection_in_query(session, payload):
    session.add(make_book())
    session.flush()
    assert Book.query.filter_by(name=payload).all() == []
    assert Book.query.filter_by(name='Pan Tadeusz').first() is not None


JS_PAYLOADS = ['<script>alert(1)</script>', '<img src=x onerror=alert(1)>', 'javascript:alert(1)', '"><svg onload=alert(1)>']


@pytest.mark.parametrize('payload', JS_PAYLOADS)
@pytest.mark.parametrize('field', ['name', 'author', 'book_type'])
def test_js_injection_rejected(field, payload):
    with pytest.raises((ValueError, TypeError)):
        make_book(**{field: payload})


@pytest.mark.parametrize('field, value', [
    ('name', 'a' * 1_000_000),
    ('author', 'a' * 1_000_000),
    ('name', 'Lalka\x00'),
    ('name', 'Lalka\u202e'),
    ('year_published', 10 ** 100),
    ('year_published', -(10 ** 100)),
    ('year_published', float('inf')),
    ('year_published', float('nan')),
])
def test_extreme_data(field, value):
    with pytest.raises((ValueError, TypeError)):
        make_book(**{field: value})


def test_many_books(session):
    before = Book.query.count()
    for i in range(1000):
        session.add(make_book(name=f'Ksiazka {i}'))
    session.flush()
    assert Book.query.count() == before + 1000
