import subprocess
import sys
import os
import time

def start_servers():
    """Start both the main Flask app and the notification API."""
    
    print("Starting Computer Lab Management System...")
    
    # Start the notification API in a separate process
    print("\nStarting Notification API server...")
    notif_process = subprocess.Popen(
        [sys.executable, "notification_api.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    # Wait for notification API to start
    time.sleep(2)
    
    # Check if the notification API process is still running
    if notif_process.poll() is not None:
        print("Error: Notification API failed to start.")
        print("Exit code:", notif_process.poll())
        output, _ = notif_process.communicate()
        print("Output:", output)
        return
    
    print("Notification API running on http://localhost:5050")
    
    # Start the main app in a separate process
    print("\nStarting Main Application server...")
    app_process = subprocess.Popen(
        [sys.executable, "run_app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    # Wait for main app to start
    time.sleep(2)
    
    # Check if the main app process is still running
    if app_process.poll() is not None:
        print("Error: Main Application failed to start.")
        print("Exit code:", app_process.poll())
        output, _ = app_process.communicate()
        print("Output:", output)
        notif_process.terminate()
        return
    
    print("Main Application running on http://localhost:8080")
    
    print("\nBoth servers are now running. Press Ctrl+C to stop.")
    
    try:
        # Monitor the processes and print their output
        while True:
            # Check if either process has terminated
            if notif_process.poll() is not None:
                print("Notification API server stopped unexpectedly.")
                break
            
            if app_process.poll() is not None:
                print("Main Application server stopped unexpectedly.")
                break
            
            # Read output from notification API
            notif_line = notif_process.stdout.readline().strip()
            if notif_line:
                print("[Notification API]", notif_line)
            
            # Read output from main app
            app_line = app_process.stdout.readline().strip()
            if app_line:
                print("[Main App]", app_line)
            
            # Small delay to prevent high CPU usage
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\nShutting down servers...")
    
    finally:
        # Terminate the processes
        notif_process.terminate()
        app_process.terminate()
        
        # Wait for the processes to terminate
        try:
            notif_process.wait(timeout=5)
            app_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            print("Force killing processes...")
            notif_process.kill()
            app_process.kill()
        
        print("Servers stopped.")

if __name__ == "__main__":
    start_servers() 