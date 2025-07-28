import psycopg2
import pandas as pd
from psycopg2 import sql
import os

def upload_csv_to_db(csv_file_path, table_name):
    try:
        # Read the CSV file
        print(f"📂 Reading CSV file: {csv_file_path}")
        df = pd.read_csv(csv_file_path)
        print(f"📊 Found {len(df)} rows with columns: {', '.join(df.columns)}")
        
        # Connect to Neon.tech
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(
            dbname="neondb",
            user="neondb_owner",
            password="npg_f7Lrs1OMVFjX",
            host="ep-green-field-a1hgytyd-pooler.ap-southeast-1.aws.neon.tech",
            port="5432",
            sslmode="require"
        )
        
        # Create table based on CSV columns
        with conn.cursor() as cur:
            # Generate column definitions
            print("🔧 Creating table...")
            columns = []
            for col, dtype in df.dtypes.items():
                col_clean = col.strip().lower().replace(' ', '_').replace('-', '_')
                if 'int' in str(dtype):
                    sql_type = 'INTEGER'
                elif 'float' in str(dtype):
                    sql_type = 'FLOAT'
                elif 'datetime' in str(dtype):
                    sql_type = 'TIMESTAMP'
                else:
                    sql_type = 'TEXT'
                columns.append(f'"{col_clean}" {sql_type}')
            
            # Create table (drop if exists)
            create_table_sql = f"""
            DROP TABLE IF EXISTS {table_name} CASCADE;
            CREATE TABLE {table_name} (
                {', '.join(columns)}
            );
            """
            cur.execute(create_table_sql)
            
            # Insert data in batches for better performance
            print("📤 Uploading data (this may take a moment for large files)...")
            batch_size = 1000
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i + batch_size]
                placeholders = ', '.join(['%s'] * len(batch.columns))
                columns = ', '.join([f'"{col.strip().lower().replace(" ", "_").replace("-", "_")}"' for col in batch.columns])
                values = [tuple(x) for x in batch.to_numpy()]
                
                insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                cur.executemany(insert_sql, values)
                conn.commit()
                print(f"  ✅ Uploaded {min(i + len(batch), len(df))}/{len(df)} rows...")
            
            print(f"✨ Successfully created table '{table_name}' with {len(df)} rows!")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    # Using your CSV file path and creating a table named 'pitk3'
    csv_file = r"C:\Users\MY PC\My Drive\Strong\pitk3.csv"
    table_name = "pitk3"  # Table name in the database
    
    if os.path.exists(csv_file):
        upload_csv_to_db(csv_file, table_name)
    else:
        print(f"❌ Error: File '{csv_file}' not found!")