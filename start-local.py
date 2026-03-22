#!/usr/bin/env python
"""
Simple script to run both servers for local development
"""
import subprocess
import sys
import os
import time

def main():
    print("=" * 60)
    print("Starting Data Dictionary - Local Development")
    print("=" * 60)
    print()
    
    # Set the DATABASE environment variable for the API
    os.environ['DATABASE'] = '../data/dictionary.db'
    
    processes = []
    
    try:
        # Start Flask API server
        print("Starting Flask API server on port 5001...")
        api_process = subprocess.Popen(
            [sys.executable, 'app.py'],
            cwd='api',
            env=os.environ.copy()
        )
        processes.append(('API Server', api_process))
        time.sleep(2)
        
        # Start Python HTTP server for frontend
        print("Starting web server on port 8000...")
        web_process = subprocess.Popen(
            [sys.executable, '-m', 'http.server', '8000']
        )
        processes.append(('Web Server', web_process))
        time.sleep(1)
        
        print()
        print("=" * 60)
        print("Data Dictionary is now running!")
        print("=" * 60)
        print()
        print("Public view:  http://localhost:8000/")
        print("Admin view:   http://localhost:8000/admin/")
        print("API:          http://localhost:5001/api")
        print()
        print("Press Ctrl+C to stop all servers")
        print("=" * 60)
        print()
        
        # Wait for processes
        while True:
            time.sleep(1)
            # Check if any process died
            for name, proc in processes:
                if proc.poll() is not None:
                    print(f"\n{name} stopped unexpectedly!")
                    raise KeyboardInterrupt
                    
    except KeyboardInterrupt:
        print("\n\nStopping servers...")
        for name, proc in processes:
            print(f"Stopping {name}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("All servers stopped.")

if __name__ == '__main__':
    main()
