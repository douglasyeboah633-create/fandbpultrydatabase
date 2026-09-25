"""MAIN APP for F & B Poultry Farm Management System. Run: python app.py"""
import hashlib
import os
import secrets
import sqlite3
import tempfile
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path
from flask import (Flask, request, jsonify, send_from_directory, send_file)
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (JWTManager, create_access_token,
                                decode_token,
                                jwt_required, get_jwt_identity,
                                verify_jwt_in_request)
from models import (db, User, Category, Product, InventoryTransaction,
                    Sale, Customer, DamageReport, FarmReport,
                    ShiftReport, Expense, Notification, ActivityLog, Setting,
                    ManagerRecord)

basedir = Path(__file__).resolve().parent
FRONTEND_DIR = basedir.parent / 'frontend'

# Local settings live in backend/.env, which is NEVER uploaded to GitHub.
# (See backend/.env.example for the names.) A hosting provider uses real
# environment variables instead.
try:
    from dotenv import load_dotenv
    load_dotenv(basedir / '.env')
except Exception:
    pass


def data_dir() -> Path:
    """Folder this app may write to: the database, uploaded photos and the
    login key. On a normal PC that is simply the backend folder. Some hosting
    sites give the code folder as read-only, so fall back to the system temp
    folder in that case. FB_DATA_DIR can force a folder (used by tests)."""
    p = Path(os.environ.get('FB_DATA_DIR') or basedir)
    try:
        p.mkdir(parents=True, exist_ok=True)
        probe = p / '.write_probe'
        probe.write_text('ok')
        probe.unlink()
        return p
    except Exception:
        q = Path(tempfile.gettempdir()) / 'fb_farm_data'
        q.mkdir(parents=True, exist_ok=True)
        return q


DATA_DIR = data_dir()


def jwt_secret():
    """The key used to sign logins. It must be the SAME on every copy of the
    app that answers your browser, otherwise a login made by one copy is
    refused by the next one and the pages say

        "Signature verification failed"

    (that is what a hosting site with several copies - for example Vercel -
    does, because each copy makes its own random key).

    Order of use:
      1. JWT_SECRET from the environment (best: set it on the hosting site).
      2. A key hidden inside MANAGER_USERNAME/MANAGER_PASSWORD (also set on the
         hosting site) so that every copy still agrees.
      3. backend/.secret_key, so that staying logged in survives a restart on
         your own PC. It is never written into this code, because the code is
         public.
    """
    s = (os.environ.get('JWT_SECRET') or '').strip()
    if s:
        return s
    user = (os.environ.get('MANAGER_USERNAME') or '').strip()
    pwd = os.environ.get('MANAGER_PASSWORD') or ''
    if pwd:
        blob = ('fb-poultry-farm-login|%s|%s' % (user, pwd)).encode('utf-8')
        return hashlib.sha256(blob).hexdigest()
    key_file = DATA_DIR / '.secret_key'
    try:
        if key_file.exists():
            s = key_file.read_text(encoding='utf-8').strip()
            if s:
                return s
        s = secrets.token_hex(32)
        key_file.write_text(s, encoding='utf-8')
    except Exception:
        pass
    if os.environ.get('VERCEL') or os.environ.get('RENDER'):
        print('WARNING: this app is running online without JWT_SECRET or '
              'MANAGER_PASSWORD. Set them in the hosting site\'s Environment '
              'settings, otherwise each copy of the app signs logins with a '
              'different key and the dashboard says "Signature verification '
              'failed".')
    return s or secrets.token_hex(32)


app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DATA_DIR / 'farm.db'}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = jwt_secret()
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=30)
db.init_app(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

PAYMENTS = ['cash', 'mobile_money', 'bank_transfer', 'other']


def log_action(user_id, username, action, detail=''):
    try:
        db.session.add(ActivityLog(user_id=user_id, username=username,
                                   action=action, detail=detail))
        db.session.commit()
    except Exception:
        db.session.rollback()


def notify(user_id, target_role, title, message):
    try:
        db.session.add(Notification(user_id=user_id, target_role=target_role,
                                    title=title, message=message))
        db.session.commit()
    except Exception:
        db.session.rollback()


def current_user():
    uid = get_jwt_identity()
    try:
        uid = int(uid)
    except (TypeError, ValueError):
        pass
    return User.query.get(uid)


def manager_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*a, **k):
        u = current_user()
        if not u or u.role != 'manager' or u.status != 'active':
            return jsonify({'error': 'Manager access required.'}), 403
        return fn(*a, **k)
    return wrapper


def login_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*a, **k):
        u = current_user()
        if not u or u.status != 'active':
            return jsonify({'error': 'Account disabled. Contact manager.'}), 403
        return fn(*a, **k)
    return wrapper


# ---------- AUTH ----------
@app.route('/api/auth/login', methods=['POST'])
def login():
    d = request.get_json(force=True, silent=True) or {}
    ident = (d.get('username') or d.get('email') or '').strip()
    pwd = d.get('password') or ''
    if not ident or not pwd:
        return jsonify({'error': 'Please enter username and password.'}), 400
    # Everyone logs in the same honest way: look the account up and check
    # the password. (There used to be a password hidden in this file - that
    # was dangerous in a public repository and is gone.)
    u = User.query.filter((User.username == ident) | (User.email == ident)).first()
    if not u:
        if not User.query.filter_by(role='manager').first():
            return jsonify({
                'code': 'setup_required',
                'error':
                "This hosting site has no manager login yet. Open the set-up "
                "form shown on this page and choose your username and "
                "password, or add MANAGER_PASSWORD in Vercel -> Settings -> "
                "Environment Variables (Production ticked) -> Save, then "
                "Redeploy (see README.md 'Deploy online (Vercel)')."}), 503
        return jsonify({'error': 'Login failed. Please check your credentials.'}), 401
    if not bcrypt.check_password_hash(u.password_hash, pwd):
        return jsonify({'error': 'Login failed. Please check your credentials.'}), 401
    if u.status != 'active':
        return jsonify({'error': 'Account disabled. Contact manager.'}), 403
    token = create_access_token(identity=str(u.id))
    log_action(u.id, u.username, 'Logged in', f'{u.role} login')
    return jsonify({'token': token, 'user': u.to_dict(),
                    'message': f'Welcome back, {u.full_name}!'})


@app.route('/api/auth/me', methods=['GET'])
@login_required
def me():
    return jsonify(current_user().to_dict())


@app.route('/api/auth/forgot', methods=['POST'])
def forgot():
    return jsonify({'message': 'Please contact your manager to reset your password.'})


@app.route('/api/auth/setup', methods=['POST'])
def setup_manager():
    """First-time set-up straight from the login page.

    Used ONLY while this copy of the app has no manager at all (a fresh
    hosting copy that was never given MANAGER_PASSWORD). The first person
    through chooses the username and password - no password in the code, no
    hosting-site settings needed. Extra guard: allowed only from Ghana or
    when the caller's country is unknown, so strangers cannot claim the
    farm. Once a manager exists this endpoint refuses forever."""
    country = (request.headers.get('x-vercel-ip-country') or '').strip().upper()
    if country and country != 'GH':
        return jsonify({'error':
            'Set-up can only be started from Ghana. (Administrator: set '
            "MANAGER_PASSWORD in the hosting site's Environment settings "
            'instead - see README.md.)'}), 403
    if User.query.filter_by(role='manager').first():
        return jsonify({'error':
            'This farm is already set up. Please log in instead.'}), 409
    d = request.get_json(force=True, silent=True) or {}
    un = (d.get('username') or '').strip()
    pw = d.get('password') or ''
    if not un or not pw:
        return jsonify({'error': 'Username and password are required.'}), 400
    if not (3 <= len(un) <= 40) or not un.replace('_', '').replace('-', '').isalnum():
        return jsonify({'error':
            'Username must be 3-40 characters: letters, numbers, _ or -.'}), 400
    if len(pw) < 8:
        return jsonify({'error':
            'Password must be at least 8 characters.'}), 400
    if User.query.filter((User.username == un) | (User.email == un)).first():
        return jsonify({'error': 'That username is already taken.'}), 409
    mgr = User(
        full_name=(d.get('full_name') or 'Farm Manager').strip() or 'Farm Manager',
        username=un,
        email=(d.get('email') or (un + '@fbpoultry.local')).strip(),
        phone='0500000000',
        password_hash=bcrypt.generate_password_hash(pw).decode(),
        role='manager', department='Management', status='active')
    db.session.add(mgr)
    db.session.commit()
    log_action(mgr.id, mgr.username, 'Manager account created',
               'First-time set-up from the login page.')
    token = create_access_token(identity=str(mgr.id))
    return jsonify({'token': token, 'user': mgr.to_dict(),
                    'message': 'Your manager account is ready!'}), 201


# ---------- DASHBOARDS ----------
@app.route('/api/dashboard/manager', methods=['GET'])
@manager_required
def dash_manager():
    approved = Product.query.filter_by(status='approved').all()
    total_stock = sum(p.quantity or 0 for p in approved)
    t = today_str()
    today_sales = Sale.query.filter(Sale.date == t).all()
    today_total = sum(s.total or 0 for s in today_sales)
    revenue = sum(s.total or 0 for s in Sale.query.all())
    expenses = sum(e.amount or 0 for e in Expense.query.all())
    sales_by_day = {}
    for s in Sale.query.all():
        k = (s.date or t)[:10]
        sales_by_day[k] = round(sales_by_day.get(k, 0) + (s.total or 0), 2)
    prod_sales = {}
    for s in Sale.query.all():
        prod_sales[s.product_name or 'Unknown'] = prod_sales.get(s.product_name or 'Unknown', 0) + (s.quantity or 0)
    return jsonify({
        'total_stock': total_stock,
        'products_available': len(approved),
        'todays_sales': round(today_total, 2),
        'todays_count': len(today_sales),
        'total_revenue': round(revenue, 2),
        'total_expenses': round(expenses, 2),
        'profit': round(revenue - expenses, 2),
        'unseen_reports': ShiftReport.query.filter_by(
            seen_by_manager=False).count(),
        'pending_submissions': Product.query.filter_by(status='pending').count(),
        'damage_pending': DamageReport.query.filter_by(status='pending').count(),
        'damage_approved_qty': sum(d.quantity or 0 for d in DamageReport.query.filter_by(status='approved').all()),
        'total_workers': User.query.filter_by(role='worker').count(),
        'sales_by_day': [{'date': k, 'total': v} for k, v in sorted(sales_by_day.items())[-14:]],
        'product_sales': [{'name': k, 'qty': v} for k, v in sorted(prod_sales.items(), key=lambda x: -x[1])[:8]],
        'shift_today': {sh: ShiftReport.query.filter_by(date=t, shift=sh).count()
                        for sh in ('morning', 'afternoon', 'evening')},
        'low_stock': [p.to_dict() for p in approved if (p.quantity or 0) <= 10][:10],
    })


@app.route('/api/dashboard/worker', methods=['GET'])
@login_required
def dash_worker():
    u = current_user()
    mine = Product.query.filter_by(worker_id=u.id).all()
    my_sales = Sale.query.filter_by(worker_id=u.id).all()
    notifs = Notification.query.filter(
        (Notification.user_id == u.id) |
        (Notification.target_role.in_(['worker', 'all']))).order_by(
        Notification.id.desc()).limit(20).all()
    return jsonify({
        'total_submitted': len(mine),
        'available': len([p for p in mine if p.status == 'approved' and (p.quantity or 0) > 0]),
        'sold_qty': sum(s.quantity or 0 for s in my_sales),
        'revenue': round(sum(s.total or 0 for s in my_sales), 2),
        'pending': len([p for p in mine if p.status == 'pending']),
        'approved': len([p for p in mine if p.status == 'approved']),
        'rejected': len([p for p in mine if p.status == 'rejected']),
        'recent': [p.to_dict() for p in sorted(mine, key=lambda x: x.id, reverse=True)[:5]],
        'unread': len([n for n in notifs if not n.is_read]),
        'shift_today': [r.shift for r in
                        ShiftReport.query.filter_by(worker_id=u.id,
                                                    date=today_str()).all()],
    })


# ---------- WORKERS (manager) ----------
@app.route('/api/workers', methods=['GET'])
@manager_required
def list_workers():
    q = request.args.get('q', '').strip().lower()
    users = User.query.filter_by(role='worker').order_by(User.id.desc()).all()
    out = []
    for u in users:
        if q and q not in (u.full_name + ' ' + u.username + ' ' + u.email).lower():
            continue
        d = u.to_dict()
        d['submissions'] = Product.query.filter_by(worker_id=u.id).count()
        d['sales'] = Sale.query.filter_by(worker_id=u.id).count()
        out.append(d)
    return jsonify(out)


@app.route('/api/workers', methods=['POST'])
@manager_required
def add_worker():
    me_u = current_user()
    d = request.get_json(force=True, silent=True) or {}
    for f in ['full_name', 'username', 'email', 'password']:
        if not (d.get(f) or '').strip():
            return jsonify({'error': f'Please enter {f.replace("_", " ")}.'}), 400
    if User.query.filter((User.username == d['username'].strip()) | (User.email == d['email'].strip())).first():
        return jsonify({'error': 'Username or email already exists.'}), 400
    role = d.get('role', 'worker') if d.get('role') in ('worker', 'manager') else 'worker'
    u = User(full_name=d['full_name'].strip(), username=d['username'].strip(),
             email=d['email'].strip(), phone=(d.get('phone') or '').strip(),
             password_hash=bcrypt.generate_password_hash(d['password']).decode(),
             role=role, department=(d.get('department') or 'General').strip(),
             status='active')
    db.session.add(u)
    db.session.commit()
    log_action(me_u.id, me_u.username, 'Worker added', u.username)
    return jsonify({'message': 'Worker added successfully.', 'user': u.to_dict()}), 201


@app.route('/api/workers/<int:uid>', methods=['PUT', 'DELETE'])
@manager_required
def edit_worker(uid):
    me_u = current_user()
    u = User.query.get_or_404(uid)
    if u.role != 'worker':
        return jsonify({'error': 'This account is not a worker, so it cannot '
                                 'be changed or removed here.'}), 400
    if request.method == 'DELETE':
        if u.id == me_u.id:
            return jsonify({'error': 'You cannot delete your own account.'}), 400
        db.session.delete(u)
        db.session.commit()
        log_action(me_u.id, me_u.username, 'Worker deleted', u.username)
        return jsonify({'message': 'Worker deleted.'})
    d = request.get_json(force=True, silent=True) or {}
    for f in ['full_name', 'phone', 'department', 'status']:
        if f in d and d[f] is not None:
            setattr(u, f, str(d[f]).strip())
    if d.get('password'):
        u.password_hash = bcrypt.generate_password_hash(d['password']).decode()
    db.session.commit()
    log_action(me_u.id, me_u.username, 'Worker updated', u.username)
    return jsonify({'message': 'Worker updated.', 'user': u.to_dict()})


@app.route('/api/workers/<int:uid>/reset-password', methods=['POST'])
@manager_required
def reset_pwd(uid):
    me_u = current_user()
    u = User.query.get_or_404(uid)
    if u.role != 'worker':
        return jsonify({'error': 'This account is not a worker, so its password '
                                 'cannot be reset here.'}), 400
    d = request.get_json(force=True, silent=True) or {}
    # No default password is filled here on purpose: the manager must type one
    # (the form already asks for it), so no real password ever ships in the code.
    new = (d.get('password') or '').strip()
    if not new:
        return jsonify({'error': 'Type a new password for this worker.'}), 400
    u.password_hash = bcrypt.generate_password_hash(new).decode()
    db.session.commit()
    log_action(me_u.id, me_u.username, 'Password reset', u.username)
    return jsonify({'message': f'Password reset for {u.username}.'})


# ---------- CATEGORIES ----------
@app.route('/api/categories', methods=['GET', 'POST'])
@login_required
def categories():
    if request.method == 'GET':
        return jsonify([c.to_dict() for c in Category.query.order_by(Category.name).all()])
    u = current_user()
    if u.role != 'manager':
        return jsonify({'error': 'Manager access required.'}), 403
    d = request.get_json(force=True, silent=True) or {}
    name = (d.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Please enter a category name.'}), 400
    if Category.query.filter_by(name=name).first():
        return jsonify({'error': 'Category already exists.'}), 400
    c = Category(name=name)
    db.session.add(c)
    db.session.commit()
    notify(None, 'manager', 'New category added',
           f'{u.full_name} added category "{name}".')
    log_action(u.id, u.username, 'Category added', name)
    return jsonify({'message': f'Category "{name}" added.', 'category': c.to_dict()}), 201

# ---------- PRODUCTS ----------
@app.route('/api/products', methods=['GET'])
@login_required
def list_products():
    u = current_user()
    status = request.args.get('status', '')
    cat = request.args.get('category', '')
    q = request.args.get('q', '').strip().lower()
    mine = request.args.get('mine', '')
    out = []
    for p in Product.query.order_by(Product.id.desc()).all():
        if mine == '1' and p.worker_id != u.id:
            continue
        if status and p.status != status:
            continue
        if cat and p.category_name != cat:
            continue
        if q and q not in (p.name + ' ' + p.category_name).lower():
            continue
        out.append(p.to_dict())
    return jsonify(out)


@app.route('/api/products', methods=['POST'])
@login_required
def add_product():
    u = current_user()
    d = request.get_json(force=True, silent=True) or {}
    name = (d.get('name') or '').strip()
    try:
        qty = int(d.get('quantity', 0))
        price = float(d.get('price_per_unit', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Please enter a valid quantity and price.'}), 400
    if not name:
        return jsonify({'error': 'Please enter a product name.'}), 400
    if qty < 0 or price < 0:
        return jsonify({'error': 'Quantity and price cannot be negative.'}), 400
    cat = (d.get('category') or d.get('category_name') or 'Other').strip()
    p = Product(name=name, category_name=cat, quantity=qty,
                opening_stock=qty, unit=(d.get('unit') or 'pcs').strip(),
                price_per_unit=price,
                description=(d.get('description') or '').strip(),
                farm_section=(d.get('farm_section') or 'Main').strip(),
                notes=(d.get('notes') or '').strip(),
                worker_id=u.id, worker_name=u.full_name,
                status='approved' if u.role == 'manager' else 'pending',
                date_available=(d.get('date_available') or today_str()))
    db.session.add(p)
    db.session.commit()
    db.session.add(InventoryTransaction(product_id=p.id, product_name=p.name,
                                        type='opening', quantity_change=qty,
                                        resulting_stock=qty,
                                        reference=('New stock received'
                                                   if u.role == 'manager'
                                                   else 'Initial stock'),
                                        worker_id=u.id,
                                        worker_name=u.full_name))
    db.session.commit()
    if u.role == 'manager':
        notify(None, 'manager', 'New stock received',
               f'{u.full_name} added new stock "{name}" ({qty} {p.unit}).')
        log_action(u.id, u.username, 'New stock received',
                   f'{name} x{qty} ({cat})')
        return jsonify({'message': f'New stock "{name}" added and approved.',
                        'product': p.to_dict()}), 201
    notify(None, 'manager', 'New product submission',
           f'{u.full_name} submitted "{name}" ({qty}).')
    log_action(u.id, u.username, 'Product submitted', f'{name} x{qty}')
    return jsonify({'message': 'Product added. Waiting for approval.',
                    'product': p.to_dict()}), 201


@app.route('/api/products/<int:pid>', methods=['PUT', 'DELETE'])
@login_required
def edit_product(pid):
    u = current_user()
    p = Product.query.get_or_404(pid)
    if request.method == 'DELETE':
        if u.role != 'manager' and p.worker_id != u.id:
            return jsonify({'error': 'Not allowed.'}), 403
        db.session.delete(p)
        db.session.commit()
        log_action(u.id, u.username, 'Product deleted', p.name)
        return jsonify({'message': 'Product deleted.'})
    d = request.get_json(force=True, silent=True) or {}
    if u.role == 'manager':
        for f in ['name', 'unit', 'description', 'farm_section',
                  'notes', 'date_available']:
            if f in d and d[f] is not None:
                setattr(p, f, str(d[f]).strip())
        if d.get('category'):
            p.category_name = str(d['category']).strip()
        if d.get('category_name'):
            p.category_name = str(d['category_name']).strip()
        if 'price_per_unit' in d:
            try:
                p.price_per_unit = float(d['price_per_unit'])
            except (TypeError, ValueError):
                return jsonify({'error': 'Enter a valid price.'}), 400
        if 'add_stock' in d:
            try:
                add = int(d['add_stock'])
            except (TypeError, ValueError):
                return jsonify({'error': 'Enter a valid quantity.'}), 400
            if add < 0:
                return jsonify({'error': 'Stock cannot be negative.'}), 400
            p.quantity = (p.quantity or 0) + add
            note = (d.get('note') or '').strip()
            db.session.add(InventoryTransaction(
                product_id=p.id, product_name=p.name, type='added',
                quantity_change=add, resulting_stock=p.quantity,
                reference=('Stock received' + (': ' + note if note else '')),
                worker_id=u.id, worker_name=u.full_name))
            if note:
                p.notes = (p.notes or '') + (
                    ('\n' if p.notes else '') +
                    f'[{today_str()} stock +{add} by {u.full_name}] {note}')
        db.session.commit()
        log_action(u.id, u.username, 'Product updated', p.name)
        return jsonify({'message': 'Product updated.',
                        'product': p.to_dict()})
    if p.worker_id != u.id or p.status != 'pending':
        return jsonify({'error': 'You can only edit pending items.'}), 403
    if 'quantity' in d:
        try:
            p.quantity = int(d['quantity'])
            p.opening_stock = p.quantity
        except (TypeError, ValueError):
            return jsonify({'error': 'Enter a valid quantity.'}), 400
    for f in ['name', 'description', 'notes']:
        if f in d and d[f]:
            setattr(p, f, str(d[f]).strip())
    db.session.commit()
    return jsonify({'message': 'Updated.', 'product': p.to_dict()})


@app.route('/api/products/<int:pid>/approve', methods=['POST'])
@manager_required
def approve_product(pid):
    u = current_user()
    p = Product.query.get_or_404(pid)
    p.status = 'approved'
    db.session.commit()
    if p.worker_id:
        notify(p.worker_id, 'worker', 'Submission approved',
               f'Your product "{p.name}" has been approved.')
    log_action(u.id, u.username, 'Product approved', p.name)
    return jsonify({'message': 'Product approved.',
                    'product': p.to_dict()})


@app.route('/api/products/<int:pid>/reject', methods=['POST'])
@manager_required
def reject_product(pid):
    u = current_user()
    p = Product.query.get_or_404(pid)
    p.status = 'rejected'
    db.session.commit()
    if p.worker_id:
        notify(p.worker_id, 'worker', 'Submission rejected',
               f'Your product "{p.name}" was rejected.')
    log_action(u.id, u.username, 'Product rejected', p.name)
    return jsonify({'message': 'Product rejected.',
                    'product': p.to_dict()})

    return jsonify({'message': 'Category added.', 'category': c.to_dict()}), 201

def today_str():
    return datetime.now().strftime('%Y-%m-%d')


# ---------- SALES ----------
@app.route('/api/sales', methods=['GET'])
@login_required
def list_sales():
    u = current_user()
    mine = request.args.get('mine', '')
    q = request.args.get('q', '').strip().lower()
    out = []
    for s in Sale.query.order_by(Sale.id.desc()).all():
        if mine == '1' and s.worker_id != u.id:
            continue
        if q and q not in ((s.product_name or '') + ' ' + s.customer_name).lower():
            continue
        out.append(s.to_dict())
    return jsonify(out)


@app.route('/api/sales', methods=['POST'])
@login_required
def add_sale():
    u = current_user()
    d = request.get_json(force=True, silent=True) or {}
    try:
        pid = int(d.get('product_id'))
        qty = int(d.get('quantity'))
    except (TypeError, ValueError):
        return jsonify({'error': 'Select a product and quantity.'}), 400
    if qty <= 0:
        return jsonify({'error': 'Enter a valid quantity.'}), 400
    p = Product.query.get(pid)
    if not p or p.status != 'approved':
        return jsonify({'error': 'Product not available.'}), 400
    if qty > (p.quantity or 0):
        return jsonify({'error': f'Insufficient stock. Only {p.quantity} left.'}), 400
    price = p.price_per_unit or 0
    total = round(qty * price, 2)
    cname = (d.get('customer_name') or '').strip()
    if not cname:
        cname = 'Daily walk-in sales'
    pm = (d.get('payment_method') or 'cash').strip()
    if pm not in PAYMENTS:
        pm = 'cash'
    s = Sale(product_id=p.id, product_name=p.name, quantity=qty,
             price_per_unit=price, total=total, customer_name=cname,
             customer_phone=(d.get('customer_phone') or '').strip(),
             payment_method=pm, date=(d.get('date') or today_str()),
             worker_id=u.id, worker_name=u.full_name,
             notes=(d.get('notes') or '').strip())
    p.quantity = (p.quantity or 0) - qty
    db.session.add(s)
    db.session.commit()
    db.session.add(InventoryTransaction(product_id=p.id,
                                        product_name=p.name, type='sold',
                                        quantity_change=-qty,
                                        resulting_stock=p.quantity,
                                        reference=f'Sale #{s.id}',
                                        worker_id=u.id,
                                        worker_name=u.full_name))
    c = Customer.query.filter_by(name=cname).first()
    if not c:
        c = Customer(name=cname, phone=s.customer_phone)
        db.session.add(c)
    c.total_orders = (c.total_orders or 0) + 1
    c.total_spent = round((c.total_spent or 0) + total, 2)
    db.session.commit()
    if p.quantity <= 10:
        notify(None, 'manager', 'Low stock',
               f'{p.name} low: {p.quantity} left.')
    log_action(u.id, u.username, 'Sale recorded',
               f'{p.name} x{qty} = {total}')
    return jsonify({'message': 'Sale recorded successfully.',
                    'sale': s.to_dict()}), 201


# ---------- DAILY REPORT (one-submit end-of-day sales) ----------
@app.route('/api/daily-report', methods=['POST'])
@login_required
def daily_report():
    u = current_user()
    d = request.get_json(force=True, silent=True) or {}
    date = str(d.get('date') or today_str()).strip()[:10]
    items = d.get('items') or d.get('lines') or []
    if not isinstance(items, list) or not items:
        return jsonify({'error': 'Add at least one line, e.g. 20 chickens.'}), 400
    pm = str(d.get('payment_method') or 'cash').strip()
    if pm not in PAYMENTS:
        pm = 'cash'
    validated = []
    for it in items:
        if not isinstance(it, dict):
            continue
        try:
            pid = int(it.get('product_id'))
            qty = int(it.get('quantity'))
        except (TypeError, ValueError):
            return jsonify({'error': 'Each line needs a product and a quantity.'}), 400
        if qty <= 0:
            continue
        p = Product.query.get(pid)
        if not p or p.status != 'approved':
            return jsonify({'error': 'One selected product is not available for sale.'}), 400
        if qty > (p.quantity or 0):
            return jsonify({'error': 'Not enough %s. Only %s left.' % (p.name, p.quantity)}), 400
        validated.append((p, qty))
    if not validated:
        return jsonify({'error': 'Enter a quantity above 0.'}), 400
    total_qty = 0
    grand = 0.0
    for p, qty in validated:
        price = p.price_per_unit or 0
        total = round(qty * price, 2)
        s = Sale(product_id=p.id, product_name=p.name, quantity=qty,
                 price_per_unit=price, total=total,
                 customer_name='Daily walk-in sales', customer_phone='',
                 payment_method=pm, date=date,
                 worker_id=u.id, worker_name=u.full_name,
                 notes=str(d.get('notes') or '').strip())
        p.quantity = (p.quantity or 0) - qty
        db.session.add(s)
        db.session.flush()
        db.session.add(InventoryTransaction(
            product_id=p.id, product_name=p.name, type='sold',
            quantity_change=-qty, resulting_stock=p.quantity,
            reference='Daily report Sale #%s' % s.id,
            worker_id=u.id, worker_name=u.full_name))
        c = Customer.query.filter_by(name='Daily walk-in sales').first()
        if not c:
            c = Customer(name='Daily walk-in sales')
            db.session.add(c)
        c.total_orders = (c.total_orders or 0) + 1
        c.total_spent = round((c.total_spent or 0) + total, 2)
        total_qty += qty
        grand = round(grand + total, 2)
        if p.quantity <= 10:
            notify(None, 'manager', 'Low stock',
                   '%s running low: %s left.' % (p.name, p.quantity))
    try:
        dead = int(d.get('dead_qty') or 0)
    except (TypeError, ValueError):
        dead = 0
    if dead > 0:
        dp = validated[0][0]
        db.session.add(DamageReport(
            product_id=dp.id, product_name=dp.name, quantity=dead,
            date=date, reason=str(d.get('dead_reason') or '').strip(),
            farm_section='Main', worker_id=u.id, worker_name=u.full_name,
            description=str(d.get('notes') or '').strip(), status='pending'))
    db.session.commit()
    summary = ', '.join('%s x%s' % (p.name, q) for p, q in validated)
    notify(None, 'manager', 'Daily report submitted',
           '%s reported %s = %s on %s.' % (u.full_name, summary, grand, date))
    log_action(u.id, u.username, 'Daily report submitted',
               '%s = %s' % (summary, grand))
    return jsonify({'message': 'Daily report sent! %s items totalling %s.' % (total_qty, grand),
                    'total_qty': total_qty, 'grand_total': grand,
                    'lines': len(validated)}), 201


# ---------- SHIFT REPORTS (morning / afternoon / evening) ----------
# One report for the whole day (no more morning/afternoon/evening).
SHIFTS = ['daily']

# Every one of these spaces must be filled before a report can be sent.
# (key in the JSON body, label shown to the worker)
REQUIRED_SHIFT_FIELDS = [
    ('date', 'Date'),
    ('farm_section', 'Farm section'),
    ('crates_sold', 'Egg crates sold'),
    ('chickens_sold', 'Live chickens sold'),
    ('birds_died', 'Birds died (number)'),
    ('death_reason', 'Reason for the deaths'),
    ('feed_qty', 'Feed type / note'),
    ('feed_bags', 'Feed used (bags)'),
    ('feed_kg', 'Feed used (kg)'),
    ('birds_fed', 'Birds fed (count)'),
    ('water_liters', 'Water used (litres)'),
    ('water_notes', 'Water notes'),
    ('eggs_collected', 'Eggs collected'),
    ('egg_crates', 'Egg crates packed'),
    ('eggs_broken', 'Eggs broken / spoilt'),
    ('amount', 'Total amount you got (GH\u20b5)'),
    ('problems', 'Other activities / problems'),
    ('notes', 'Notes for manager'),
]

_NUMERIC_SHIFT_FIELDS = {'feed_bags', 'feed_kg', 'water_liters', 'amount',
                         'birds_died', 'birds_fed', 'eggs_collected',
                         'egg_crates', 'eggs_broken', 'chickens_sold',
                         'crates_sold'}


def shift_missing_fields(d):
    """Labels of every space the worker left empty. Empty list == complete."""
    missing = []
    for key, label in REQUIRED_SHIFT_FIELDS:
        raw = d.get(key)
        txt = '' if raw is None else str(raw).strip()
        if txt == '':
            missing.append(label)
            continue
        if key in _NUMERIC_SHIFT_FIELDS:
            try:
                float(txt)
            except (TypeError, ValueError):
                missing.append(label)
    # a real mortality must always come with a photo as proof
    if to_int(d.get('birds_died')) > 0 and not str(d.get('death_image') or '').strip():
        missing.append('\U0001f4f7 Photo of the dead bird(s)')
    return missing


def to_int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def to_float(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def ensure_shift_columns():
    """Create shift_reports table + any newer columns on an old farm.db."""
    db.create_all()
    try:
        cols = {c[1] for c in db.session.execute(
            db.text('PRAGMA table_info(shift_reports)')).fetchall()}
    except Exception:
        return
    wanted = {'feed_bags': 'FLOAT', 'feed_kg': 'FLOAT',
              'water_liters': 'FLOAT', 'egg_crates': 'INTEGER',
              'chickens_sold': 'INTEGER', 'crates_sold': 'INTEGER',
              'seen_by_manager': 'BOOLEAN', 'reviewed_at': 'DATETIME',
              'manager_comment': 'TEXT', 'death_image': 'STRING',
              'amount': 'FLOAT'}
    for col, typ in wanted.items():
        if col not in cols:
            try:
                db.session.execute(db.text(
                    'ALTER TABLE shift_reports ADD COLUMN %s %s' % (col, typ)))
            except Exception:
                db.session.rollback()
                return
    db.session.commit()


def record_sale_for_shift(u, pid, qty, date, pm,
                          customer_name='Daily walk-in sales',
                          customer_phone=''):
    """Shared sale writer used by Record Sale, Daily Report and Shift Reports.

    Reduces stock, writes InventoryTransaction and Customer stats.
    Raises ValueError with a user-friendly message on any problem."""
    p = Product.query.get(pid)
    if not p or p.status != 'approved':
        raise ValueError('%s is not available for sale.' % (
            p.name if p else 'Product'))
    if qty <= 0:
        raise ValueError('Enter a quantity above 0.')
    if qty > (p.quantity or 0):
        raise ValueError('Not enough %s. Only %s left.' % (p.name, p.quantity))
    price = p.price_per_unit or 0
    total = round(qty * price, 2)
    if pm not in PAYMENTS:
        pm = 'cash'
    s = Sale(product_id=p.id, product_name=p.name, quantity=qty,
             price_per_unit=price, total=total,
             customer_name=customer_name, customer_phone=customer_phone,
             payment_method=pm, date=date,
             worker_id=u.id, worker_name=u.full_name)
    p.quantity = (p.quantity or 0) - qty
    db.session.add(s)
    db.session.flush()
    db.session.add(InventoryTransaction(
        product_id=p.id, product_name=p.name, type='sold',
        quantity_change=-qty, resulting_stock=p.quantity,
        reference='Shift report Sale #%s' % s.id,
        worker_id=u.id, worker_name=u.full_name))
    if customer_name and customer_name != 'Daily walk-in sales':
        c = Customer.query.filter_by(name=customer_name).first()
        if not c:
            c = Customer(name=customer_name, phone=customer_phone)
            db.session.add(c)
        c.total_orders = (c.total_orders or 0) + 1
        c.total_spent = round((c.total_spent or 0) + total, 2)
    if p.quantity <= 10:
        notify(None, 'manager', 'Low stock',
               '%s running low: %s left.' % (p.name, p.quantity))
    db.session.flush()
    return p, s, total



@app.route('/api/shift-reports', methods=['GET'])
@login_required
def list_shift_reports():
    u = current_user()
    date = (request.args.get('date') or '').strip()[:10]
    status = (request.args.get('status') or '').strip().lower()
    ensure_shift_columns()
    q = ShiftReport.query
    if date:
        q = q.filter(ShiftReport.date == date)
    if status == 'reviewed':
        q = q.filter(ShiftReport.seen_by_manager.is_(True))
    elif status == 'pending':
        q = q.filter(ShiftReport.seen_by_manager.is_(False))
    if u.role != 'manager':
        q = q.filter(ShiftReport.worker_id == u.id)
    return jsonify([r.to_dict() for r in
                    q.order_by(ShiftReport.id.desc()).all()])


@app.route('/api/shift-reports', methods=['POST'])
@login_required
def add_shift_report():
    u = current_user()
    ensure_shift_columns()
    d = request.get_json(force=True, silent=True) or {}
    missing = shift_missing_fields(d)
    if missing:
        return jsonify({'error': 'Please fill in every space before you send '
                                 'the report. Still empty: ' +
                                 ', '.join(missing)}), 400
    shift = (d.get('shift') or 'daily').strip().lower()
    if shift not in SHIFTS:
        shift = 'daily'
    date = (str(d.get('date') or today_str())).strip()[:10]
    existing = ShiftReport.query.filter_by(
        worker_id=u.id, date=date).first()
    if existing:
        return jsonify({'error': 'You already sent your report for %s.'
                                 ' Only one report per day is allowed - use'
                                 ' Edit if you need to correct it.' % date}), 409
    pm = str(d.get('payment_method') or 'cash').strip()
    if pm not in PAYMENTS:
        pm = 'cash'
    sales = d.get('sales') or d.get('items') or d.get('lines') or []
    if not isinstance(sales, list):
        sales = []
    created = []
    grand = 0.0
    for it in sales:
        if not isinstance(it, dict):
            continue
        try:
            pid = int(it.get('product_id'))
            qty = int(it.get('quantity'))
        except (TypeError, ValueError):
            return jsonify({'error': 'Each sales line needs a product and a quantity.'}), 400
        if qty <= 0:
            continue
        try:
            p, s, total = record_sale_for_shift(u, pid, qty, date, pm)
        except ValueError as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
        created.append((p, qty, s))
        grand = round(grand + total, 2)
    feed_done = bool(d.get('feed_done'))
    water_done = bool(d.get('water_done'))
    feed_bags = to_float(d.get('feed_bags'))
    feed_kg = to_float(d.get('feed_kg'))
    water_liters = to_float(d.get('water_liters'))
    egg_crates = to_int(d.get('egg_crates'))
    chickens_sold = to_int(d.get('chickens_sold'))
    crates_sold = to_int(d.get('crates_sold'))
    eggs_collected = to_int(d.get('eggs_collected'))
    eggs_broken = to_int(d.get('eggs_broken'))
    birds_fed = to_int(d.get('birds_fed'))
    birds_died = to_int(d.get('birds_died'))
    rep = ShiftReport(
        date=date, shift=shift, worker_id=u.id, worker_name=u.full_name,
        farm_section=(d.get('farm_section') or 'Main'),
        feed_done=feed_done,
        feed_qty=str(d.get('feed_qty') or '').strip() or None,
        feed_bags=feed_bags, feed_kg=feed_kg,
        birds_fed=birds_fed, water_done=water_done,
        water_liters=water_liters,
        water_notes=str(d.get('water_notes') or '').strip() or None,
        eggs_collected=eggs_collected, eggs_broken=eggs_broken,
        egg_crates=egg_crates,
        chickens_sold=chickens_sold, crates_sold=crates_sold,
        birds_died=birds_died,
        death_reason=str(d.get('death_reason') or '').strip() or None,
        death_image=str(d.get('death_image') or '').strip() or None,
        sale_ids=','.join(str(s.id) for _, _, s in created) or None,
        sales_summary=', '.join('%s x%s' % (p.name, q)
                                for p, q, _ in created) or None,
        sales_total=grand,
        problems=str(d.get('problems') or '').strip() or None,
        notes=str(d.get('notes') or '').strip() or None,
        amount=to_float(d.get('amount')))
    db.session.add(rep)
    db.session.commit()
    lines_txt = ', '.join('%s x%s' % (p.name, q) for p, q, _ in created)
    for p, qty, s in created:
        s.notes = 'Daily report %s' % date
    log_action(u.id, u.username, 'Daily report submitted',
               '%s %s: feed=%s water=%s eggs=%s sold=%s died=%s' %
               (date, shift, 'yes' if feed_done else 'no',
                'yes' if water_done else 'no', eggs_collected,
                lines_txt or 'none', birds_died))
    notify(None, 'manager', 'Daily report submitted',
           '%s sent the daily report for %s: %s.' %
           (u.full_name, date, lines_txt or 'no sales'))
    db.session.commit()
    nlines = sum(q for _, q, _ in created)
    msg = 'Daily report sent for %s!' % date
    if created:
        msg += ' %s sold totalling %s.' % (nlines, grand)
    return jsonify({'message': msg,
                    'shift_report': rep.to_dict()}), 201


@app.route('/api/shift-reports/<int:rid>', methods=['PUT'])
@login_required
def edit_shift_report(rid):
    u = current_user()
    r = ShiftReport.query.get(rid)
    if not r:
        return jsonify({'error': 'Report not found.'}), 404
    if u.role != 'manager' and r.worker_id != u.id:
        return jsonify({'error': 'You can only edit your own reports.'}), 403
    d = request.get_json(force=True, silent=True) or {}
    if r.death_image and not str(d.get('death_image') or '').strip():
        d['death_image'] = r.death_image
    missing = shift_missing_fields(d)
    if missing:
        return jsonify({'error': 'Please fill in every space before you save '
                                 'the report. Still empty: ' +
                                 ', '.join(missing)}), 400
    # once submitted, sales lines are never edited or deleted
    if 'sales' in d or 'items' in d or 'lines' in d or 'sale_ids' in d:
        return jsonify({'error': 'A submitted report cannot be changed. It is kept as a permanent record.'}), 400
    r.farm_section = str(d.get('farm_section') or r.farm_section or 'Main')
    r.feed_done = bool(d.get('feed_done', r.feed_done))
    r.feed_qty = str(d.get('feed_qty') or '').strip() or r.feed_qty
    r.feed_bags = to_float(d.get('feed_bags', r.feed_bags or 0))
    r.feed_kg = to_float(d.get('feed_kg', r.feed_kg or 0))
    r.birds_fed = to_int(d.get('birds_fed', r.birds_fed))
    r.water_done = bool(d.get('water_done', r.water_done))
    r.water_liters = to_float(d.get('water_liters', r.water_liters or 0))
    r.water_notes = (str(d.get('water_notes') or '').strip()
                     or r.water_notes)
    r.eggs_collected = to_int(d.get('eggs_collected', r.eggs_collected))
    r.eggs_broken = to_int(d.get('eggs_broken', r.eggs_broken))
    r.egg_crates = to_int(d.get('egg_crates', r.egg_crates or 0))
    r.chickens_sold = to_int(d.get('chickens_sold', r.chickens_sold or 0))
    r.crates_sold = to_int(d.get('crates_sold', r.crates_sold or 0))
    r.birds_died = to_int(d.get('birds_died', r.birds_died))
    r.death_reason = (str(d.get('death_reason') or '').strip()
                      or r.death_reason)
    if 'death_image' in d:
        r.death_image = str(d.get('death_image') or '').strip() or None
    r.problems = (str(d.get('problems') or '').strip()
                  or r.problems)
    r.notes = (str(d.get('notes') or '').strip() or r.notes)
    if 'amount' in d:
        r.amount = to_float(d.get('amount'))
    if 'death_image' in d:
        r.death_image = (str(d.get('death_image') or '').strip()
                         or r.death_image)
    db.session.commit()
    return jsonify({'message': 'Shift report updated.',
                    'shift_report': r.to_dict()})


@app.route('/api/shift-reports/<int:rid>/reviewed', methods=['POST'])
@manager_required
def review_shift_report(rid):
    r = ShiftReport.query.get(rid)
    if not r:
        return jsonify({'error': 'Report not found.'}), 404
    r.seen_by_manager = True
    db.session.commit()
    log_action(None, 'manager', 'Shift report reviewed',
               '%s %s report #%s' % (r.date, r.shift, r.id))
    return jsonify({'message': 'Marked as reviewed.',
                    'shift_report': r.to_dict()})


@app.route('/api/shift-reports/<int:rid>/comment', methods=['POST'])
@manager_required
def comment_shift_report(rid):
    r = ShiftReport.query.get(rid)
    if not r:
        return jsonify({'error': 'Report not found.'}), 404
    d = request.get_json(force=True, silent=True) or {}
    comment = (d.get('comment') or '').strip()
    if not comment:
        return jsonify({'error': 'Write something first.'}), 400
    r.manager_comment = comment
    r.seen_by_manager = True
    db.session.commit()
    if r.worker_id:
        notify(r.worker_id, None, 'Manager replied to your report',
               'Your %s report for %s: "%s"' % (r.shift, r.date, comment))
    log_action(None, 'manager', 'Report commented',
               '%s %s report #%s: %s' % (r.date, r.shift, r.id, comment))
    return jsonify({'message': 'Note saved on the report.',
                    'shift_report': r.to_dict()})


@app.route('/api/reminders/check', methods=['POST'])
@login_required
def reminders_check():
    u = current_user()
    now = datetime.now()
    t = today_str()
    hour = now.hour + now.minute / 60.0
    sent = []
    if u.role == 'worker' and hour >= 19.0:
        have = [r for r in ShiftReport.query.filter_by(worker_id=u.id,
                                                      date=t).all()]
        if not have:
            key = 'remind-shift-%s-%s' % (u.id, t)
            if not ActivityLog.query.filter_by(action=key).first():
                db.session.add(ActivityLog(
                    user_id=u.id, username=u.username, action=key,
                    detail='7pm daily report reminder sent'))
                notify(u.id, None, chr(9200) + ' Daily report reminder',
                       'It is past 7pm and you have not sent your daily report for today (%s). Please fill every space and send it now.' % t)
                db.session.commit()
                log_action(u.id, u.username, 'Daily report reminder sent', t)
                sent.append('shift')
    if u.role == 'manager':
        unseen = ShiftReport.query.filter_by(seen_by_manager=False).count()
        if unseen:
            key = 'remind-unseen-%s' % t
            if not ActivityLog.query.filter_by(action=key).first():
                db.session.add(ActivityLog(
                    user_id=u.id, username=u.username, action=key,
                    detail='%s unseen reports' % unseen))
                notify(None, 'manager', chr(128229) + ' Unreviewed worker reports',
                       'You have %s report(s) you have not checked yet. Open Worker Reports and mark each as Reviewed.' % unseen)
                db.session.commit()
                sent.append('unseen')
    return jsonify({'reminded': sent})


@app.route('/api/shift-reports/weekly', methods=['GET'])
@login_required
def weekly_shift_reports():
    u = current_user()
    days = []
    for i in range(6, -1, -1):
        days.append((datetime.now() -
                     timedelta(days=i)).strftime('%Y-%m-%d'))
    q = ShiftReport.query.filter(ShiftReport.date.in_(days))
    if u.role != 'manager':
        q = q.filter(ShiftReport.worker_id == u.id)
    rows = q.all()

    def day_total(day, field):
        tot = 0.0
        for r in rows:
            if r.date == day:
                tot += to_float(getattr(r, field, 0) or 0)
        return tot

    def day_int(day, *fields):
        tot = 0
        for r in rows:
            if r.date == day:
                for f in fields:
                    tot += to_int(getattr(r, f, 0) or 0)
        return tot

    return jsonify({
        'days': days,
        'feeding_bags': [round(day_total(day, 'feed_bags'), 2)
                         for day in days],
        'feeding_kg': [round(day_total(day, 'feed_kg'), 2) for day in days],
        'water_liters': [round(day_total(day, 'water_liters'), 2)
                         for day in days],
        'eggs': [day_int(day, 'eggs_collected') for day in days],
        'egg_crates': [day_int(day, 'egg_crates', 'crates_sold')
                       for day in days],
        'chickens_sold': [day_int(day, 'chickens_sold') for day in days],
        'amounts': [round(day_total(day, 'amount')
                          or day_total(day, 'sales_total'), 2)
                    for day in days],
    })


@app.route('/api/shift-reports/<int:rid>', methods=['DELETE'])
@login_required
def delete_shift_report(rid):
    """A report can be deleted: a worker may delete their own report and
    the manager may delete any report (a notification is sent to the worker)."""
    u = current_user()
    r = ShiftReport.query.get(rid)
    if not r:
        return jsonify({'error': 'Report not found.'}), 404
    if u.role != 'manager' and r.worker_id != u.id:
        return jsonify({'error': 'You can only delete your own reports.'}), 403
    info = '%s %s report #%s by %s' % (r.date, r.shift, r.id, r.worker_name)
    wid, sh, dt = r.worker_id, r.shift, r.date
    db.session.delete(r)
    db.session.commit()
    log_action(u.id, u.username, 'Shift report deleted', info)
    if u.role == 'manager' and wid:
        notify(wid, None, 'Report deleted',
               'Your %s report for %s was deleted by the manager. '
               'Please submit it again if it was still needed.' % (sh, dt))
        db.session.commit()
    return jsonify({'message': 'Report deleted.'})



# ---------- IMAGE UPLOADS (e.g. mortality photos) ----------
UPLOAD_DIR = DATA_DIR / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.route('/api/uploads', methods=['POST'])
@login_required
def upload_file():
    f = request.files.get('file')
    if not f or not f.filename:
        return jsonify({'error': 'No image was selected.'}), 400
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
        return jsonify({'error': 'Only image files (png, jpg, gif, webp) are allowed.'}), 400
    fname = 'mort_%s%s' % (datetime.utcnow().strftime('%Y%m%d%H%M%S%f'), ext)
    f.save(str(UPLOAD_DIR / fname))
    return jsonify({'url': '/api/uploads/%s' % fname, 'filename': fname}), 201


@app.route('/api/uploads/<path:fname>')
def get_upload(fname):
    """Serve an uploaded image. Works with the normal Authorization
    header OR ?token=... in the URL (needed because <img> tags cannot
    send headers). Tokens in URLs are accepted only for GET views."""
    tok = request.args.get('token') or ''
    if not tok:
        try:
            verify_jwt_in_request()
        except Exception:
            return jsonify({'error': 'Login required.'}), 401
    else:
        try:
            decode_token(tok)
        except Exception:
            return jsonify({'error': 'Login required (bad token).'}), 401
    safe = os.path.basename(fname)
    return send_from_directory(str(UPLOAD_DIR), safe)


# ---------- INVENTORY ----------
@app.route('/api/inventory', methods=['GET'])
@manager_required
def inventory():
    rows = []
    for p in Product.query.order_by(Product.name).all():
        tx = InventoryTransaction.query.filter_by(product_id=p.id).all()
        added = sum(t.quantity_change for t in tx if t.type == 'added')
        sold = sum(-t.quantity_change for t in tx if t.type == 'sold')
        dmg = sum(-t.quantity_change for t in tx if t.type == 'damaged')
        rows.append({'id': p.id, 'product': p.name,
                     'category': p.category_name,
                     'quantity': p.quantity, 'price': p.price_per_unit,
                     'status': p.status, 'worker': p.worker_name,
                     'opening': p.opening_stock or 0, 'added': added,
                     'sold': sold, 'damaged': dmg,
                     'remaining': p.quantity or 0})
    return jsonify(rows)


@app.route('/api/inventory/history/<int:pid>', methods=['GET'])

@login_required

def inv_history(pid):

    tx = InventoryTransaction.query.filter_by(

        product_id=pid).order_by(InventoryTransaction.id.desc()).all()

    return jsonify([t.to_dict() for t in tx])





# ---------- DAMAGE + FARM REPORTS ----------
@app.route('/api/damage', methods=['GET'])
@login_required
def list_damage():
    u = current_user()
    mine = request.args.get('mine', '')
    out = []
    for r in DamageReport.query.order_by(DamageReport.id.desc()).all():
        if mine == '1' and r.worker_id != u.id:
            continue
        out.append(r.to_dict())
    return jsonify(out)


@app.route('/api/damage', methods=['POST'])
@login_required
def add_damage():
    u = current_user()
    d = request.get_json(force=True, silent=True) or {}
    try:
        qty = int(d.get('quantity', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Enter a valid quantity.'}), 400
    pname = (d.get('product_name') or '').strip()
    pid = d.get('product_id')
    p = None
    if pid:
        try:
            p = Product.query.get(int(pid))
            if p:
                pname = p.name
        except (TypeError, ValueError):
            pass
    if not pname or qty <= 0:
        return jsonify({'error': 'Select product and quantity.'}), 400
    r = DamageReport(product_id=p.id if p else None,
                     product_name=pname, quantity=qty,
                     date=(d.get('date') or today_str()),
                     reason=(d.get('reason') or '').strip(),
                     farm_section=(d.get('farm_section') or 'Main').strip(),
                     worker_id=u.id, worker_name=u.full_name,
                     description=(d.get('description') or '').strip(),
                     status='pending')
    db.session.add(r)
    db.session.commit()
    notify(None, 'manager', 'Damage report',
           f'{u.full_name} reported {qty} x {pname}.')
    log_action(u.id, u.username, 'Damage reported', f'{pname} x{qty}')
    return jsonify({'message': 'Damage report submitted.',
                    'report': r.to_dict()}), 201


@app.route('/api/damage/<int:rid>/review', methods=['POST'])
@manager_required
def review_damage(rid):
    u = current_user()
    r = DamageReport.query.get_or_404(rid)
    d = request.get_json(force=True, silent=True) or {}
    act = (d.get('action') or 'approve').strip()
    if act == 'approve':
        r.status = 'approved'
        p = Product.query.get(r.product_id) if r.product_id else None
        if not p:
            p = Product.query.filter_by(name=r.product_name).first()
        if p:
            p.quantity = max(0, (p.quantity or 0) - r.quantity)
            db.session.add(InventoryTransaction(
                product_id=p.id, product_name=p.name, type='damaged',
                quantity_change=-r.quantity, resulting_stock=p.quantity,
                reference=f'Damage #{r.id}', worker_id=u.id,
                worker_name=u.full_name))
        if r.worker_id:
            notify(r.worker_id, 'worker', 'Damage approved',
                   f'Report for {r.product_name} approved.')
    else:
        r.status = 'rejected'
        if r.worker_id:
            notify(r.worker_id, 'worker', 'Damage rejected',
                   f'Report for {r.product_name} needs correction.')
    db.session.commit()
    log_action(u.id, u.username, f'Damage {r.status}', r.product_name)
    return jsonify({'message': f'Report {r.status}.',
                    'report': r.to_dict()})


@app.route('/api/farm-reports', methods=['GET', 'POST'])
@login_required
def farm_reports():
    u = current_user()
    if request.method == 'GET':
        mine = request.args.get('mine', '')
        out = []
        for r in FarmReport.query.order_by(FarmReport.id.desc()).all():
            if mine == '1' and r.worker_id != u.id:
                continue
            out.append(r.to_dict())
        return jsonify(out)
    d = request.get_json(force=True, silent=True) or {}
    def num(k):
        try:
            return int(d.get(k, 0) or 0)
        except (TypeError, ValueError):
            return 0
    r = FarmReport(date=(d.get('date') or today_str()),
                   worker_id=u.id, worker_name=u.full_name,
                   farm_section=(d.get('farm_section') or 'Main').strip(),
                   num_birds=num('num_birds'),
                   feed_used=str(d.get('feed_used') or '').strip(),
                   eggs_collected=num('eggs_collected'),
                   birds_sold=num('birds_sold'),
                   birds_died=num('birds_died'),
                   problems=(d.get('problems') or '').strip(),
                   observations=(d.get('observations') or '').strip(),
                   recommendations=(d.get('recommendations') or '').strip())
    db.session.add(r)
    db.session.commit()
    log_action(u.id, u.username, 'Farm report submitted', r.date)
    return jsonify({'message': 'Farm report submitted.',
                    'report': r.to_dict()}), 201


# ---------- EXPENSES ----------
@app.route('/api/expenses', methods=['GET', 'POST'])
@login_required
def expenses():
    u = current_user()
    if request.method == 'GET':
        return jsonify([e.to_dict() for e in
                        Expense.query.order_by(Expense.id.desc()).all()])
    if u.role != 'manager':
        return jsonify({'error': 'Manager access required.'}), 403
    d = request.get_json(force=True, silent=True) or {}
    try:
        amt = float(d.get('amount', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Enter a valid amount.'}), 400
    if not (d.get('name') or '').strip() or amt <= 0:
        return jsonify({'error': 'Enter name and valid amount.'}), 400
    e = Expense(name=d['name'].strip(),
                category=(d.get('category') or 'other').strip(),
                amount=amt, date=(d.get('date') or today_str()),
                description=(d.get('description') or '').strip(),
                recorded_by_name=u.full_name)
    db.session.add(e)
    db.session.commit()
    log_action(u.id, u.username, 'Expense recorded',
               f"{e.name} = {amt}")
    return jsonify({'message': 'Expense recorded.',
                    'expense': e.to_dict()}), 201


@app.route('/api/expenses/<int:eid>', methods=['DELETE'])
@manager_required
def del_expense(eid):
    u = current_user()
    e = Expense.query.get_or_404(eid)
    db.session.delete(e)
    db.session.commit()
    log_action(u.id, u.username, 'Expense deleted', e.name)
    return jsonify({'message': 'Expense deleted.'})


# ---------- NOTIFICATIONS / ACTIVITY / REPORTS / SETTINGS ----------
@app.route('/api/notifications', methods=['GET'])
@login_required
def list_notifs():
    u = current_user()
    items = Notification.query.order_by(Notification.id.desc()).limit(100).all()
    out = []
    for n in items:
        if n.user_id and n.user_id != u.id:
            if not (u.role == 'manager' and n.target_role == 'manager'):
                continue
        elif n.target_role and n.target_role not in ('all', u.role):
            if not (u.role == 'manager' and n.target_role == 'manager'):
                continue
        out.append(n.to_dict())
    return jsonify(out[:50])


@app.route('/api/notifications/send', methods=['POST'])
@manager_required
def send_notif():
    u = current_user()
    d = request.get_json(force=True, silent=True) or {}
    title = (d.get('title') or '').strip()
    msg = (d.get('message') or '').strip()
    if not title or not msg:
        return jsonify({'error': 'Enter title and message.'}), 400
    uid = d.get('user_id')
    try:
        uid = int(uid) if uid else None
    except (TypeError, ValueError):
        uid = None
    notify(uid, d.get('target_role') or 'worker', title, msg)
    log_action(u.id, u.username, 'Notification sent', title)
    return jsonify({'message': 'Notification sent.'}), 201


@app.route('/api/notifications/<int:nid>/read', methods=['POST'])
@login_required
def read_notif(nid):
    n = Notification.query.get_or_404(nid)
    n.is_read = True
    db.session.commit()
    return jsonify({'message': 'Marked read.'})


@app.route('/api/activity', methods=['GET'])
@manager_required
def activity():
    items = ActivityLog.query.order_by(ActivityLog.id.desc()).limit(200).all()
    return jsonify([a.to_dict() for a in items])


@app.route('/api/reports/<kind>', methods=['GET'])
@manager_required
def reports(kind):
    if kind == 'sales':
        return jsonify([s.to_dict() for s in
                        Sale.query.order_by(Sale.id.desc()).all()])
    if kind == 'inventory':
        return inventory()
    if kind == 'revenue':
        rev = sum(s.total or 0 for s in Sale.query.all())
        exp = sum(e.amount or 0 for e in Expense.query.all())
        return jsonify({'revenue': round(rev, 2),
                        'expenses': round(exp, 2),
                        'profit': round(rev - exp, 2),
                        'sales': [s.to_dict() for s in
                                  Sale.query.order_by(Sale.id.desc()).all()],
                        'expenses_list': [e.to_dict() for e in
                                          Expense.query.order_by(
                                              Expense.id.desc()).all()]})
    if kind == 'workers':
        out = []
        for u in User.query.filter_by(role='worker').all():
            out.append({'worker': u.full_name, 'username': u.username,
                        'submissions': Product.query.filter_by(
                            worker_id=u.id).count(),
                        'sales': Sale.query.filter_by(worker_id=u.id).count(),
                        'revenue': round(sum(s.total or 0 for s in
                                             Sale.query.filter_by(
                                                 worker_id=u.id).all()), 2),
                        'reports': FarmReport.query.filter_by(
                            worker_id=u.id).count()})
        return jsonify(out)
    return jsonify({'error': 'Unknown report.'}), 400


@app.route('/api/settings', methods=['GET', 'PUT'])
@login_required
def settings():
    if request.method == 'GET':
        return jsonify({s.key: s.value for s in Setting.query.all()})
    u = current_user()
    if u.role != 'manager':
        return jsonify({'error': 'Manager access required.'}), 403
    d = request.get_json(force=True, silent=True) or {}
    for k, v in d.items():
        s = Setting.query.filter_by(key=k).first()
        if not s:
            s = Setting(key=k)
            db.session.add(s)
        s.value = str(v)
    db.session.commit()
    return jsonify({'message': 'Settings saved.'})


# ---------- FARM DASHBOARD (today at a glance + month comparison) ----------

def month_bounds(d):
    """First and last day (date objects) of the month containing day d."""
    first = d.replace(day=1)
    nxt = (first + timedelta(days=32)).replace(day=1)
    return first, nxt - timedelta(days=1)


def sum_reports(rows):
    """Add up the important numbers of a set of reports."""
    keys = ('feed_bags', 'feed_kg', 'birds_fed', 'water_liters',
            'eggs_collected', 'eggs_broken', 'egg_crates', 'crates_sold',
            'chickens_sold', 'birds_died')
    out = {}
    for k in keys:
        out[k] = round(sum((getattr(r, k) or 0) for r in rows), 2)
    out['amount'] = round(sum(((r.amount or 0) or (r.sales_total or 0))
                              for r in rows), 2)
    out['reports'] = len(rows)
    out['workers'] = len({r.worker_id for r in rows if r.worker_id})
    return out


@app.route('/api/dashboard/farm', methods=['GET'])
@manager_required
def dash_farm():
    """Everything the manager needs on one screen: today's numbers, who has
    not reported, this month vs last month and a 30-day chart series."""
    t = datetime.now().date()
    tstr = t.isoformat()
    today_rows = ShiftReport.query.filter_by(date=tstr).all()

    m_start, m_end = month_bounds(t)
    p_end = m_start - timedelta(days=1)
    p_start, p_last = month_bounds(p_end)
    this_rows = ShiftReport.query.filter(
        ShiftReport.date >= m_start.isoformat(),
        ShiftReport.date <= m_end.isoformat()).all()
    last_rows = ShiftReport.query.filter(
        ShiftReport.date >= p_start.isoformat(),
        ShiftReport.date <= p_last.isoformat()).all()

    workers = User.query.filter_by(role='worker', status='active').all()
    sent = {r.worker_id for r in today_rows if r.worker_id}
    missing = [w.full_name for w in workers if w.id not in sent]

    series = []
    for i in range(29, -1, -1):
        d = (t - timedelta(days=i)).isoformat()
        s = sum_reports(ShiftReport.query.filter_by(date=d).all())
        series.append({'date': d, 'amount': s['amount'],
                       'eggs': s['eggs_collected'], 'deaths': s['birds_died']})

    warnings = []
    if missing:
        warnings.append('⏳ %d worker(s) have not sent a report today yet: %s'
                        % (len(missing), ', '.join(missing)))
    deaths_today = sum((r.birds_died or 0) for r in today_rows)
    if deaths_today >= 20:
        warnings.append('☠️ High mortality today: %d birds died — open the '
                        'reports and check the photos.' % deaths_today)
    s_low = Setting.query.filter_by(key='low_stock').first()
    try:
        low = int(float(s_low.value)) if s_low else 10
    except (TypeError, ValueError):
        low = 10
    for p in Product.query.filter_by(status='approved').all():
        if (p.quantity or 0) <= low:
            warnings.append('⚠️ Low stock: %s — only %s left.'
                            % (p.name, p.quantity or 0))

    return jsonify({
        'date': tstr,
        'today': sum_reports(today_rows),
        'workers_total': len(workers),
        'workers_sent': len(sent),
        'missing': missing,
        'month': {'label': m_start.strftime('%B %Y'),
                  'start': m_start.isoformat(), 'end': m_end.isoformat(),
                  'totals': sum_reports(this_rows)},
        'last_month': {'label': p_start.strftime('%B %Y'),
                       'start': p_start.isoformat(), 'end': p_last.isoformat(),
                       'totals': sum_reports(last_rows)},
        'series': series,
        'warnings': warnings[:6],
    })


# ---------- MANAGER RECORDS (the manager's own notebook) ----------

RECORD_CATEGORIES = ['Goods received', 'Money paid out', 'Reminder',
                     'Repair / Work', 'Note']


@app.route('/api/records', methods=['GET', 'POST'])
@manager_required
def manager_records():
    u = current_user()
    if request.method == 'GET':
        rows = ManagerRecord.query.order_by(ManagerRecord.date.desc(),
                                           ManagerRecord.id.desc()).all()
        return jsonify([r.to_dict() for r in rows])
    d = request.get_json(silent=True) or {}
    title = (d.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Please write a title for this record.'}), 400
    rec = ManagerRecord(
        date=((d.get('date') or today_str()) or today_str())[:10],
        category=((d.get('category') or 'Note').strip() or 'Note')[:40],
        title=title[:160],
        note=(d.get('note') or '').strip(),
        amount=to_float(d.get('amount'), 0))
    db.session.add(rec)
    db.session.commit()
    log_action(u.id, u.username, 'manager record added', title[:80])
    return jsonify({'message': 'Record saved.', 'record': rec.to_dict()}), 201


@app.route('/api/records/<int:rid>', methods=['PUT', 'DELETE'])
@manager_required
def manager_record(rid):
    rec = ManagerRecord.query.get(rid)
    if not rec:
        return jsonify({'error': 'Record not found.'}), 404
    if request.method == 'DELETE':
        title = (rec.title or '')[:80]
        db.session.delete(rec)
        db.session.commit()
        log_action(current_user().id, current_user().username,
                   'manager record deleted', title)
        return jsonify({'message': 'Record deleted.'})
    d = request.get_json(silent=True) or {}
    if d.get('title') is not None:
        t = (d.get('title') or '').strip()
        if not t:
            return jsonify({'error': 'Please write a title for this record.'}), 400
        rec.title = t[:160]
    if d.get('date') is not None:
        rec.date = (d.get('date') or '')[:10]
    if d.get('category') is not None:
        rec.category = ((d.get('category') or 'Note').strip() or 'Note')[:40]
    if d.get('note') is not None:
        rec.note = (d.get('note') or '').strip()
    if d.get('amount') is not None:
        rec.amount = to_float(d.get('amount'), 0)
    db.session.commit()
    log_action(current_user().id, current_user().username,
               'manager record edited', (rec.title or '')[:80])
    return jsonify({'message': 'Record updated.', 'record': rec.to_dict()})


# ---------- BACKUP (download a safe copy of the whole database) ----------

@app.route('/api/backup', methods=['GET'])
@manager_required
def backup_db():
    """One-click copy of the whole farm database (reports, workers, records).
    Uses SQLite's safe backup, so it also works while the app is running."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    tmp.close()
    try:
        src = sqlite3.connect(str(DATA_DIR / 'farm.db'))
        dst = sqlite3.connect(tmp.name)
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
    except Exception as e:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        return jsonify({'error': 'Could not build the backup: %s' % e}), 500
    u = current_user()
    name = 'fb_poultry_backup_%s.db' % datetime.now().strftime('%Y-%m-%d_%H%M')
    log_action(u.id, u.username, 'backup downloaded', name)
    return send_file(tmp.name, as_attachment=True, download_name=name,
                     mimetype='application/octet-stream')


# ---------- STATIC FRONTEND ----------
@app.route('/')
def index():
    return send_from_directory(str(FRONTEND_DIR), 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    if filename.startswith('api/'):
        return jsonify({'error': 'Not found.'}), 404
    f = FRONTEND_DIR / filename
    if f.is_file():
        return send_from_directory(str(FRONTEND_DIR), filename)
    return send_from_directory(str(FRONTEND_DIR), 'index.html')


def ensure_seed():
    db.create_all()
    ensure_shift_columns()
    if not Category.query.first():
        for name in ['Live Birds', 'Broilers', 'Layers', 'Eggs',
                     'Chicken Meat', 'Chicks', 'Manure', 'Feed', 'Other']:
            db.session.add(Category(name=name))
        db.session.commit()
    if not Setting.query.filter_by(key='farm_name').first():
        db.session.add(Setting(key='farm_name',
                               value='F & B Poultry Farm'))
        db.session.add(Setting(key='low_stock', value='10'))
        db.session.commit()


def ensure_manager():
    """Make sure a manager account exists when MANAGER_PASSWORD is provided.
    On a hosting site every fresh copy of the app starts with an empty
    database, so this is what lets you log in there. Same rules as seed.py:
    the password comes only from the environment, never from this code."""
    if User.query.filter_by(role='manager').first():
        return
    pwd = (os.environ.get('MANAGER_PASSWORD') or '').strip()
    if not pwd:
        return
    mgr = User(
        full_name=(os.environ.get('MANAGER_NAME') or 'Farm Manager').strip() or 'Farm Manager',
        username=(os.environ.get('MANAGER_USERNAME') or 'manager').strip() or 'manager',
        email=(os.environ.get('MANAGER_EMAIL') or 'manager@example.com').strip() or 'manager@example.com',
        phone='0500000000',
        password_hash=bcrypt.generate_password_hash(pwd).decode(),
        role='manager', department='Management', status='active')
    db.session.add(mgr)
    db.session.commit()
    log_action(mgr.id, mgr.username, 'System seeded',
               'Manager account created from environment settings.')


# ---------- CLEAR MESSAGES FOR LOGIN PROBLEMS ----------
# The pages show these words to the user, so they must be helpful instead of
# the old blanket "Something went wrong".
@jwt.expired_token_loader
def _jwt_expired(jwt_header, jwt_payload):
    return jsonify({'error': 'Your login has expired. Please log in again.',
                    'code': 'bad_token'}), 401


@jwt.invalid_token_loader
def _jwt_invalid(reason):
    msg = 'Your login could not be verified. Please log in again.'
    if 'signature' in str(reason).lower():
        msg += (" (If this keeps happening on a hosted copy of the farm app, "
                "set JWT_SECRET in the hosting site's Environment settings - "
                "see README.md.)")
    return jsonify({'error': msg, 'code': 'bad_token'}), 422


@jwt.unauthorized_loader
def _jwt_missing(reason):
    # No login token was sent at all. Say what that means and how to fix it,
    # instead of the bare "Please log in first" that used to show up even for
    # a manager who had just signed in.
    return jsonify({'error':
        'No login was sent with this request. Please log in and try again.',
        'code': 'no_login'}), 401


@jwt.revoked_token_loader
def _jwt_revoked(jwt_header, jwt_payload):
    return jsonify({'error': 'This login is no longer valid. Please log in again.'}), 401


# ---------- FRIENDLY ERRORS (JSON for the app, never a bare HTML error page) ----------
@app.errorhandler(404)
def _err_404(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found.'}), 404
    return send_from_directory(str(FRONTEND_DIR), 'index.html')


@app.errorhandler(405)
def _err_405(e):
    if request.path.startswith('/api/'):
        return jsonify({'error': 'That action is not allowed here.'}), 405
    return send_from_directory(str(FRONTEND_DIR), 'index.html')


@app.errorhandler(500)
def _err_500(e):
    try:
        db.session.rollback()
    except Exception:
        pass
    if request.path.startswith('/api/'):
        return jsonify({'error':
            'The server hit a problem while doing that. Please try again in '
            'a moment.'}), 500
    return 'The server hit a problem. Please reload the page.', 500


# When the app is served online (gunicorn / a hosting provider) the __main__
# block below never runs, so make sure the database and its default rows exist.
with app.app_context():
    try:
        ensure_seed()
        ensure_manager()
    except Exception as _exc:            # never block the app from starting
        print('Could not prepare the database:', _exc)


if __name__ == '__main__':
    # Kill any previous farm server so only ONE copy ever runs.
    # (Two copies fighting over the same database caused
    #  "sent reports not visible" and pages that never load.)
    pidfile0 = basedir / 'server.pid'
    if pidfile0.exists():
        try:
            old = int(pidfile0.read_text().strip())
            if old != os.getpid():
                os.kill(old, 9)
                print('Stopped old farm server (PID %s).' % old)
        except Exception:
            pass
        try:
            pidfile0.unlink()
        except Exception:
            pass
    with app.app_context():
        ensure_seed()
        ensure_manager()
    pidfile = basedir / 'server.pid'
    try:
        pidfile.write_text(str(os.getpid()))
    except Exception:
        pass
    try:
        _port = int(os.environ.get('PORT') or 5000)
        print(f'F & B Poultry Farm: http://localhost:{_port}')
        app.run(host='0.0.0.0', port=_port)
    finally:
        try:
            pidfile.unlink()
        except Exception:
            pass
