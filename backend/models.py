"""DATABASE MODELS for F & B Poultry Farm Management System."""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='worker')
    department = db.Column(db.String(80), nullable=True, default='General')
    status = db.Column(db.String(20), nullable=False, default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'full_name': self.full_name,
                'username': self.username, 'email': self.email,
                'phone': self.phone, 'role': self.role,
                'department': self.department, 'status': self.status,
                'created_at': self.created_at.isoformat() if self.created_at else None}


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    def to_dict(self):
        return {'id': self.id, 'name': self.name}


class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    category_name = db.Column(db.String(80), nullable=False, default='Other')
    quantity = db.Column(db.Integer, nullable=False, default=0)
    opening_stock = db.Column(db.Integer, nullable=False, default=0)
    unit = db.Column(db.String(30), nullable=False, default='pcs')
    price_per_unit = db.Column(db.Float, nullable=False, default=0)
    description = db.Column(db.Text, nullable=True)
    farm_section = db.Column(db.String(80), nullable=True, default='Main')
    image_path = db.Column(db.String(250), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    worker_name = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending')
    date_available = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        qty = self.quantity or 0
        price = self.price_per_unit or 0
        return {'id': self.id, 'name': self.name,
                'category_id': self.category_id,
                'category': self.category_name,
                'category_name': self.category_name,
                'quantity': qty, 'opening_stock': self.opening_stock,
                'unit': self.unit, 'price_per_unit': price,
                'total_value': round(qty * price, 2),
                'description': self.description,
                'farm_section': self.farm_section,
                'notes': self.notes, 'worker_id': self.worker_id,
                'worker_name': self.worker_name, 'status': self.status,
                'date_available': self.date_available,
                'created_at': self.created_at.isoformat() if self.created_at else None}


class InventoryTransaction(db.Model):
    __tablename__ = 'inventory_transactions'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(120), nullable=True)
    type = db.Column(db.String(20), nullable=False)
    quantity_change = db.Column(db.Integer, nullable=False)
    resulting_stock = db.Column(db.Integer, nullable=False)
    reference = db.Column(db.String(120), nullable=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    worker_name = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'product_id': self.product_id,
                'product_name': self.product_name, 'type': self.type,
                'quantity_change': self.quantity_change,
                'resulting_stock': self.resulting_stock,
                'reference': self.reference,
                'worker_name': self.worker_name,
                'created_at': self.created_at.isoformat() if self.created_at else None}

    description = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {'id': self.id, 'name': self.name,
                'description': self.description}



class Sale(db.Model):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(120), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    price_per_unit = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(30), nullable=True)
    payment_method = db.Column(db.String(30), nullable=False, default='cash')
    date = db.Column(db.String(20), nullable=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    worker_name = db.Column(db.String(120), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'product_id': self.product_id,
                'product_name': self.product_name, 'quantity': self.quantity,
                'price_per_unit': self.price_per_unit, 'total': self.total,
                'customer_name': self.customer_name,
                'customer_phone': self.customer_phone,
                'payment_method': self.payment_method, 'date': self.date,
                'worker_name': self.worker_name,
                'notes': self.notes,
                'created_at': self.created_at.isoformat() if self.created_at else None}


class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    location = db.Column(db.String(150), nullable=True)
    total_orders = db.Column(db.Integer, default=0)
    total_spent = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'name': self.name, 'phone': self.phone,
                'location': self.location, 'total_orders': self.total_orders,
                'total_spent': self.total_spent,
                'created_at': self.created_at.isoformat() if self.created_at else None}


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    product_name = db.Column(db.String(120), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    delivery_option = db.Column(db.String(20), default='pickup')
    delivery_location = db.Column(db.String(200), nullable=True)
    preferred_date = db.Column(db.String(20), nullable=True)
    payment_method = db.Column(db.String(30), default='cash')
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'customer_name': self.customer_name,
                'phone': self.phone, 'product_id': self.product_id,
                'product_name': self.product_name, 'quantity': self.quantity,
                'delivery_option': self.delivery_option,
                'delivery_location': self.delivery_location,
                'preferred_date': self.preferred_date,
                'payment_method': self.payment_method,
                'notes': self.notes, 'status': self.status,
                'created_at': self.created_at.isoformat() if self.created_at else None}



class DamageReport(db.Model):
    __tablename__ = 'damage_reports'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    product_name = db.Column(db.String(120), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(20), nullable=True)
    reason = db.Column(db.String(200), nullable=True)
    farm_section = db.Column(db.String(80), nullable=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    worker_name = db.Column(db.String(120), nullable=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'product_id': self.product_id,
                'product_name': self.product_name,
                'quantity': self.quantity, 'date': self.date,
                'reason': self.reason, 'farm_section': self.farm_section,
                'worker_name': self.worker_name,
                'description': self.description, 'status': self.status,
                'created_at': self.created_at.isoformat() if self.created_at else None}


class FarmReport(db.Model):
    __tablename__ = 'farm_reports'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    worker_name = db.Column(db.String(120), nullable=True)
    farm_section = db.Column(db.String(80), nullable=True)
    num_birds = db.Column(db.Integer, default=0)
    feed_used = db.Column(db.String(80), nullable=True)
    eggs_collected = db.Column(db.Integer, default=0)
    birds_sold = db.Column(db.Integer, default=0)
    birds_died = db.Column(db.Integer, default=0)
    problems = db.Column(db.Text, nullable=True)
    observations = db.Column(db.Text, nullable=True)
    recommendations = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'date': self.date,
                'worker_name': self.worker_name,
                'farm_section': self.farm_section,
                'num_birds': self.num_birds, 'feed_used': self.feed_used,
                'eggs_collected': self.eggs_collected,
                'birds_sold': self.birds_sold, 'birds_died': self.birds_died,
                'problems': self.problems, 'observations': self.observations,
                'recommendations': self.recommendations,
                'created_at': self.created_at.isoformat() if self.created_at else None}


class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='other')
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(20), nullable=True)
    description = db.Column(db.Text, nullable=True)
    recorded_by_name = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'name': self.name,
                'category': self.category, 'amount': self.amount,
                'date': self.date, 'description': self.description,
                'recorded_by_name': self.recorded_by_name,
                'created_at': self.created_at.isoformat() if self.created_at else None}


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    target_role = db.Column(db.String(20), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'user_id': self.user_id,
                'target_role': self.target_role, 'title': self.title,
                'message': self.message, 'is_read': self.is_read,
                'created_at': self.created_at.isoformat() if self.created_at else None}


class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    username = db.Column(db.String(80), nullable=True)
    action = db.Column(db.String(200), nullable=False)
    detail = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        ts = self.timestamp
        return {'id': self.id, 'user_id': self.user_id,
                'username': self.username, 'action': self.action,
                'detail': self.detail,
                'date': ts.strftime('%Y-%m-%d') if ts else None,
                'time': ts.strftime('%H:%M:%S') if ts else None,
                'timestamp': ts.isoformat() if ts else None}


class Setting(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(80), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {'id': self.id, 'key': self.key, 'value': self.value}


class ShiftReport(db.Model):
    """One report per day per worker (the whole day, not per shift).

    Captures eggs, chickens, mortality, feeding, water, the total amount
    received plus auto-linked sales lines (stored as Sale rows; their ids
    are kept in sale_ids)."""
    __tablename__ = 'shift_reports'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=True)
    shift = db.Column(db.String(20), nullable=False, default='morning')
    worker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    worker_name = db.Column(db.String(120), nullable=True)
    farm_section = db.Column(db.String(80), nullable=True, default='Main')
    feed_done = db.Column(db.Boolean, default=False)
    feed_qty = db.Column(db.String(120), nullable=True)
    feed_bags = db.Column(db.Float, default=0)
    feed_kg = db.Column(db.Float, default=0)
    birds_fed = db.Column(db.Integer, default=0)
    water_done = db.Column(db.Boolean, default=False)
    water_liters = db.Column(db.Float, default=0)
    water_notes = db.Column(db.String(250), nullable=True)
    eggs_collected = db.Column(db.Integer, default=0)
    eggs_broken = db.Column(db.Integer, default=0)
    egg_crates = db.Column(db.Integer, default=0)
    chickens_sold = db.Column(db.Integer, default=0)
    crates_sold = db.Column(db.Integer, default=0)
    birds_died = db.Column(db.Integer, default=0)
    death_reason = db.Column(db.String(250), nullable=True)
    death_image = db.Column(db.String(250), nullable=True)
    sale_ids = db.Column(db.String(250), nullable=True)
    sales_summary = db.Column(db.Text, nullable=True)
    sales_total = db.Column(db.Float, default=0)
    amount = db.Column(db.Float, default=0)
    seen_by_manager = db.Column(db.Boolean, default=False)
    manager_comment = db.Column(db.Text, nullable=True)
    problems = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'date': self.date, 'shift': self.shift,
                'worker_id': self.worker_id, 'worker_name': self.worker_name,
                'farm_section': self.farm_section,
                'feed_done': bool(self.feed_done), 'feed_qty': self.feed_qty,
                'feed_bags': self.feed_bags or 0, 'feed_kg': self.feed_kg or 0,
                'birds_fed': self.birds_fed or 0,
                'water_done': bool(self.water_done),
                'water_liters': self.water_liters or 0,
                'water_notes': self.water_notes,
                'eggs_collected': self.eggs_collected or 0,
                'eggs_broken': self.eggs_broken or 0,
                'egg_crates': self.egg_crates or 0,
                'chickens_sold': self.chickens_sold or 0,
                'crates_sold': self.crates_sold or 0,
                'birds_died': self.birds_died or 0,
                'death_reason': self.death_reason,
                'death_image': self.death_image,
                'sale_ids': self.sale_ids, 'sales_summary': self.sales_summary,
                'sales_total': self.sales_total or 0,
                'amount': self.amount or 0,
                'seen_by_manager': bool(self.seen_by_manager),
                'manager_comment': self.manager_comment,
                'problems': self.problems, 'notes': self.notes,
                'created_at': self.created_at.isoformat() if self.created_at else None}
class ManagerRecord(db.Model):
    """A free-text record kept by the manager (his own notebook).

    Examples: goods received, feed bought, money paid out, reminders,
    observations in the poultry house. Only the manager can read/write them.
    """
    __tablename__ = 'manager_records'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20), nullable=True)
    category = db.Column(db.String(40), nullable=True, default='Note')
    title = db.Column(db.String(160), nullable=False)
    note = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'date': self.date,
                'category': self.category or 'Note',
                'title': self.title, 'note': self.note,
                'amount': self.amount or 0,
                'created_at': self.created_at.isoformat() if self.created_at else None}
