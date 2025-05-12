import requests
import time
import threading
from app import app

def check_notifications():
    """Background task to periodically check for new notifications."""
    print("Starting notification checker background task...")
    
    # Wait for 15 seconds to allow the server to start
    time.sleep(15)
    
    while True:
        try:
            # Send a request to the notification check endpoint
            response = requests.get('http://localhost:8080/check_all_notifications')
            if response.status_code == 200:
                data = response.json()
                print(f"Notification check: {data.get('message')}")
            else:
                print(f"Error checking notifications: {response.status_code}")
        except Exception as e:
            print(f"Exception in notification checker: {e}")
        
        # Sleep for 5 minutes
        time.sleep(300)

if __name__ == '__main__':
    # Create database tables for notifications if they don't exist
    from app import create_notifications_table
    create_notifications_table()
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=8080, debug=True) 