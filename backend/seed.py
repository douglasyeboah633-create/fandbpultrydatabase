"""Seed demo data. Run: python seed.py"""
import os

from app import app, db, bcrypt, ensure_seed, today_str, notify, to_float, to_int
from models import (User, Category, Product, InventoryTransaction, Sale,
                    DamageReport, FarmReport, ShiftReport,
                    Expense, ActivityLog)

with app.app_context():
    ensure_seed()
    # Importing app already created the manager (ensure_manager) when
    # MANAGER_PASSWORD is set, so only demo data can mean "already seeded".
    if Product.query.first() or User.query.filter_by(role='worker').first():
        print('Already seeded. Delete farm.db to re-seed.')
        raise SystemExit
    # The manager account is built from environment variables, so that no real
    # password is ever kept in this code (the project is public on GitHub).
    # Locally they come from backend/.env; when hosting, set them in the
    # provider's environment settings.
    mgr = User.query.filter_by(role='manager').first()
    if not mgr:
        mgr_name = os.environ.get('MANAGER_NAME', 'Farm Manager').strip()
        mgr_username = os.environ.get('MANAGER_USERNAME', 'manager').strip()
        mgr_email = os.environ.get('MANAGER_EMAIL', 'manager@example.com').strip()
        mgr_password = os.environ.get('MANAGER_PASSWORD', '')
        if not mgr_password:
            raise SystemExit('Missing MANAGER_PASSWORD. Copy backend/.env.example '
                             'to backend/.env and set MANAGER_PASSWORD first '
                             '(on Render, set it under Environment instead).')
        mgr = User(full_name=mgr_name, username=mgr_username,
                   email=mgr_email, phone='0500000000',
                   password_hash=bcrypt.generate_password_hash(
                       mgr_password).decode(), role='manager',
                   department='Management', status='active')
        db.session.add(mgr)
    # Demo workers get a random one-time password each (printed once).
    # Change them after logging in as the manager.
    import secrets as _secrets
    _w1pw = _secrets.token_urlsafe(10)
    _w2pw = _secrets.token_urlsafe(10)
    print('Demo worker passwords (one-time, change them now): '
          'worker1 / %s, worker2 / %s' % (_w1pw, _w2pw))
    w1 = User(full_name='Kwame Mensah', username='worker1',
              email='worker1@fbpoultry.local', phone='0501111111',
              password_hash=bcrypt.generate_password_hash(
                  _w1pw).decode(), role='worker',
              department='Layer Section', status='active')
    w2 = User(full_name='Ama Serwaa', username='worker2',
              email='worker2@fbpoultry.local', phone='0502222222',
              password_hash=bcrypt.generate_password_hash(
                  _w2pw).decode(), role='worker',
              department='Broiler Section', status='active')
    db.session.add_all([mgr, w1, w2])
    db.session.commit()
    items = [
        ('Broiler Chicken', 'Broilers', 500, 'pcs', 85.0, w1),
        ('Layer Chicken', 'Layers', 300, 'pcs', 95.0, w1),
        ('Fresh Eggs (Crate of 30)', 'Eggs', 120, 'crates', 55.0, w2),
        ('Day-old Chicks', 'Chicks', 1000, 'pcs', 12.0, w2),
        ('Chicken Manure (Bag)', 'Manure', 80, 'bags', 25.0, w1),
    ]
    for name, cat, qty, unit, price, w in items:
        p = Product(name=name, category_name=cat, quantity=qty,
                    opening_stock=qty, unit=unit, price_per_unit=price,
                    description=f'Quality {name.lower()} from F & B farm.',
                    farm_section='Main', worker_id=w.id,
                    worker_name=w.full_name, status='approved',
                    date_available=today_str())
        db.session.add(p)
        db.session.commit()
        db.session.add(InventoryTransaction(
            product_id=p.id, product_name=p.name, type='opening',
            quantity_change=qty, resulting_stock=qty,
            reference='Opening stock', worker_id=w.id,
            worker_name=w.full_name))
    prods = Product.query.all()
    s1 = Sale(product_id=prods[0].id, product_name=prods[0].name,
              quantity=100, price_per_unit=85.0, total=8500.0,
              customer_name='Daily walk-in sales', customer_phone='',
              payment_method='mobile_money', date=today_str(),
              worker_id=w1.id, worker_name=w1.full_name)
    prods[0].quantity -= 100
    s2 = Sale(product_id=prods[2].id, product_name=prods[2].name,
              quantity=20, price_per_unit=55.0, total=1100.0,
              customer_name='Daily walk-in sales', customer_phone='',
              payment_method='cash', date=today_str(),
              worker_id=w2.id, worker_name=w2.full_name)
    prods[2].quantity -= 20
    db.session.add_all([s1, s2])
    db.session.add(DamageReport(product_name='Broiler Chicken',
                                quantity=10, date=today_str(),
                                reason='Disease', farm_section='Broiler Pen A',
                                worker_id=w1.id, worker_name=w1.full_name,
                                description='10 birds found dead in morning.',
                                status='pending'))
    prods[0].quantity -= 0
    db.session.add(FarmReport(date=today_str(), worker_id=w1.id,
                              worker_name=w1.full_name,
                              farm_section='Layer Pen B', num_birds=290,
                              feed_used='3 bags', eggs_collected=250,
                              birds_sold=5, birds_died=2,
                              problems='One drinker leaking.',
                              observations='Birds active and feeding well.',
                              recommendations='Replace drinker valve.'))
    db.session.add(Expense(name='Layer feed (10 bags)', category='feed',
                           amount=2500.0, date=today_str(),
                           description='Starter feed',
                           recorded_by_name='Farm Manager'))
    db.session.add(Expense(name='Vaccination', category='medication',
                           amount=800.0, date=today_str(),
                           description='Newcastle vaccine',
                           recorded_by_name='Farm Manager'))
    db.session.commit()
    db.session.add(ActivityLog(user_id=mgr.id, username='admin',
                               action='System seeded',
                               detail='Demo data created.'))
    db.session.commit()
    # demo shift reports (morning + afternoon) for today
    from app import record_sale_for_shift as _sr_sale
    for shift, feed_qty, water, eggs, broken, items, died, reason in [
            ('morning', '3 bags', True, 250, 3,
             [('Broiler Chicken', 12)], 1, 'Heat stress'),
            ('afternoon', '2 bags', True, 180, 0,
             [('Fresh Eggs (Crate of 30)', 5)], 0, None)]:
        made = []
        stot = 0.0
        for pname, qty in items:
            pp = Product.query.filter_by(name=pname).first()
            _p, _s, _t = _sr_sale(w1, pp.id, qty, today_str(), 'cash')
            _s.notes = 'Shift: %s' % shift
            made.append((_p, qty, _s))
            stot = round(stot + _t, 2)
        db.session.add(ShiftReport(
            date=today_str(), shift=shift, worker_id=w1.id,
            worker_name=w1.full_name, farm_section='Layer Pen B',
            feed_done=True, feed_qty=feed_qty, birds_fed=290,
            water_done=water, water_notes='Drinkers topped up.',
            eggs_collected=eggs, eggs_broken=broken, birds_died=died,
            death_reason=reason if died else None,
            sale_ids=','.join(str(_s.id) for _, _, _s in made) or None,
            sales_summary=', '.join('%s x%s' % (_p.name, _q)
                                    for _p, _q, _ in made) or None,
            sales_total=stot,
            problems='One drinker leaking.' if shift == 'morning' else None,
            notes='Demo shift data.' if shift == 'morning' else None,
            feed_bags=3.0 if shift == 'morning' else 2.0,
            feed_kg=150.0 if shift == 'morning' else 100.0,
            water_liters=200.0 if shift == 'morning' else 120.0,
            egg_crates=8 if shift == 'morning' else 0,
            chickens_sold=12 if shift == 'morning' else 0,
            crates_sold=5 if shift == 'afternoon' else 0))
    db.session.commit()
    notify(None, 'manager', 'Welcome',
           'Demo data loaded. Review pending items.')
    print('Seeded! manager username: %s (set your own MANAGER_PASSWORD) '
          'Demo workers: worker1 and worker2 with one-time passwords shown above -- change them now.' % mgr.username)
