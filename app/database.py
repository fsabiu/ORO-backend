"""
Oracle Autonomous Database Connection Module

This module provides a Database class for connecting to Oracle Autonomous Database
using wallet-based authentication. It handles wallet extraction, connection management,
and provides methods for executing queries and managing transactions.
"""

import os
import zipfile
import tempfile
import shutil
from typing import Optional, List, Dict, Any, Union
import logging
from contextlib import contextmanager

try:
    import oracledb
except ImportError:
    raise ImportError(
        "oracledb package is required. Install it with: pip install oracledb"
    )

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Database:
    """
    Oracle Autonomous Database connection manager using wallet authentication.
    
    This class handles wallet extraction, connection management, and provides
    methods for executing SQL queries and managing database transactions.
    """
    
    def __init__(self, wallet_path: str = "db/wallet_oro.zip"):
        """
        Initialize the Database instance.
        
        Args:
            wallet_path (str): Path to the Oracle wallet zip file
        """
        self.wallet_path = wallet_path
        self.wallet_dir = None
        self.connection = None
        
        # Load database credentials from environment
        self.db_user = os.getenv('DB_USER')
        self.db_password = os.getenv('DB_PASSWORD')
        self.wallet_password = os.getenv('WALLET_PASSWORD')
        self.db_service_name = os.getenv('DB_SERVICE_NAME', 'high')
        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_port = int(os.getenv('DB_PORT', '1522'))
        
        # Validate required credentials
        if not all([self.db_user, self.db_password, self.wallet_password]):
            raise ValueError(
                "Missing required environment variables: DB_USER, DB_PASSWORD, WALLET_PASSWORD"
            )
        
        # Extract wallet if needed
        self._extract_wallet()
    
    def _extract_wallet(self) -> None:
        """
        Extract the Oracle wallet zip file to a temporary directory.
        """
        if not os.path.exists(self.wallet_path):
            raise FileNotFoundError(f"Wallet file not found: {self.wallet_path}")
        
        # Create temporary directory for wallet extraction
        self.wallet_dir = tempfile.mkdtemp(prefix="oracle_wallet_")
        
        try:
            with zipfile.ZipFile(self.wallet_path, 'r') as zip_ref:
                zip_ref.extractall(self.wallet_dir)
            logger.info(f"Wallet extracted to: {self.wallet_dir}")
        except Exception as e:
            logger.error(f"Failed to extract wallet: {e}")
            raise
    
    def _get_connection_string(self) -> str:
        """
        Generate the Oracle connection string using the extracted wallet.
        
        Returns:
            str: Oracle connection string (DSN)
        """
        # Find the tnsnames.ora file in the extracted wallet
        tnsnames_path = os.path.join(self.wallet_dir, 'tnsnames.ora')
        
        if not os.path.exists(tnsnames_path):
            raise FileNotFoundError("tnsnames.ora not found in wallet")
        
        # Read tnsnames.ora to get the connection string
        with open(tnsnames_path, 'r') as f:
            tnsnames_content = f.read()
        
        # Extract the full connection string from tnsnames.ora
        # Look for the service name and its description
        import re
        
        # Try to find the specific service name first, then fall back to _high
        target_service = self.db_service_name
        if not target_service or target_service == 'high':
            target_service = '_high'
        
        # Look for service entries that end with the target service name
        pattern = rf'(\w+{re.escape(target_service)})\s*=\s*\((.*?)\)\s*$'
        service_match = re.search(pattern, tnsnames_content, re.DOTALL | re.MULTILINE)
        
        if not service_match:
            # Fallback: look for any service ending with _high
            pattern = r'(\w+_high)\s*=\s*\((.*?)\)\s*$'
            service_match = re.search(pattern, tnsnames_content, re.DOTALL | re.MULTILINE)
        
        if not service_match:
            # Fallback: get the first service found
            pattern = r'(\w+)\s*=\s*\((.*?)\)\s*$'
            service_match = re.search(pattern, tnsnames_content, re.DOTALL | re.MULTILINE)
        
        if service_match:
            service_name = service_match.group(1)
            description = service_match.group(2)
            logger.info(f"Using service: {service_name}")
            # Return the full DSN string
            return f"({description})"
        else:
            # Fallback to service name only
            return self.db_service_name
    
    def connect(self) -> None:
        """
        Establish connection to the Oracle Autonomous Database.
        """
        try:
            # Get connection string (DSN)
            dsn = self._get_connection_string()
            
            # Establish connection using thin mode with wallet
            self.connection = oracledb.connect(
                user=self.db_user,
                password=self.db_password,
                dsn=dsn,
                config_dir=self.wallet_dir
            )
            logger.info("Successfully connected to Oracle Autonomous Database using thin mode with wallet")
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self) -> None:
        """
        Close the database connection.
        """
        if self.connection:
            try:
                self.connection.close()
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                self.connection = None
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results as a list of dictionaries.
        
        Args:
            query (str): SQL SELECT query
            params (Dict[str, Any], optional): Query parameters
            
        Returns:
            List[Dict[str, Any]]: Query results as list of dictionaries
        """
        if not self.connection:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        try:
            cursor = self.connection.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Fetch all results
            rows = cursor.fetchall()
            
            # Convert to list of dictionaries
            results = [dict(zip(columns, row)) for row in rows]
            
            cursor.close()
            logger.info(f"Query executed successfully, returned {len(results)} rows")
            
            return results
            
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    def execute_update(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        Execute an INSERT, UPDATE, or DELETE query.
        
        Args:
            query (str): SQL query
            params (Dict[str, Any], optional): Query parameters
            
        Returns:
            int: Number of affected rows
        """
        if not self.connection:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        try:
            cursor = self.connection.cursor()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            affected_rows = cursor.rowcount
            self.connection.commit()
            
            cursor.close()
            logger.info(f"Update query executed successfully, affected {affected_rows} rows")
            
            return affected_rows
            
        except Exception as e:
            logger.error(f"Error executing update query: {e}")
            self.connection.rollback()
            raise
    
    def execute_many(self, query: str, params_list: List[Dict[str, Any]]) -> int:
        """
        Execute a query multiple times with different parameters.
        
        Args:
            query (str): SQL query
            params_list (List[Dict[str, Any]]): List of parameter dictionaries
            
        Returns:
            int: Number of affected rows
        """
        if not self.connection:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        try:
            cursor = self.connection.cursor()
            cursor.executemany(query, params_list)
            
            affected_rows = cursor.rowcount
            self.connection.commit()
            
            cursor.close()
            logger.info(f"Batch query executed successfully, affected {affected_rows} rows")
            
            return affected_rows
            
        except Exception as e:
            logger.error(f"Error executing batch query: {e}")
            self.connection.rollback()
            raise
    
    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.
        
        Usage:
            with db.transaction():
                db.execute_update("INSERT INTO table ...")
                db.execute_update("UPDATE table ...")
        """
        if not self.connection:
            raise RuntimeError("Database not connected. Call connect() first.")
        
        try:
            yield self
            self.connection.commit()
            logger.info("Transaction committed successfully")
        except Exception as e:
            self.connection.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test the database connection by executing a simple query.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            result = self.execute_query("SELECT 1 as test FROM DUAL")
            return len(result) > 0 and result[0]['TEST'] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get information about a table's columns.
        
        Args:
            table_name (str): Name of the table
            
        Returns:
            List[Dict[str, Any]]: Table column information
        """
        query = """
        SELECT 
            column_name,
            data_type,
            data_length,
            nullable,
            data_default
        FROM user_tab_columns 
        WHERE table_name = UPPER(:table_name)
        ORDER BY column_id
        """
        
        return self.execute_query(query, {'table_name': table_name})
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        self._cleanup_wallet()
    
    def _cleanup_wallet(self) -> None:
        """
        Clean up the temporary wallet directory.
        """
        if self.wallet_dir and os.path.exists(self.wallet_dir):
            try:
                shutil.rmtree(self.wallet_dir)
                logger.info("Wallet cleanup completed")
            except Exception as e:
                logger.error(f"Error cleaning up wallet directory: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.disconnect()
        self._cleanup_wallet()
