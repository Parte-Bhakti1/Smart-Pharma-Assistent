import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
import os

def create_database():
    """Create and initialize the pharmacy database with sample data"""
    
    print("=" * 60)
    print("🗄️  Initializing Smart Pharma Assistant Database")
    print("=" * 60)
    
    # Remove existing database if exists (for fresh start)
    if os.path.exists('pharma.db'):
        backup_name = f'pharma_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        os.rename('pharma.db', backup_name)
        print(f"📁 Existing database backed up as: {backup_name}")
    
    try:
        # Create database and tables
        conn = sqlite3.connect('pharma.db')
        cur = conn.cursor()
        
        print("\n📊 Creating database tables...")
        
        # Create users table
        cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'pharmacist',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create medicines table
        cur.execute('''
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            composition TEXT,
            uses TEXT,
            dosage TEXT,
            side_effects TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create batches table
        cur.execute('''
        CREATE TABLE IF NOT EXISTS batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id INTEGER NOT NULL,
            batch_no TEXT NOT NULL UNIQUE,
            quantity INTEGER DEFAULT 0,
            mrp REAL,
            cost_price REAL,
            mfg_date DATE NOT NULL,
            expiry_date DATE NOT NULL,
            supplier TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (medicine_id) REFERENCES medicines (id) ON DELETE CASCADE
        )
        ''')
        
        # Create sales table
        cur.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            quantity_sold INTEGER NOT NULL,
            selling_price REAL NOT NULL,
            customer_name TEXT,
            customer_phone TEXT,
            customer_age INTEGER,
            prescription_number TEXT,
            doctor_name TEXT,
            diagnosis TEXT,
            sold_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES batches (id)
        )
        ''')
        
        # Create interactions table
        cur.execute('''
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_a TEXT NOT NULL,
            drug_b TEXT NOT NULL,
            severity TEXT CHECK(severity IN ('Low', 'Medium', 'High')),
            description TEXT,
            recommendation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create alerts table
        cur.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL CHECK(alert_type IN ('expiry', 'low_stock', 'recall', 'other')),
            message TEXT NOT NULL,
            severity TEXT DEFAULT 'warning' CHECK(severity IN ('info', 'warning', 'danger')),
            is_read BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (batch_id) REFERENCES batches (id)
        )
        ''')
        
        # Create audit log table
        cur.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        print("✅ Database tables created successfully!")
        
        # Add admin user
        print("\n👤 Creating admin user...")
        password_hash = generate_password_hash('admin123')
        cur.execute("INSERT OR REPLACE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    ('admin', password_hash, 'admin'))
        
        # Add additional users
        users = [
            ('pharmacist1', generate_password_hash('pharma123'), 'pharmacist'),
            ('manager', generate_password_hash('manage123'), 'manager'),
            ('staff', generate_password_hash('staff123'), 'staff'),
        ]
        
        cur.executemany('''
        INSERT OR IGNORE INTO users (username, password_hash, role) 
        VALUES (?, ?, ?)
        ''', users)
        
        # Add sample medicines
        print("\n💊 Adding sample medicines...")
        medicines = [
            ('Paracetamol', 'Paracetamol 500mg', 'Fever, Pain relief', '1 tablet every 4-6 hours', 
             'Rare: Skin rash, Nausea', 'Analgesic'),
            ('Amoxicillin', 'Amoxicillin 250mg Capsule', 'Bacterial infections', '1 capsule 3 times daily for 5-7 days', 
             'Nausea, Diarrhea, Allergic reactions', 'Antibiotic'),
            ('Cetirizine', 'Cetirizine 10mg', 'Allergies, Cold symptoms, Hay fever', '1 tablet daily', 
             'Drowsiness, Dry mouth, Headache', 'Antihistamine'),
            ('Omeprazole', 'Omeprazole 20mg', 'Acidity, Heartburn, GERD', '1 capsule before breakfast for 14 days', 
             'Headache, Nausea, Abdominal pain', 'Antacid'),
            ('Aspirin', 'Aspirin 75mg', 'Pain relief, Fever, Blood thinner', '1 tablet daily as prescribed', 
             'Stomach irritation, Bleeding risk', 'NSAID'),
            ('Ibuprofen', 'Ibuprofen 400mg', 'Pain, Inflammation, Fever', '1 tablet every 6-8 hours with food', 
             'Stomach upset, Dizziness, Rash', 'NSAID'),
            ('Metformin', 'Metformin 500mg', 'Type 2 Diabetes', '1 tablet twice daily with meals', 
             'Nausea, Diarrhea, Abdominal discomfort', 'Anti-diabetic'),
            ('Atorvastatin', 'Atorvastatin 10mg', 'High cholesterol', '1 tablet at bedtime', 
             'Muscle pain, Headache, Nausea', 'Statin'),
            ('Levothyroxine', 'Levothyroxine 50mcg', 'Hypothyroidism', '1 tablet empty stomach in morning', 
             'Palpitations, Weight loss, Insomnia', 'Thyroid hormone'),
            ('Salbutamol', 'Salbutamol Inhaler 100mcg', 'Asthma, Bronchospasm', '1-2 puffs as needed', 
             'Tremors, Palpitations, Headache', 'Bronchodilator'),
            ('Azithromycin', 'Azithromycin 500mg', 'Bacterial infections', '2 tablets on day 1, then 1 daily for 4 days', 
             'Diarrhea, Nausea, Abdominal pain', 'Antibiotic'),
            ('Diclofenac', 'Diclofenac 50mg', 'Pain, Inflammation, Arthritis', '1 tablet 2-3 times daily with food', 
             'Stomach pain, Ulcers, Kidney issues', 'NSAID'),
            ('Pantoprazole', 'Pantoprazole 40mg', 'Acid reflux, Ulcers', '1 tablet before breakfast', 
             'Headache, Diarrhea, Nausea', 'Proton pump inhibitor'),
            ('Losartan', 'Losartan 50mg', 'High blood pressure', '1 tablet daily', 
             'Dizziness, Fatigue, Back pain', 'ARB'),
            ('Sertraline', 'Sertraline 50mg', 'Depression, Anxiety', '1 tablet daily', 
             'Nausea, Insomnia, Sexual dysfunction', 'SSRI'),
        ]
        
        cur.executemany('''
        INSERT OR IGNORE INTO medicines (name, composition, uses, dosage, side_effects, category)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', medicines)
        
        # Add sample batches
        print("📦 Adding sample batches...")
        today = datetime.now().date()
        
        batches = [
            # Paracetamol batches
            (1, 'PAR2024A001', 150, 15.0, 8.5, today - timedelta(days=45), today + timedelta(days=180), 'MediCorp India'),
            (1, 'PAR2024B002', 200, 15.0, 8.5, today - timedelta(days=30), today + timedelta(days=210), 'HealthPharma Ltd'),
            
            # Amoxicillin batches
            (2, 'AMX2024C001', 80, 45.0, 25.0, today - timedelta(days=60), today + timedelta(days=365), 'BioMed Solutions'),
            (2, 'AMX2024D002', 120, 45.0, 25.0, today - timedelta(days=20), today + timedelta(days=400), 'MediCorp India'),
            
            # Cetirizine batches
            (3, 'CET2024E001', 250, 8.0, 4.0, today - timedelta(days=15), today + timedelta(days=730), 'AllerFree Inc'),
            (3, 'CET2024F002', 180, 8.0, 4.0, today - timedelta(days=90), today + timedelta(days=640), 'PharmaHealth'),
            
            # Omeprazole batches
            (4, 'OME2024G001', 100, 25.0, 12.0, today - timedelta(days=40), today + timedelta(days=150), 'DigestCare Pharma'),
            (4, 'OME2024H002', 75, 25.0, 12.0, today - timedelta(days=100), today + timedelta(days=90), 'MediCorp India'),
            
            # Aspirin batches
            (5, 'ASP2024I001', 120, 12.0, 6.0, today - timedelta(days=120), today - timedelta(days=15), 'CardioCare Inc'),
            (5, 'ASP2024J002', 90, 12.0, 6.0, today - timedelta(days=30), today + timedelta(days=90), 'HealthLine Pharma'),
            
            # Ibuprofen batches
            (6, 'IBU2024K001', 140, 18.0, 9.0, today - timedelta(days=25), today + timedelta(days=335), 'PainRelief Co'),
            (6, 'IBU2024L002', 95, 18.0, 9.0, today - timedelta(days=80), today + timedelta(days=280), 'MediCorp India'),
            
            # Low stock batches
            (7, 'MET2024M001', 15, 35.0, 18.0, today - timedelta(days=60), today + timedelta(days=300), 'DiabetoCare'),
            (8, 'ATO2024N001', 8, 55.0, 28.0, today - timedelta(days=30), today + timedelta(days=365), 'Cholesterol Care'),
            
            # Expired batch
            (9, 'LEV2023O001', 50, 42.0, 21.0, today - timedelta(days=400), today - timedelta(days=30), 'ThyroMed'),
        ]
        
        cur.executemany('''
        INSERT OR IGNORE INTO batches (medicine_id, batch_no, quantity, mrp, cost_price, mfg_date, expiry_date, supplier)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', batches)
        
        # Add sample interactions
        print("⚠️ Adding drug interactions...")
        interactions = [
            # High severity interactions
            ('Warfarin', 'Aspirin', 'High', 'Increased risk of bleeding, bruising', 'Avoid combination. Monitor INR regularly if necessary.'),
            ('Warfarin', 'Ibuprofen', 'High', 'Increased bleeding risk, GI bleeding', 'Avoid NSAIDs with warfarin. Use paracetamol instead.'),
            ('Metformin', 'Alcohol', 'High', 'Risk of lactic acidosis', 'Avoid excessive alcohol consumption.'),
            ('Lithium', 'Ibuprofen', 'High', 'Increased lithium levels, toxicity risk', 'Monitor lithium levels. Avoid NSAIDs.'),
            ('Monoamine Oxidase Inhibitors', 'Tyramine-rich foods', 'High', 'Hypertensive crisis', 'Avoid aged cheese, cured meats, fermented foods.'),
            
            # Medium severity interactions
            ('Aspirin', 'Ibuprofen', 'Medium', 'Reduced cardioprotective effect of aspirin', 'Take aspirin 2 hours before ibuprofen.'),
            ('Omeprazole', 'Clopidogrel', 'Medium', 'Reduced effectiveness of clopidogrel', 'Consider alternative PPI like pantoprazole.'),
            ('Digoxin', 'Furosemide', 'Medium', 'Increased risk of digoxin toxicity', 'Monitor digoxin levels and potassium.'),
            ('Statins', 'Grapefruit juice', 'Medium', 'Increased statin levels, muscle pain risk', 'Avoid grapefruit juice with statins.'),
            ('Oral Contraceptives', 'Antibiotics', 'Medium', 'Reduced contraceptive effectiveness', 'Use backup contraception during antibiotic course.'),
            
            # Low severity interactions
            ('Cetirizine', 'Alcohol', 'Low', 'Increased drowsiness, impaired coordination', 'Avoid driving or operating machinery.'),
            ('Metformin', 'Cimetidine', 'Low', 'Increased metformin levels', 'Monitor for increased side effects.'),
            ('Levothyroxine', 'Calcium supplements', 'Low', 'Reduced levothyroxine absorption', 'Take levothyroxine 4 hours before calcium.'),
            ('Sertraline', 'NSAIDs', 'Low', 'Increased bleeding risk', 'Monitor for bruising or bleeding.'),
            ('Atorvastatin', 'Antacids', 'Low', 'Reduced statin absorption', 'Take atorvastatin 2 hours before antacids.'),
        ]
        
        cur.executemany('''
        INSERT OR IGNORE INTO interactions (drug_a, drug_b, severity, description, recommendation)
        VALUES (?, ?, ?, ?, ?)
        ''', interactions)
        
        # Add sample sales data for analytics
        print("💰 Adding sample sales data...")
        sales = []
        for i in range(1, 31):  # 30 sample sales
            batch_id = (i % 12) + 1  # Distribute across batches
            quantity = [1, 2, 3, 4, 5][i % 5]
            price = [10.0, 15.0, 20.0, 25.0, 30.0][i % 5]
            days_ago = i * 2  # Spread sales over last 60 days
            
            sales.append((
                batch_id, quantity, price, 
                f'Customer {i}', f'98{i:07d}', 
                20 + (i % 50), f'RX{i:06d}', 
                f'Dr. {"ABC"[i%3]}', 
                ['Fever', 'Cold', 'Headache', 'Allergy', 'Pain'][i % 5],
                (today - timedelta(days=days_ago)).isoformat()
            ))
        
        cur.executemany('''
        INSERT OR IGNORE INTO sales 
        (batch_id, quantity_sold, selling_price, customer_name, customer_phone, 
         customer_age, prescription_number, doctor_name, diagnosis, sold_on)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sales)
        
        # Add sample alerts
        print("🔔 Generating sample alerts...")
        
        # Near expiry alerts
        cur.execute('''
        INSERT OR IGNORE INTO alerts (batch_id, alert_type, message, severity)
        SELECT id, 'expiry', 'Batch ' || batch_no || ' expires in less than 30 days', 'warning'
        FROM batches 
        WHERE expiry_date BETWEEN DATE('now') AND DATE('now', '+30 days')
        ''')
        
        # Expired alerts
        cur.execute('''
        INSERT OR IGNORE INTO alerts (batch_id, alert_type, message, severity)
        SELECT id, 'expiry', '🚨 BATCH EXPIRED: ' || batch_no || ' has expired', 'danger'
        FROM batches 
        WHERE expiry_date < DATE('now')
        ''')
        
        # Low stock alerts
        cur.execute('''
        INSERT OR IGNORE INTO alerts (batch_id, alert_type, message, severity)
        SELECT id, 'low_stock', '⚠️ Low stock: Batch ' || batch_no || ' has only ' || quantity || ' units left', 'warning'
        FROM batches 
        WHERE quantity < 20
        ''')
        
        # Commit all changes
        conn.commit()
        
        # Print summary statistics
        print("\n" + "=" * 60)
        print("📊 DATABASE SUMMARY")
        print("=" * 60)
        
        summary_data = [
            ('users', cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]),
            ('medicines', cur.execute("SELECT COUNT(*) FROM medicines").fetchone()[0]),
            ('batches', cur.execute("SELECT COUNT(*) FROM batches").fetchone()[0]),
            ('interactions', cur.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]),
            ('sales', cur.execute("SELECT COUNT(*) FROM sales").fetchone()[0]),
            ('alerts', cur.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]),
        ]
        
        for table, count in summary_data:
            print(f"📁 {table.capitalize():12} : {count}")
        
        # Expiry statistics
        expiry_stats = cur.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN expiry_date < DATE('now') THEN 1 ELSE 0 END) as expired,
            SUM(CASE WHEN expiry_date BETWEEN DATE('now') AND DATE('now', '+15 days') THEN 1 ELSE 0 END) as near_expiry,
            SUM(CASE WHEN expiry_date BETWEEN DATE('now', '+16 days') AND DATE('now', '+90 days') THEN 1 ELSE 0 END) as expiring_soon
        FROM batches
        ''').fetchone()
        
        print(f"\n📅 BATCH EXPIRY STATUS:")
        print(f"   • Expired: {expiry_stats[1]} batches")
        print(f"   • Near expiry (≤15 days): {expiry_stats[2]} batches")
        print(f"   • Expiring soon (16-90 days): {expiry_stats[3]} batches")
        print(f"   • Good (>90 days): {expiry_stats[0] - expiry_stats[1] - expiry_stats[2] - expiry_stats[3]} batches")
        
        # Stock statistics
        stock_stats = cur.execute('''
        SELECT 
            SUM(quantity) as total_stock,
            AVG(quantity) as avg_stock,
            COUNT(CASE WHEN quantity < 10 THEN 1 END) as low_stock,
            COUNT(CASE WHEN quantity = 0 THEN 1 END) as out_of_stock
        FROM batches
        ''').fetchone()
        
        print(f"\n📦 STOCK STATUS:")
        print(f"   • Total units in stock: {stock_stats[0] or 0}")
        print(f"   • Average batch size: {stock_stats[1] or 0:.1f} units")
        print(f"   • Low stock batches (<10 units): {stock_stats[2] or 0}")
        print(f"   • Out of stock batches: {stock_stats[3] or 0}")
        
        # Sales statistics
        sales_stats = cur.execute('''
        SELECT 
            SUM(quantity_sold) as total_sold,
            SUM(quantity_sold * selling_price) as total_revenue,
            COUNT(DISTINCT customer_name) as unique_customers
        FROM sales
        ''').fetchone()
        
        print(f"\n💰 SALES STATISTICS:")
        print(f"   • Total units sold: {sales_stats[0] or 0}")
        print(f"   • Total revenue: ₹{sales_stats[1] or 0:,.2f}")
        print(f"   • Unique customers: {sales_stats[2] or 0}")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ DATABASE INITIALIZATION COMPLETE")
        print("=" * 60)
        
        print("\n👤 LOGIN CREDENTIALS:")
        print("   • Admin: admin / admin123")
        print("   • Pharmacist: pharmacist1 / pharma123")
        print("   • Manager: manager / manage123")
        print("   • Staff: staff / staff123")
        
        print("\n🚀 NEXT STEPS:")
        print("   1. Run train_model.py to train AI:")
        print("      python train_model.py")
        print("\n   2. Start the application:")
        print("      python app.py")
        print("\n   3. Open browser and go to:")
        print("      http://127.0.0.1:5000")
        print("\n   4. Login with admin credentials")
        print("=" * 60)
        
    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        raise

if __name__ == '__main__':
    try:
        create_database()
    except KeyboardInterrupt:
        print("\n\n⚠️ Database initialization interrupted by user.")
    except Exception as e:
        print(f"\n❌ Failed to initialize database: {e}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check if SQLite3 is installed")
        print("   2. Ensure you have write permissions")
        print("   3. Try deleting existing pharma.db file")
        print("   4. Check Python packages: pip install werkzeug")