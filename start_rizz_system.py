#!/usr/bin/env python3
"""
Startup script for the RizzBot system
Runs the API server and starts the glasses client
"""

import subprocess
import sys
import time
import threading
import os
from pathlib import Path

def start_api_server():
    """Start the FastAPI server"""
    print("🚀 Starting RizzBot API server...")
    api_dir = Path(__file__).parent / "api_server"
    os.chdir(api_dir)
    
    # Try different ports if 8000 is busy
    ports = [8000, 8001, 8002, 8003, 8004]
    
    for port in ports:
        try:
            print(f"🔄 Trying port {port}...")
            subprocess.run([
                sys.executable, "-m", "uvicorn", "main:app", 
                "--host", "0.0.0.0", "--port", str(port), "--reload"
            ], check=True)
            break
        except subprocess.CalledProcessError as e:
            if "Address already in use" in str(e):
                print(f"⚠️  Port {port} is busy, trying next port...")
                continue
            else:
                print(f"❌ Error starting API server: {e}")
                break
        except KeyboardInterrupt:
            print("\n🛑 API server stopped")
            break
        except Exception as e:
            print(f"❌ Error starting API server: {e}")
            break

def start_rizz_client():
    """Start the rizz client for glasses"""
    print("🎧 Starting RizzClient for glasses...")
    meta_dir = Path(__file__).parent / "meta"
    os.chdir(meta_dir)
    
    try:
        # Import and start the rizz client
        sys.path.append(str(meta_dir))
        from rizz_client import start_rizz_client
        
        start_rizz_client()
        
        # Keep the client running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 RizzClient stopped")
    except Exception as e:
        print(f"❌ Error starting RizzClient: {e}")

def main():
    """Main startup function"""
    print("🎯 Starting RizzBot System...")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("api_server").exists() or not Path("meta").exists():
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Start API server in a separate thread
    api_thread = threading.Thread(target=start_api_server, daemon=True)
    api_thread.start()
    
    # Give the API server time to start
    print("⏳ Waiting for API server to start...")
    time.sleep(3)
    
    # Start the rizz client
    start_rizz_client()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 RizzBot system stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1) 