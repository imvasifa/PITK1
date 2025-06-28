import sys
import os
import json
import logging

# Add the current directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def test_database_connection():
    """Test the database connection and table creation"""
    try:
        from app3 import db
        
        logger.info("Testing database connection...")
        cur = db.get_cursor()
        if not cur:
            logger.error("Failed to get database cursor")
            return False
            
        # Test connection
        cur.execute("SELECT 1")
        result = cur.fetchone()
        logger.info(f"Database connection test result: {result}")
        
        # Test table creation
        logger.info("Testing table creation...")
        cur.execute("""
            DROP TABLE IF EXISTS test_table;
            CREATE TABLE test_table (id SERIAL PRIMARY KEY, data JSONB);
            INSERT INTO test_table (data) VALUES ('{"test": "success"}');
            SELECT * FROM test_table;
        """)
        
        result = cur.fetchone()
        logger.info(f"Table creation test result: {result}")
        
        # Clean up
        cur.execute("DROP TABLE IF EXISTS test_table")
        db.conn.commit()
        
        return True
        
    except Exception as e:
        logger.error(f"Database test failed: {e}", exc_info=True)
        return False
    finally:
        if 'cur' in locals() and cur:
            cur.close()
        if 'db' in locals() and hasattr(db, 'conn'):
            db.conn.close()

if __name__ == "__main__":
    logger.info("Starting database tests...")
    if test_database_connection():
        logger.info("✅ All database tests passed!")
    else:
        logger.error("❌ Database tests failed")
        sys.exit(1)
