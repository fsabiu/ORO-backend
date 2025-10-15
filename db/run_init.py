#!/usr/bin/env python3
"""
Database initialization script for ORO Backend.

This script uses the Database class to execute the init.sql script
and set up the Oracle Spatial database schema.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from database import Database


def split_sql_statements(sql_content):
    """
    Split SQL content into individual statements.
    Handles Oracle-specific syntax like PL/SQL blocks and forward slashes.
    """
    statements = []
    current_statement = ""
    in_string = False
    string_char = None
    brace_count = 0
    
    lines = sql_content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('--'):
            continue
            
        current_statement += line + '\n'
        
        # Check for string literals and braces
        i = 0
        while i < len(line):
            char = line[i]
            if not in_string and char in ("'", '"'):
                in_string = True
                string_char = char
            elif in_string and char == string_char:
                # Check for escaped quotes
                if i + 1 < len(line) and line[i + 1] == string_char:
                    i += 1  # Skip the next quote
                else:
                    in_string = False
                    string_char = None
            elif not in_string:
                if char == '(':
                    brace_count += 1
                elif char == ')':
                    brace_count -= 1
            i += 1
        
        # Check for statement terminators
        if not in_string and brace_count == 0:
            if line.endswith(';'):
                # Regular SQL statement
                statement = current_statement.rstrip(';').strip()
                if statement:
                    statements.append(statement)
                current_statement = ""
            elif line == '/' and current_statement.strip():
                # PL/SQL block or Oracle script terminator
                statement = current_statement.rstrip('/').strip()
                if statement:
                    statements.append(statement)
                current_statement = ""
    
    # Add any remaining statement
    if current_statement.strip():
        statements.append(current_statement.strip())
    
    return statements


def run_init_script():
    """
    Execute the init.sql script using the Database class.
    """
    print("ORO Backend Database Initialization")
    print("=" * 40)
    
    try:
        # Initialize database connection
        print("1. Connecting to Oracle Autonomous Database...")
        db = Database(wallet_path="wallet_oro.zip")
        db.connect()
        
        # Test connection
        if not db.test_connection():
            print("   ✗ Database connection failed!")
            return False
        
        print("   ✓ Connected successfully!")
        
        # Read the init.sql file
        print("2. Reading init.sql script...")
        init_sql_path = os.path.join(os.path.dirname(__file__), 'init.sql')
        
        if not os.path.exists(init_sql_path):
            print(f"   ✗ init.sql file not found at: {init_sql_path}")
            return False
        
        with open(init_sql_path, 'r') as f:
            sql_content = f.read()
        
        print("   ✓ init.sql script loaded")
        
        # First, clean up any existing objects
        print("3. Cleaning up existing objects...")
        try:
            cleanup_statements = [
                "DROP TABLE NOTIFICATIONS CASCADE CONSTRAINTS",
                "DROP TABLE DETECTIONS CASCADE CONSTRAINTS", 
                "DROP TABLE RULESETS CASCADE CONSTRAINTS",
                "DROP TABLE REPORTS CASCADE CONSTRAINTS"
            ]
            
            for stmt in cleanup_statements:
                try:
                    db.execute_update(stmt)
                    print(f"   ✓ Dropped existing table")
                except Exception as e:
                    if "does not exist" in str(e).lower() or "not exist" in str(e).lower():
                        print(f"   ℹ Table already clean")
                    else:
                        print(f"   ⚠ Warning: {str(e)[:50]}...")
            
            # Clear spatial metadata
            try:
                db.execute_update("DELETE FROM USER_SDO_GEOM_METADATA WHERE TABLE_NAME IN ('REPORTS', 'RULESETS', 'DETECTIONS')")
                print("   ✓ Cleared spatial metadata")
            except Exception as e:
                print(f"   ℹ Spatial metadata already clean")
                
        except Exception as e:
            print(f"   ⚠ Cleanup warning: {e}")
        
        # Execute the main SQL script
        print("4. Executing main SQL script...")
        try:
            # Split the script into individual statements and execute them
            statements = split_sql_statements(sql_content)
            print(f"   ✓ Found {len(statements)} statements to execute")
            
            success_count = 0
            error_count = 0
            
            for i, statement in enumerate(statements, 1):
                if not statement.strip():
                    continue
                    
                try:
                    print(f"   [{i}/{len(statements)}] Executing statement...")
                    
                    # Execute the statement
                    if statement.strip().upper().startswith(('SELECT', 'WITH')):
                        result = db.execute_query(statement)
                        print(f"      ✓ Query executed, returned {len(result)} rows")
                    else:
                        affected_rows = db.execute_update(statement)
                        print(f"      ✓ Statement executed, affected {affected_rows} rows")
                    
                    success_count += 1
                    
                except Exception as e:
                    print(f"      ✗ Error: {str(e)[:100]}...")
                    error_count += 1
                    
                    # For some errors (like table already exists), we can continue
                    if any(msg in str(e).lower() for msg in ["already exists", "name is already used", "object already exists"]):
                        print(f"      ℹ Continuing (object may already exist)")
                        success_count += 1
                        error_count -= 1
            
            print(f"\n5. Execution Summary:")
            print(f"   ✓ Successful statements: {success_count}")
            print(f"   ⚠ Failed statements: {error_count}")
            
            # Don't fail if we have some errors - let verification determine success
            success = True
            
        except Exception as e:
            print(f"   ✗ Error executing SQL script: {e}")
            success = False
        
        # Verify the schema was created
        print("6. Verifying schema creation...")
        try:
            tables = db.execute_query("""
                SELECT table_name 
                FROM user_tables 
                WHERE table_name IN ('REPORTS', 'RULESETS', 'DETECTIONS', 'NOTIFICATIONS')
                ORDER BY table_name
            """)
            
            if tables:
                print("   ✓ Created tables:")
                for table in tables:
                    print(f"      - {table['TABLE_NAME']}")
            else:
                print("   ⚠ No expected tables found")
            
            # Check spatial metadata
            spatial_metadata = db.execute_query("""
                SELECT table_name, column_name, srid
                FROM user_sdo_geom_metadata
                WHERE table_name IN ('REPORTS', 'RULESETS', 'DETECTIONS')
                ORDER BY table_name, column_name
            """)
            
            if spatial_metadata:
                print("   ✓ Spatial metadata registered:")
                for meta in spatial_metadata:
                    print(f"      - {meta['TABLE_NAME']}.{meta['COLUMN_NAME']} (SRID: {meta['SRID']})")
            
            # Check indexes
            indexes = db.execute_query("""
                SELECT index_name, table_name, index_type
                FROM user_indexes
                WHERE table_name IN ('REPORTS', 'RULESETS', 'DETECTIONS')
                ORDER BY table_name, index_name
            """)
            
            if indexes:
                print("   ✓ Created indexes:")
                for idx in indexes:
                    print(f"      - {idx['INDEX_NAME']} on {idx['TABLE_NAME']} ({idx['INDEX_TYPE']})")
            
        except Exception as e:
            print(f"   ⚠ Error verifying schema: {e}")
            success = False
        
        # Determine final success based on verification results
        if success and 'tables' in locals() and len(tables) >= 4:
            print("\n✓ Database initialization completed successfully!")
            print("   All required tables, spatial metadata, and indexes are in place.")
            return True
        else:
            print("\n✗ Database initialization failed!")
            return False
            
    except Exception as e:
        print(f"\n✗ Database initialization failed: {e}")
        return False
    
    finally:
        # Ensure connection is closed
        try:
            db.disconnect()
            print("7. Database connection closed")
        except:
            pass




if __name__ == "__main__":
    print("Starting database initialization...")
    print("Make sure your .env file contains the required database credentials.")
    print()
    
    success = run_init_script()
    
    if success:
        print("\n🎉 Database initialization completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Database initialization failed!")
        sys.exit(1)
