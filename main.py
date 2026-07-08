import subprocess
import time
import sys
import os

def main():
    print("====================================================================")
    print("[Launcher] Starting brownfield modernization AI agent POC...")
    print("====================================================================")
    
    # 1. Start FastAPI backend using uvicorn in a subprocess
    # Run uvicorn on port 8000
    print("[Launcher] Starting FastAPI API server on http://127.0.0.1:8000...")
    backend_cmd = [
        sys.executable, "-m", "uvicorn", "backend.api:app",
        "--host", "127.0.0.1", "--port", "8000", "--reload"
    ]
    
    backend_process = subprocess.Popen(
        backend_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    # Wait for the backend to spin up
    time.sleep(3)
    
    # 2. Start Streamlit UI
    print("[Launcher] Starting Streamlit interface on http://localhost:8501...")
    frontend_cmd = [
        sys.executable, "-m", "streamlit", "run", "frontend/app.py"
    ]
    
    try:
        # Streamlit runs in the foreground, blocking until exit
        subprocess.run(frontend_cmd, check=True)
    except KeyboardInterrupt:
        print("\n[Launcher] Shutting down services...")
    finally:
        # Clean up backend subprocess
        backend_process.terminate()
        try:
            backend_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            backend_process.kill()
        print("[Launcher] Services successfully stopped. Goodbye!")

if __name__ == "__main__":
    main()
