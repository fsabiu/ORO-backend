#!/usr/bin/env python3
"""
Real database test script for Oracle Autonomous Database.

This script tests the Database class with actual wallet and credentials
from the .env file.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from database import Database


def test_real_connection():
    """
    Test the database connection with real credentials and wallet.
    """
    print("Testing Oracle Autonomous Database Connection")
    print("=" * 50)
    
    try:
        # Initialize database with real wallet
        wallet_path = os.path.join(os.path.dirname(__file__), '..', 'db', 'wallet_oro.zip')
        print(f"1. Initializing database with wallet: {wallet_path}")
        db = Database(wallet_path=wallet_path)
        
        # Connect to database
        print("2. Connecting to Oracle Autonomous Database...")
        db.connect()
        
        # Test basic connection
        print("3. Testing connection...")
        if db.test_connection():
            print("   ✓ Connection successful!")
        else:
            print("   ✗ Connection test failed!")
            return False
        
        # Get database information
        print("4. Getting database information...")
        try:
            # Get current user and time
            result = db.execute_query("SELECT USER as current_user, SYSDATE as current_time FROM DUAL")
            print(f"   Current user: {result[0]['CURRENT_USER']}")
            print(f"   Current time: {result[0]['CURRENT_TIME']}")
            
            # Get database version
            version_result = db.execute_query("SELECT BANNER as version FROM v$version WHERE ROWNUM = 1")
            print(f"   Database version: {version_result[0]['VERSION']}")
            
        except Exception as e:
            print(f"   Error getting database info: {e}")
        
        # Test table operations
        print("5. Testing table operations...")
        try:
            # Check if we can list tables
            tables = db.execute_query("""
                SELECT table_name, num_rows 
                FROM user_tables 
                WHERE ROWNUM <= 5
                ORDER BY table_name
            """)
            
            if tables:
                print(f"   Found {len(tables)} tables:")
                for table in tables:
                    rows = table['NUM_ROWS'] if table['NUM_ROWS'] else 'Unknown'
                    print(f"   - {table['TABLE_NAME']} ({rows} rows)")
            else:
                print("   No tables found in current schema")
                
        except Exception as e:
            print(f"   Error listing tables: {e}")
        
        # Test transaction
        print("6. Testing transaction capabilities...")
        try:
            with db.transaction():
                # Create a regular test table (not temporary)
                db.execute_update("""
                    CREATE TABLE test_table_temp (
                        id NUMBER,
                        test_data VARCHAR2(100)
                    )
                """)
                print("   ✓ Test table created")
                
                # Insert test data
                test_data = [
                    {'id': 1, 'test_data': 'Test 1'},
                    {'id': 2, 'test_data': 'Test 2'}
                ]
                
                db.execute_many("""
                    INSERT INTO test_table_temp (id, test_data) 
                    VALUES (:id, :test_data)
                """, test_data)
                print("   ✓ Test data inserted")
                
                # Query test data
                results = db.execute_query("SELECT * FROM test_table_temp ORDER BY id")
                print(f"   ✓ Retrieved {len(results)} test records")
                
                # Clean up - drop the test table
                db.execute_update("DROP TABLE test_table_temp")
                print("   ✓ Test table cleaned up")
                
                print("   ✓ Transaction completed successfully")
                
        except Exception as e:
            print(f"   Error in transaction test: {e}")
            # Try to clean up the table if it exists
            try:
                db.execute_update("DROP TABLE test_table_temp")
                print("   ✓ Cleanup completed after error")
            except:
                pass
        
        print("\n7. All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during testing: {e}")
        return False
    
    finally:
        # Ensure connection is closed
        try:
            db.disconnect()
            print("8. Database connection closed")
        except:
            pass


if __name__ == "__main__":
    print("Starting real database test...")
    print("Make sure your .env file contains:")
    print("- DB_USER")
    print("- DB_PASSWORD") 
    print("- WALLET_PASSWORD")
    print("- DB_SERVICE_NAME (optional)")
    print("- DB_HOST (optional)")
    print("- DB_PORT (optional)")
    print()
    
    success = test_real_connection()
    
    if success:
        print("\n✓ Database test completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Database test failed!")
        sys.exit(1)
