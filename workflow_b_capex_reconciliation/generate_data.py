import sqlite3
import random
import os
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

def generate_mock_erp_data(num_invoices=500):
    db_path = os.path.join(os.path.dirname(__file__), "capex_erp.db")
    print(f"🏭 Generating {num_invoices} synthetic invoices & ERP budget into {db_path}...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create Master Budget Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS MasterBudget (
        Phase TEXT PRIMARY KEY,
        Contractor TEXT,
        TotalBudget REAL,
        AmountPaid REAL,
        RemainingBudget REAL
    )''')
    
    # Create Invoice Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Invoices (
        InvoiceID TEXT PRIMARY KEY,
        Date TEXT,
        Contractor TEXT,
        Phase TEXT,
        Amount REAL,
        Status TEXT
    )''')
    
    # Insert Master Budget (Sterile Data)
    phases = [
        ("Phase 1 Foundation", "Acme Builders", 5000000, 4800000, 200000),
        ("Phase 2 Cooling Infrastructure", "Frosty Tech", 10000000, 8500000, 1500000),
        ("Phase 3 Electrical", "Sparky Inc", 8000000, 2000000, 6000000),
        ("Phase 4 Security Systems", "SafeGuard LLC", 2000000, 500000, 1500000)
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO MasterBudget VALUES (?,?,?,?,?)', phases)
    
    # Insert 500 Fake Invoices
    for i in range(num_invoices):
        phase_data = random.choice(phases)
        phase_name = phase_data[0]
        contractor = phase_data[1]
        
        # Generate realistic amount (sometimes over budget)
        is_fraud = random.random() < 0.05 # 5% chance of being over remaining budget
        if is_fraud:
            amount = phase_data[4] + random.uniform(10000, 500000)
        else:
            amount = random.uniform(1000, phase_data[4] / 10)
            
        date = fake.date_between(start_date='-1y', end_date='today').strftime('%Y-%m-%d')
        invoice_id = f"INV-{fake.unique.random_number(digits=6)}"
        
        cursor.execute('INSERT OR REPLACE INTO Invoices VALUES (?,?,?,?,?,?)', 
                       (invoice_id, date, contractor, phase_name, round(amount, 2), "Pending Review"))
    
    conn.commit()
    conn.close()
    print("✅ Synthetic dataset created successfully.")

if __name__ == "__main__":
    generate_mock_erp_data()
