import mysql.connector

# Database connection parameters
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "sysarch"
}

try:
    # Create connection
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    print("Connected to database successfully.")
    
    # SQL query to alter the computer_status table
    sql = """
    ALTER TABLE computer_status 
    MODIFY COLUMN status ENUM('vacant', 'occupied', 'in_class', 'maintenance') NOT NULL
    """
    
    # Execute the query
    cursor.execute(sql)
    conn.commit()
    
    print("Table computer_status updated successfully to include 'maintenance' status.")
    
except mysql.connector.Error as err:
    print(f"Error updating table: {err}")
    
finally:
    # Close connection
    if 'cursor' in locals():
        cursor.close()
    if 'conn' in locals():
        conn.close() 