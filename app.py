from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, g
import sqlite3
import joblib
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from functools import wraps
import os  # Added for file existence check

app = Flask(__name__)
app.secret_key = 'smart-pharma-assistant-secret-key-2024'

# Load ML model
try:
    model_path = 'models/symptom_model.joblib'
    if os.path.exists(model_path):
        symptom_model = joblib.load(model_path)
        print("✅ ML Model loaded successfully")
    else:
        print("⚠️  ML Model file not found. Please run train_model.py first")
        symptom_model = None
except Exception as e:
    print(f"⚠️  Error loading ML model: {str(e)}")
    symptom_model = None

# Database helper
def get_db():
    conn = sqlite3.connect('pharma.db')
    conn.row_factory = sqlite3.Row
    return conn

# Create tables if they don't exist
def init_database():
    try:
        db = get_db()
        # Check if tables exist
        db.execute('SELECT 1 FROM users LIMIT 1')
        db.close()
    except sqlite3.OperationalError:
        # Tables don't exist, create them
        print("Database tables not found. Running initialization...")
        import subprocess
        subprocess.run(['python', 'init_db.py'])

# Initialize database on startup
init_database()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Before each request - add unread alerts count to g
@app.before_request
def before_request():
    if 'user_id' in session:
        db = get_db()
        unread_alerts = db.execute('SELECT COUNT(*) as count FROM alerts WHERE is_read = 0').fetchone()['count']
        g.unread_alerts_count = unread_alerts
        db.close()

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('❌ Please fill all fields', 'danger')
            return redirect(url_for('login'))
        
        try:
            db = get_db()
            user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
            db.close()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash('✅ Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('❌ Invalid username or password', 'danger')
        except Exception as e:
            flash(f'❌ Database error: {str(e)}', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('👋 Logged out successfully', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        db = get_db()
        
        # Get statistics with error handling
        stats = {
            'medicines': db.execute('SELECT COUNT(*) FROM medicines').fetchone()[0] or 0,
            'batches': db.execute('SELECT COUNT(*) FROM batches').fetchone()[0] or 0,
            'sales': db.execute('SELECT SUM(quantity_sold) FROM sales').fetchone()[0] or 0,
            'revenue': db.execute('SELECT SUM(quantity_sold * selling_price) FROM sales').fetchone()[0] or 0,
        }
        
        # Near expiry batches (within 15 days)
        threshold = (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d')
        near_expiry = db.execute('''
            SELECT COUNT(*) FROM batches 
            WHERE expiry_date <= ? AND expiry_date >= DATE('now')
        ''', (threshold,)).fetchone()[0] or 0
        
        # Expired batches
        expired = db.execute('SELECT COUNT(*) FROM batches WHERE expiry_date < DATE("now")').fetchone()[0] or 0
        
        db.close()
        
        # Get current date and time
        now = datetime.now()
        
        return render_template('dashboard.html',
                             stats=stats,
                             near_expiry=near_expiry,
                             expired=expired,
                             username=session['username'],
                             current_date=now,
                             current_time=now)
    except Exception as e:
        flash(f'❌ Error loading dashboard: {str(e)}', 'danger')
        return redirect(url_for('login'))

@app.route('/medicines')
@login_required
def view_medicines():
    try:
        db = get_db()
        medicines = db.execute('SELECT * FROM medicines ORDER BY name').fetchall()
        db.close()
        return render_template('view_medicines.html', medicines=medicines)
    except Exception as e:
        flash(f'❌ Error loading medicines: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/medicine/add', methods=['GET', 'POST'])
@login_required
def add_medicine():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            composition = request.form.get('composition', '').strip()
            uses = request.form.get('uses', '').strip()
            dosage = request.form.get('dosage', '').strip()
            side_effects = request.form.get('side_effects', '').strip()
            category = request.form.get('category', '').strip()
            
            if not name:
                flash('❌ Medicine name is required', 'danger')
                return redirect(url_for('add_medicine'))
            
            db = get_db()
            db.execute('''
                INSERT INTO medicines (name, composition, uses, dosage, side_effects, category)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, composition, uses, dosage, side_effects, category))
            db.commit()
            db.close()
            
            flash(f'✅ Medicine "{name}" added successfully!', 'success')
            return redirect(url_for('view_medicines'))
        except Exception as e:
            flash(f'❌ Error adding medicine: {str(e)}', 'danger')
            return redirect(url_for('add_medicine'))
    
    return render_template('add_medicine.html')

@app.route('/medicine/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_medicine(id):
    try:
        db = get_db()
        
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            composition = request.form.get('composition', '').strip()
            uses = request.form.get('uses', '').strip()
            dosage = request.form.get('dosage', '').strip()
            side_effects = request.form.get('side_effects', '').strip()
            category = request.form.get('category', '').strip()
            
            if not name:
                flash('❌ Medicine name is required', 'danger')
                return redirect(url_for('edit_medicine', id=id))
            
            db.execute('''
                UPDATE medicines 
                SET name = ?, composition = ?, uses = ?, dosage = ?, 
                    side_effects = ?, category = ?
                WHERE id = ?
            ''', (name, composition, uses, dosage, side_effects, category, id))
            db.commit()
            
            flash(f'✅ Medicine "{name}" updated successfully!', 'success')
            return redirect(url_for('view_medicines'))
        
        # GET request: load medicine data
        medicine = db.execute('SELECT * FROM medicines WHERE id = ?', (id,)).fetchone()
        
        # Get batch statistics
        batch_stats = db.execute('''
            SELECT 
                COUNT(*) as batches_count,
                SUM(quantity) as total_quantity,
                COUNT(CASE WHEN expiry_date BETWEEN DATE('now') AND DATE('now', '+15 days') THEN 1 END) as near_expiry_count
            FROM batches 
            WHERE medicine_id = ?
        ''', (id,)).fetchone()
        
        db.close()
        
        if not medicine:
            flash('❌ Medicine not found', 'danger')
            return redirect(url_for('view_medicines'))
        
        return render_template('edit_medicine.html',
                             medicine=medicine,
                             batches_count=batch_stats['batches_count'] or 0,
                             total_quantity=batch_stats['total_quantity'] or 0,
                             near_expiry_count=batch_stats['near_expiry_count'] or 0)
    
    except Exception as e:
        flash(f'❌ Error editing medicine: {str(e)}', 'danger')
        return redirect(url_for('view_medicines'))

@app.route('/medicine/delete/<int:id>')
@login_required
def delete_medicine(id):
    try:
        db = get_db()
        
        # Get medicine name for flash message
        medicine = db.execute('SELECT name FROM medicines WHERE id = ?', (id,)).fetchone()
        
        # Delete medicine (cascade will delete associated batches)
        db.execute('DELETE FROM medicines WHERE id = ?', (id,))
        db.commit()
        db.close()
        
        if medicine:
            flash(f'✅ Medicine "{medicine["name"]}" deleted successfully!', 'success')
        else:
            flash('✅ Medicine deleted successfully!', 'success')
        
        return redirect(url_for('view_medicines'))
    
    except Exception as e:
        flash(f'❌ Error deleting medicine: {str(e)}', 'danger')
        return redirect(url_for('view_medicines'))

@app.route('/medicine/details/<int:id>')
@login_required
def medicine_details(id):
    """View detailed information about a specific medicine"""
    try:
        db = get_db()
        
        # Get medicine details
        medicine = db.execute('''
            SELECT * FROM medicines 
            WHERE id = ?
        ''', (id,)).fetchone()
        
        if not medicine:
            flash('❌ Medicine not found', 'danger')
            return redirect(url_for('view_medicines'))
        
        # Get all batches for this medicine
        batches = db.execute('''
            SELECT * FROM batches 
            WHERE medicine_id = ?
            ORDER BY expiry_date
        ''', (id,)).fetchall()
        
        # Get recent sales for this medicine
        recent_sales = db.execute('''
            SELECT s.*, b.batch_no, s.sold_on
            FROM sales s
            JOIN batches b ON s.batch_id = b.id
            WHERE b.medicine_id = ?
            ORDER BY s.sold_on DESC
            LIMIT 10
        ''', (id,)).fetchall()
        
        # Calculate statistics
        total_stock = sum([batch['quantity'] for batch in batches])
        total_value = sum([batch['quantity'] * batch['mrp'] for batch in batches])
        
        # Count expiry status
        today = datetime.now().date()
        expired = 0
        near_expiry = 0
        
        for batch in batches:
            try:
                expiry_date = datetime.strptime(batch['expiry_date'], '%Y-%m-%d').date()
                if expiry_date < today:
                    expired += 1
                elif today <= expiry_date <= today + timedelta(days=15):
                    near_expiry += 1
            except:
                continue
        
        db.close()
        
        return render_template('medicine_details.html',
                             medicine=medicine,
                             batches=batches,
                             recent_sales=recent_sales,
                             total_stock=total_stock,
                             total_value=total_value,
                             expired=expired,
                             near_expiry=near_expiry)
        
    except Exception as e:
        flash(f'❌ Error loading medicine details: {str(e)}', 'danger')
        return redirect(url_for('view_medicines'))

@app.route('/medicine/details/by_name/<name>')
@login_required
def medicine_details_by_name(name):
    """View medicine details by name (for AI recommendations)"""
    try:
        db = get_db()
        
        # Get medicine details by name
        medicine = db.execute('''
            SELECT * FROM medicines 
            WHERE name = ?
        ''', (name,)).fetchone()
        
        db.close()
        
        if not medicine:
            flash(f'❌ Medicine "{name}" not found in database', 'danger')
            return redirect(url_for('view_medicines'))
        
        # Redirect to the ID-based details page
        return redirect(url_for('medicine_details', id=medicine['id']))
        
    except Exception as e:
        flash(f'❌ Error loading medicine details: {str(e)}', 'danger')
        return redirect(url_for('view_medicines'))

@app.route('/batch/add', methods=['GET', 'POST'])
@login_required
def add_batch():
    try:
        db = get_db()
        
        if request.method == 'POST':
            try:
                medicine_id = request.form.get('medicine_id')
                batch_no = request.form.get('batch_no', '').strip()
                quantity = request.form.get('quantity', '0')
                mrp = request.form.get('mrp', '0.0')
                cost_price = request.form.get('cost_price', '0.0')
                mfg_date = request.form.get('mfg_date')
                expiry_date = request.form.get('expiry_date')
                supplier = request.form.get('supplier', '').strip()
                
                if not batch_no or not medicine_id:
                    flash('❌ Batch number and medicine are required', 'danger')
                    return redirect(url_for('add_batch'))
                
                db.execute('''
                    INSERT INTO batches (medicine_id, batch_no, quantity, mrp, cost_price, mfg_date, expiry_date, supplier)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (medicine_id, batch_no, int(quantity), float(mrp), float(cost_price), mfg_date, expiry_date, supplier))
                db.commit()
                db.close()
                
                flash(f'✅ Batch "{batch_no}" added successfully!', 'success')
                return redirect(url_for('view_medicines'))
            except ValueError:
                flash('❌ Invalid numeric values', 'danger')
                return redirect(url_for('add_batch'))
            except Exception as e:
                flash(f'❌ Error adding batch: {str(e)}', 'danger')
                return redirect(url_for('add_batch'))
        
        medicines = db.execute('SELECT id, name FROM medicines ORDER BY name').fetchall()
        db.close()
        return render_template('add_batch.html', medicines=medicines)
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/view_batches')
@login_required
def view_batches():
    try:
        db = get_db()
        batches = db.execute('''
            SELECT b.*, m.name as medicine_name 
            FROM batches b 
            JOIN medicines m ON b.medicine_id = m.id 
            ORDER BY b.expiry_date
        ''').fetchall()
        db.close()
        return render_template('view_batches.html', batches=batches)
    except Exception as e:
        flash(f'❌ Error loading batches: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/sell', methods=['GET', 'POST'])
@login_required
def sell_medicine():
    try:
        db = get_db()
        now = datetime.now()
        
        # Generate receipt number
        last_sale = db.execute('SELECT MAX(id) as last_id FROM sales').fetchone()
        receipt_number = (last_sale['last_id'] or 0) + 1
        
        if request.method == 'POST':
            # Get data from form
            customer_name = request.form.get('customer_name', '').strip()
            customer_phone = request.form.get('customer_phone', '').strip()
            customer_age = request.form.get('customer_age')
            prescription_number = request.form.get('prescription_number', '').strip()
            doctor_name = request.form.get('doctor_name', '').strip()
            diagnosis = request.form.get('diagnosis', '').strip()
            payment_method = request.form.get('payment_method', 'cash')
            
            # Get cart data from form
            medicine_ids = request.form.getlist('medicine_id[]')
            batch_ids = request.form.getlist('batch_id[]')
            quantities = request.form.getlist('quantity[]')
            prices = request.form.getlist('price[]')
            
            if not customer_name or not customer_phone:
                flash('❌ Customer name and phone are required', 'danger')
                return redirect(url_for('sell_medicine'))
            
            if not medicine_ids:
                flash('❌ Please add medicines to cart', 'danger')
                return redirect(url_for('sell_medicine'))
            
            # Process each item in cart
            for i in range(len(medicine_ids)):
                medicine_id = medicine_ids[i]
                batch_id = batch_ids[i]
                quantity = int(quantities[i])
                price = float(prices[i])
                
                # Check stock availability
                batch = db.execute('SELECT quantity FROM batches WHERE id = ?', 
                                  (batch_id,)).fetchone()
                
                if not batch or batch['quantity'] < quantity:
                    flash(f'❌ Insufficient stock for medicine ID: {medicine_id}', 'danger')
                    return redirect(url_for('sell_medicine'))
                
                # Update stock
                new_quantity = batch['quantity'] - quantity
                db.execute('UPDATE batches SET quantity = ? WHERE id = ?', 
                          (new_quantity, batch_id))
                
                # Record sale
                db.execute('''
                    INSERT INTO sales 
                    (batch_id, quantity_sold, selling_price, customer_name, customer_phone, 
                     customer_age, prescription_number, doctor_name, diagnosis, sold_on)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    batch_id, quantity, price,
                    customer_name, customer_phone, customer_age,
                    prescription_number, doctor_name, diagnosis, now.isoformat()
                ))
            
            db.commit()
            
            # Generate receipt
            receipt_number = db.execute('SELECT last_insert_rowid()').fetchone()[0]
            
            flash(f'✅ Sale processed successfully! Receipt #: {receipt_number}', 'success')
            return redirect(url_for('sell_medicine'))
        
        # GET request: load available medicines
        medicines = db.execute('''
            SELECT m.id, m.name, m.category, m.composition,
                   b.id as batch_id, b.batch_no, b.quantity, b.mrp, b.expiry_date
            FROM medicines m
            JOIN batches b ON m.id = b.medicine_id
            WHERE b.quantity > 0 AND b.expiry_date > DATE('now')
            ORDER BY m.name, b.expiry_date
        ''').fetchall()
        
        # Group medicines with their batches
        medicine_dict = {}
        for row in medicines:
            if row['id'] not in medicine_dict:
                medicine_dict[row['id']] = {
                    'id': row['id'],
                    'name': row['name'],
                    'category': row['category'],
                    'composition': row['composition'],
                    'batches': []
                }
            
            medicine_dict[row['id']]['batches'].append({
                'id': row['batch_id'],
                'batch_no': row['batch_no'],
                'quantity': row['quantity'],
                'mrp': row['mrp'],
                'expiry_date': row['expiry_date']
            })
        
        medicine_list = list(medicine_dict.values())
        db.close()
        
        return render_template('sell_medicine.html',
                             medicines=medicine_list,
                             receipt_number=receipt_number,
                             now=now)
    
    except Exception as e:
        flash(f'❌ Error in sales module: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/sales')
@login_required
def view_sales():
    try:
        db = get_db()
        sales = db.execute('''
            SELECT s.*, b.batch_no, m.name as medicine_name
            FROM sales s
            JOIN batches b ON s.batch_id = b.id
            JOIN medicines m ON b.medicine_id = m.id
            ORDER BY s.sold_on DESC
            LIMIT 100
        ''').fetchall()
        
        # Calculate sales summary
        summary = db.execute('''
            SELECT 
                COUNT(*) as total_sales,
                SUM(quantity_sold) as total_units,
                SUM(quantity_sold * selling_price) as total_revenue,
                AVG(quantity_sold * selling_price) as avg_transaction
            FROM sales 
            WHERE DATE(sold_on) = DATE('now')
        ''').fetchone()
        
        db.close()
        
        return render_template('sales.html', 
                             sales=sales, 
                             summary=summary,
                             now=datetime.now())
    except Exception as e:
        flash(f'❌ Error loading sales: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/recommend', methods=['GET', 'POST'])
@login_required
def recommend_medicine():
    if request.method == 'POST':
        symptoms = request.form.get('symptoms', '').strip()
        
        if not symptoms:
            flash('❌ Please enter symptoms', 'danger')
            return redirect(url_for('recommend_medicine'))
        
        if not symptom_model:
            flash('❌ AI model not loaded. Please run train_model.py first.', 'danger')
            return redirect(url_for('recommend_medicine'))
        
        try:
            # Get prediction from ML model
            prediction = symptom_model.predict([symptoms])[0]
            probabilities = symptom_model.predict_proba([symptoms])[0]
            
            # Get top 3 predictions
            classes = symptom_model.classes_
            top_3_indices = probabilities.argsort()[-3:][::-1]
            
            # Get medicine details for recommendations
            recommendations = []
            db = get_db()
            
            for i in top_3_indices:
                medicine_name = classes[i]
                confidence = round(probabilities[i] * 100, 2)
                
                try:
                    # Find the medicine in database to get ID and details
                    medicine = db.execute('''
                        SELECT * FROM medicines 
                        WHERE name = ?
                    ''', (medicine_name,)).fetchone()
                    
                    if medicine:
                        recommendations.append({
                            'name': medicine['name'],
                            'confidence': confidence,
                            'id': medicine['id'],
                            'details': {
                                'category': medicine['category'],
                                'composition': medicine['composition'],
                                'uses': medicine['uses'],
                                'dosage': medicine['dosage'],
                                'side_effects': medicine['side_effects']
                            }
                        })
                    else:
                        # Medicine not in database, but still show recommendation
                        recommendations.append({
                            'name': medicine_name,
                            'confidence': confidence,
                            'id': None,
                            'details': None
                        })
                        
                except Exception as e:
                    print(f"Error fetching medicine {medicine_name}: {e}")
                    # Still add recommendation without database details
                    recommendations.append({
                        'name': medicine_name,
                        'confidence': confidence,
                        'id': None,
                        'details': None
                    })
            
            db.close()
            
            if not recommendations:
                flash('❌ No recommendations found for these symptoms.', 'warning')
                return render_template('recommend.html', symptoms=symptoms)
            
            flash(f'✅ Found {len(recommendations)} recommendations for your symptoms.', 'success')
            return render_template('recommend.html',
                                 symptoms=symptoms,
                                 recommendations=recommendations)
            
        except Exception as e:
            print(f"Error in AI recommendation: {e}")
            flash(f'❌ Error generating recommendations: {str(e)}', 'danger')
            return render_template('recommend.html')
    
    return render_template('recommend.html')

@app.route('/check-interaction', methods=['GET', 'POST'])
@login_required
def check_interaction():
    if request.method == 'POST':
        drug1 = request.form.get('drug1', '').strip()
        drug2 = request.form.get('drug2', '').strip()
        
        if not drug1 or not drug2:
            flash('❌ Please enter both drug names', 'danger')
            return redirect(url_for('check_interaction'))
        
        try:
            db = get_db()
            interaction = db.execute('''
                SELECT * FROM interactions 
                WHERE (drug_a = ? AND drug_b = ?) OR (drug_a = ? AND drug_b = ?)
            ''', (drug1, drug2, drug2, drug1)).fetchone()
            db.close()
            
            return render_template('interaction_result.html',
                                 drug1=drug1,
                                 drug2=drug2,
                                 interaction=interaction,
                                 current_date=datetime.now())
        except Exception as e:
            flash(f'❌ Error checking interaction: {str(e)}', 'danger')
    
    return render_template('check_interaction.html', current_date=datetime.now())

@app.route('/interaction/result')
@login_required
def interaction_result():
    drug1 = request.args.get('drug1', '')
    drug2 = request.args.get('drug2', '')
    interaction_id = request.args.get('interaction_id')
    
    try:
        db = get_db()
        interaction = None
        if interaction_id:
            interaction = db.execute('SELECT * FROM interactions WHERE id = ?', (interaction_id,)).fetchone()
        elif drug1 and drug2:
            interaction = db.execute('''
                SELECT * FROM interactions 
                WHERE (drug_a = ? AND drug_b = ?) OR (drug_a = ? AND drug_b = ?)
            ''', (drug1, drug2, drug2, drug1)).fetchone()
        
        db.close()
        return render_template('interaction_result.html',
                             drug1=drug1,
                             drug2=drug2,
                             interaction=interaction,
                             current_date=datetime.now())
    except Exception as e:
        flash(f'❌ Error loading interaction result: {str(e)}', 'danger')
        return redirect(url_for('check_interaction'))

@app.route('/alerts')
@login_required
def view_alerts():
    try:
        db = get_db()
        alerts = db.execute('''
            SELECT a.*, b.batch_no, m.name as medicine_name
            FROM alerts a
            LEFT JOIN batches b ON a.batch_id = b.id
            LEFT JOIN medicines m ON b.medicine_id = m.id
            WHERE a.is_read = 0
            ORDER BY a.created_at DESC
        ''').fetchall()
        db.close()
        return render_template('alerts.html', alerts=alerts)
    except Exception as e:
        flash(f'❌ Error loading alerts: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/alerts/mark-read/<int:id>')
@login_required
def mark_alert_read(id):
    try:
        db = get_db()
        db.execute('UPDATE alerts SET is_read = 1 WHERE id = ?', (id,))
        db.commit()
        db.close()
        flash('✅ Alert marked as read', 'success')
    except Exception as e:
        flash(f'❌ Error marking alert as read: {str(e)}', 'danger')
    
    return redirect(url_for('view_alerts'))

@app.route('/alerts/clear-all')
@login_required
def clear_all_alerts():
    try:
        db = get_db()
        db.execute('UPDATE alerts SET is_read = 1 WHERE is_read = 0')
        db.commit()
        db.close()
        flash('✅ All alerts cleared', 'success')
    except Exception as e:
        flash(f'❌ Error clearing alerts: {str(e)}', 'danger')
    
    return redirect(url_for('view_alerts'))

@app.route('/reports')
@login_required
def reports():
    try:
        db = get_db()
        now = datetime.now()
        
        # Sales statistics (last 30 days)
        sales_stats = db.execute('''
            SELECT 
                SUM(quantity_sold * selling_price) as total_revenue,
                SUM(quantity_sold) as total_sales,
                COUNT(DISTINCT customer_name) as unique_customers
            FROM sales 
            WHERE sold_on >= DATE('now', '-30 days')
        ''').fetchone()
        
        # Calculate average transaction value
        avg_transaction = 0
        if sales_stats['total_sales'] and sales_stats['total_revenue']:
            avg_transaction = sales_stats['total_revenue'] / sales_stats['total_sales']
        
        sales_data = {
            'total_revenue': sales_stats['total_revenue'] or 0,
            'total_sales': sales_stats['total_sales'] or 0,
            'unique_customers': sales_stats['unique_customers'] or 0,
            'avg_transaction': avg_transaction
        }
        
        # Inventory statistics
        inventory_stats = db.execute('''
            SELECT 
                COUNT(DISTINCT m.id) as total_medicines,
                COUNT(b.id) as total_batches,
                SUM(b.quantity) as total_quantity,
                SUM(b.quantity * b.mrp) as stock_value,
                SUM(b.quantity * b.cost_price) as cost_value
            FROM medicines m
            LEFT JOIN batches b ON m.id = b.medicine_id
            WHERE b.expiry_date >= DATE('now') OR b.id IS NULL
        ''').fetchone()
        
        # Calculate potential revenue and profit margin
        potential_revenue = inventory_stats['stock_value'] or 0
        cost_value = inventory_stats['cost_value'] or 0
        profit_margin = 0
        if cost_value > 0:
            profit_margin = ((potential_revenue - cost_value) / cost_value) * 100
        
        inventory_data = {
            'total_medicines': inventory_stats['total_medicines'] or 0,
            'total_batches': inventory_stats['total_batches'] or 0,
            'total_quantity': inventory_stats['total_quantity'] or 0,
            'stock_value': inventory_stats['stock_value'] or 0,
            'cost_value': cost_value,
            'potential_revenue': potential_revenue,
            'profit_margin': profit_margin
        }
        
        # Expiry statistics
        expiry_stats = db.execute('''
            SELECT 
                COUNT(CASE WHEN expiry_date < DATE('now') THEN 1 END) as expired_count,
                COUNT(CASE WHEN expiry_date BETWEEN DATE('now') AND DATE('now', '+15 days') THEN 1 END) as near_expiry_count,
                COUNT(CASE WHEN expiry_date BETWEEN DATE('now', '+16 days') AND DATE('now', '+90 days') THEN 1 END) as expiring_soon_count,
                COUNT(CASE WHEN expiry_date > DATE('now', '+90 days') THEN 1 END) as good_stock_count
            FROM batches
        ''').fetchone()
        
        expiry_data = {
            'expired_count': expiry_stats['expired_count'] or 0,
            'near_expiry_count': expiry_stats['near_expiry_count'] or 0,
            'expiring_soon_count': expiry_stats['expiring_soon_count'] or 0,
            'good_stock_count': expiry_stats['good_stock_count'] or 0
        }
        
        db.close()
        
        return render_template('reports.html',
                             sales_stats=sales_data,
                             inventory_stats=inventory_data,
                             expiry_stats=expiry_data,
                             now=now)
    
    except Exception as e:
        flash(f'❌ Error loading reports: {str(e)}', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/api/medicines/search')
@login_required
def search_medicines():
    query = request.args.get('q', '').strip()
    
    try:
        db = get_db()
        
        if query:
            medicines = db.execute('''
                SELECT m.*, 
                       (SELECT SUM(quantity) FROM batches b 
                        WHERE b.medicine_id = m.id AND b.expiry_date > DATE('now')) as total_stock
                FROM medicines m
                WHERE m.name LIKE ? OR m.category LIKE ? OR m.composition LIKE ?
                ORDER BY m.name
                LIMIT 20
            ''', (f'%{query}%', f'%{query}%', f'%{query}%')).fetchall()
        else:
            medicines = db.execute('''
                SELECT m.*, 
                       (SELECT SUM(quantity) FROM batches b 
                        WHERE b.medicine_id = m.id AND b.expiry_date > DATE('now')) as total_stock
                FROM medicines m
                ORDER BY m.name
                LIMIT 20
            ''').fetchall()
        
        db.close()
        
        # Convert to dictionary for JSON response
        medicines_list = []
        for med in medicines:
            medicines_list.append({
                'id': med['id'],
                'name': med['name'],
                'category': med['category'],
                'composition': med['composition'],
                'total_stock': med['total_stock'] or 0
            })
        
        return jsonify({'medicines': medicines_list})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/batches/<int:medicine_id>')
@login_required
def get_batches(medicine_id):
    try:
        db = get_db()
        batches = db.execute('''
            SELECT id, batch_no, quantity, mrp, expiry_date
            FROM batches
            WHERE medicine_id = ? AND quantity > 0 AND expiry_date > DATE('now')
            ORDER BY expiry_date
        ''', (medicine_id,)).fetchall()
        
        db.close()
        
        batches_list = []
        for batch in batches:
            batches_list.append({
                'id': batch['id'],
                'batch_no': batch['batch_no'],
                'quantity': batch['quantity'],
                'mrp': batch['mrp'],
                'expiry_date': batch['expiry_date']
            })
        
        return jsonify({'batches': batches_list})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/medicine/by_name/<name>')
@login_required
def get_medicine_by_name(name):
    """Get medicine ID by name for AJAX requests"""
    try:
        db = get_db()
        medicine = db.execute('''
            SELECT id, name, composition, uses, dosage, side_effects, category
            FROM medicines 
            WHERE name = ?
        ''', (name,)).fetchone()
        
        db.close()
        
        if medicine:
            return jsonify({
                'success': True,
                'medicine': {
                    'id': medicine['id'],
                    'name': medicine['name'],
                    'composition': medicine['composition'],
                    'uses': medicine['uses'],
                    'dosage': medicine['dosage'],
                    'side_effects': medicine['side_effects'],
                    'category': medicine['category']
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Medicine not found'
            })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/sales/process', methods=['POST'])
@login_required
def process_sale_api():
    try:
        data = request.get_json()
        
        if not data or 'cart' not in data or 'customer' not in data:
            return jsonify({'success': False, 'message': 'Invalid data'}), 400
        
        cart = data['cart']
        customer = data['customer']
        payment_method = data.get('payment_method', 'cash')
        
        db = get_db()
        now = datetime.now()
        
        # Process each item in cart
        for item in cart:
            # Check stock availability
            batch = db.execute('SELECT quantity FROM batches WHERE id = ?', 
                              (item['batchId'],)).fetchone()
            
            if not batch or batch['quantity'] < item['quantity']:
                return jsonify({
                    'success': False, 
                    'message': f'Insufficient stock for {item["name"]}'
                }), 400
            
            # Update stock
            new_quantity = batch['quantity'] - item['quantity']
            db.execute('UPDATE batches SET quantity = ? WHERE id = ?', 
                      (new_quantity, item['batchId']))
            
            # Record sale
            db.execute('''
                INSERT INTO sales 
                (batch_id, quantity_sold, selling_price, customer_name, customer_phone, 
                 customer_age, prescription_number, doctor_name, diagnosis, sold_on)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['batchId'], item['quantity'], item['price'],
                customer['name'], customer['phone'], customer.get('age'),
                customer.get('prescription'), customer.get('doctor'), 
                customer.get('diagnosis'), now.isoformat()
            ))
        
        db.commit()
        
        # Get the last inserted sale ID for receipt number
        receipt_number = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        db.close()
        
        return jsonify({
            'success': True, 
            'message': 'Sale processed successfully',
            'receipt_number': receipt_number
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Check if database exists, if not create it
    if not os.path.exists('pharma.db'):
        print("Database not found. Running initialization...")
        try:
            exec(open('init_db.py').read())
        except Exception as e:
            print(f"Error initializing database: {e}")
    
    # Check if model exists, if not train it
    if not os.path.exists('models/symptom_model.joblib'):
        print("ML model not found. Training model...")
        try:
            exec(open('train_model.py').read())
        except Exception as e:
            print(f"Error training model: {e}")
    
    print("\n" + "="*50)
    print("🚀 Smart Pharma Assistant Starting...")
    print("="*50)
    print("📊 Access the application at: http://127.0.0.1:5000")
    print("👤 Default login: admin / admin123")
    print("="*50 + "\n")
    
    app.run(debug=True, port=5000)