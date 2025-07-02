
"""
Data Migration Script: SQLite to PostgreSQL
Migrates all data from instance/app.db to Docker PostgreSQL
"""

import sqlite3
import psycopg2
from datetime import datetime

# Database configurations
SQLITE_DB = 'instance/app.db'
POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'mechanic_shop',
    'user': 'mechanic_user',
    'password': 'mechanic_password'
}

def convert_boolean_fields(table_name, columns, rows):
    """Convert SQLite integer booleans to PostgreSQL booleans"""
    boolean_fields = {
        'inventory': ['is_deleted'],
        'service_ticket': ['is_deleted'],
        'serialized_part': ['is_deleted'],
        'customer': [],
        'employee': [],
        'service': []
    }
    
    if table_name not in boolean_fields:
        return rows
    
    bool_columns = boolean_fields[table_name]
    if not bool_columns:
        return rows
    
    # Find indices of boolean columns
    bool_indices = []
    for bool_col in bool_columns:
        if bool_col in columns:
            bool_indices.append(columns.index(bool_col))
    
    if not bool_indices:
        return rows
    
    # Convert rows
    converted_rows = []
    for row in rows:
        row_list = list(row)
        for idx in bool_indices:
            # Convert 0/1 to False/True
            if row_list[idx] == 0:
                row_list[idx] = False
            elif row_list[idx] == 1:
                row_list[idx] = True
        converted_rows.append(tuple(row_list))
    
    return converted_rows

def export_table_data(sqlite_cursor, table_name):
    """Export all data from a SQLite table"""
    print(f"Exporting {table_name}...")
    
    # Get column info
    sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in sqlite_cursor.fetchall()]
    
    # Get all data
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    
    # Convert boolean fields
    rows = convert_boolean_fields(table_name, columns, rows)
    
    print(f"   Found {len(rows)} records")
    return columns, rows

def import_table_data(pg_cursor, table_name, columns, rows):
    """Import data into PostgreSQL table"""
    if not rows:
        print(f"   ⏭️  Skipping {table_name} (no data)")
        return
    
    print(f"Importing {len(rows)} records into {table_name}...")
    
    # Quote column names to handle reserved keywords
    quoted_columns = [f'"{col}"' for col in columns]
    placeholders = ', '.join(['%s'] * len(columns))
    column_names = ', '.join(quoted_columns)
    
    # Handle potential conflicts with auto-increment IDs
    if 'id' in columns:
        # Disable ID conflicts by handling sequences
        insert_sql = f"""
        INSERT INTO {table_name} ({column_names}) 
        VALUES ({placeholders})
        ON CONFLICT (id) DO NOTHING
        """
    else:
        insert_sql = f"""
        INSERT INTO {table_name} ({column_names}) 
        VALUES ({placeholders})
        """
    
    try:
        # Insert all rows
        pg_cursor.executemany(insert_sql, rows)
        print(f"Successfully imported {len(rows)} records")
        
        # Reset sequence if table has id column
        if 'id' in columns:
            pg_cursor.execute(f"""
                SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), 
                       COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {table_name};
            """)
            print(f"Reset ID sequence for {table_name}")
            
    except Exception as e:
        print(f"Error importing {table_name}: {e}")
        raise

def clear_postgresql_data(pg_cursor):
    """Clear existing data from PostgreSQL tables"""
    print("Clearing existing data from PostgreSQL...")
    
    tables = [
        'serialized_part_usage',
        'employee_service_ticket', 
        'service_tracker',
        'serialized_part',
        'service_ticket',
        'inventory',
        'service',
        'employee',
        'customer'
    ]
    
    for table in tables:
        try:
            pg_cursor.execute(f"DELETE FROM {table}")
            print(f"Cleared {table}")
        except Exception as e:
            print(f"Could not clear {table}: {e}")

def migrate_data():
    """Main migration function"""
    print("Starting data migration from SQLite to PostgreSQL")
    print("="*60)
    
    # Tables to migrate (in dependency order)
    tables_to_migrate = [
        'customer',
        'employee', 
        'service',
        'inventory',
        'service_ticket',
        'serialized_part',
        'employee_service_ticket',
        'serialized_part_usage',
        'service_tracker'
    ]
    
    try:
        # Connect to SQLite
        print("Connecting to SQLite database...")
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        sqlite_cursor = sqlite_conn.cursor()
        
        # Connect to PostgreSQL
        print("Connecting to PostgreSQL database...")
        pg_conn = psycopg2.connect(**POSTGRES_CONFIG)
        pg_cursor = pg_conn.cursor()
        
        # Clear existing data first
        clear_postgresql_data(pg_cursor)
        pg_conn.commit()
        
        # Migrate each table
        total_migrated = 0
        for table in tables_to_migrate:
            try:
                # Check if table exists in SQLite
                sqlite_cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?", 
                    (table,)
                )
                if not sqlite_cursor.fetchone():
                    print(f"kipping {table} (doesn't exist in SQLite)")
                    continue
                
                # Export from SQLite
                columns, rows = export_table_data(sqlite_cursor, table)
                
                # Import to PostgreSQL  
                import_table_data(pg_cursor, table, columns, rows)
                total_migrated += len(rows)
                
                # Commit after each successful table
                pg_conn.commit()
                
            except Exception as e:
                print(f"Error migrating {table}: {e}")
                # Rollback this table's changes but continue
                pg_conn.rollback()
                continue
        
        print("="*60)
        print(f"Migration completed!")
        print(f"Total records migrated: {total_migrated}")
        
        # Verify migration
        print("\nVerification:")
        for table in tables_to_migrate:
            try:
                pg_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = pg_cursor.fetchone()[0]
                if count > 0:
                    print(f"   {table}: {count} records")
            except Exception as e:
                print(f"   {table}:{e}")
                
    except Exception as e:
        print(f"Migration failed: {e}")
        if 'pg_conn' in locals():
            pg_conn.rollback()
        raise
        
    finally:
        # Close connections
        if 'sqlite_conn' in locals():
            sqlite_conn.close()
        if 'pg_conn' in locals():
            pg_conn.close()
        print("Database connections closed")

if __name__ == "__main__":
    migrate_data() 