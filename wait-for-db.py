import time
import psycopg2
from app.core.config import settings

def wait_for_db():
    max_retries = 30
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Parse DATABASE_URL to get connection parameters
            db_url = settings.database_url
            # Simple parsing for postgresql://user:password@host:port/dbname
            if db_url.startswith('postgresql://'):
                # Remove protocol
                db_url = db_url[13:]
                # Split user:password@host:port/dbname
                auth_host = db_url.split('@')
                if len(auth_host) == 2:
                    user_pass = auth_host[0].split(':')
                    host_port_db = auth_host[1].split('/')
                    host_port = host_port_db[0].split(':')
                    
                    user = user_pass[0]
                    password = user_pass[1] if len(user_pass) > 1 else ''
                    host = host_port[0]
                    port = int(host_port[1]) if len(host_port) > 1 else 5432
                    dbname = host_port_db[1] if len(host_port_db) > 1 else 'postgres'
                    
                    # Try to connect
                    conn = psycopg2.connect(
                        host=host,
                        port=port,
                        user=user,
                        password=password,
                        dbname=dbname
                    )
                    conn.close()
                    print("Database is ready!")
                    return True
                    
        except Exception as e:
            print(f"Database not ready yet (attempt {retry_count + 1}/{max_retries}): {e}")
            retry_count += 1
            time.sleep(2)
    
    print("Database failed to become ready")
    return False

if __name__ == "__main__":
    wait_for_db()