#!/usr/bin/env python3
"""
Migration script to add area_of_interest spatial metadata.

This script adds the missing spatial metadata registration and index
for the area_of_interest column in the REPORTS table.
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from database import Database


def migrate_area_of_interest():
    """
    Add spatial metadata and index for area_of_interest column.
    """
    print("ORO Backend - Area of Interest Migration")
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
        
        # Check if metadata already exists
        print("2. Checking existing spatial metadata...")
        existing_metadata = db.execute_query("""
            SELECT table_name, column_name
            FROM user_sdo_geom_metadata
            WHERE table_name = 'REPORTS' AND column_name = 'area_of_interest'
        """)
        
        if existing_metadata:
            print("   ℹ Spatial metadata already exists for area_of_interest")
        else:
            print("   ✓ No existing metadata found")
            
            # Add spatial metadata
            print("3. Adding spatial metadata for area_of_interest...")
            try:
                db.execute_update("""
                    INSERT INTO USER_SDO_GEOM_METADATA (TABLE_NAME, COLUMN_NAME, DIMINFO, SRID)
                    VALUES ('REPORTS', 'area_of_interest', 
                            SDO_DIM_ARRAY(
                                SDO_DIM_ELEMENT('X', -180, 180, 0.005), 
                                SDO_DIM_ELEMENT('Y', -90, 90, 0.005)
                            ), 
                            4326)
                """)
                print("   ✓ Spatial metadata added successfully!")
            except Exception as e:
                print(f"   ✗ Error adding spatial metadata: {e}")
                return False
        
        # Check if index already exists
        print("4. Checking existing spatial indexes...")
        existing_indexes = db.execute_query("""
            SELECT index_name
            FROM user_indexes
            WHERE table_name = 'REPORTS' AND index_name = 'REPORTS_AREA_OF_INTEREST_IDX'
        """)
        
        if existing_indexes:
            print("   ℹ Spatial index already exists for area_of_interest")
        else:
            print("   ✓ No existing index found")
            
            # Add spatial index
            print("5. Creating spatial index for area_of_interest...")
            try:
                db.execute_update("""
                    CREATE INDEX REPORTS_AREA_OF_INTEREST_IDX 
                    ON REPORTS(area_of_interest) 
                    INDEXTYPE IS MDSYS.SPATIAL_INDEX_V2
                """)
                print("   ✓ Spatial index created successfully!")
            except Exception as e:
                print(f"   ✗ Error creating spatial index: {e}")
                # Non-critical error - continue
        
        # Verify the migration
        print("6. Verifying migration...")
        metadata = db.execute_query("""
            SELECT table_name, column_name, srid
            FROM user_sdo_geom_metadata
            WHERE table_name = 'REPORTS'
            ORDER BY column_name
        """)
        
        if metadata:
            print("   ✓ Current spatial metadata for REPORTS table:")
            for meta in metadata:
                print(f"      - {meta['COLUMN_NAME']} (SRID: {meta['SRID']})")
        
        print("\n✓ Migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        return False
    
    finally:
        # Ensure connection is closed
        try:
            db.disconnect()
            print("7. Database connection closed")
        except:
            pass


if __name__ == "__main__":
    print("Starting migration...")
    print()
    
    success = migrate_area_of_interest()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)

