import mysql.connector
from mysql.connector import Error
import traceback

def get_connection():
    """Establishes a connection to the MySQL database with detailed error logging."""
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='django_user',
            password='yousuf123',
            database='thelab'
        )
        
        if conn.is_connected():
            print('Connected to MySQL database')
            return conn
    except Error as e:
        print(f"Database connection error: {e}")
        traceback.print_exc()  # Print the full traceback of the error
        return None
