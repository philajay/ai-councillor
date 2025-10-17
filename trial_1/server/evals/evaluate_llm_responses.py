import asyncio
import os
import subprocess
import time
import sys
import argparse
from test_chat_interface import test_chat_endpoint

# --- Configuration ---
LOG_FILE = "/Users/ajay/2.0/cu/scraper/trial_1/server/evals/server.log"
SERVER_STARTUP_TIME = 5  # seconds to wait for the server to start

# --- Helper Functions ---

def start_server():
    """Starts the Uvicorn server as a background process and logs its output."""
    print("--- Starting Server ---")
    # Ensure the evals directory exists
    os.makedirs("evals", exist_ok=True)
    
    # Open the log file in write mode to clear it
    log_handle = open(LOG_FILE, "w")
    
    # Get the current environment and add PYTHONUNBUFFERED
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    
    # Start the server process using the current python executable
    process = subprocess.Popen(
        ["/Users/ajay/2.0/cu/scraper/.venv/bin/python", "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8080"],
        stdout=log_handle,
        stderr=log_handle,
        text=True,
        env=env
    )
    
    print(f"Server process started with PID: {process.pid}. Waiting {SERVER_STARTUP_TIME}s for it to initialize...")
    time.sleep(SERVER_STARTUP_TIME)
    print("Server should be ready.")
    return process, log_handle

def stop_server(process, log_handle):
    """Stops the Uvicorn server process."""
    print("--- Stopping Server ---")
    process.terminate()
    try:
        process.wait(timeout=5)
        print(f"Server process {process.pid} terminated.")
    except subprocess.TimeoutExpired:
        print(f"Server process {process.pid} did not terminate gracefully. Killing.")
        process.kill()
    time.sleep(1) # Allow time for logs to flush
    log_handle.close()

# --- Main Execution ---

async def main():
    """Main function to run the evaluation suite."""
    parser = argparse.ArgumentParser(description="Run evaluation test suite.")
    parser.add_argument("-n", "--runs", type=int, default=1, help="Number of times to run the test case.")
    args = parser.parse_args()

    # Clear log files for a clean run
    if os.path.exists(LOG_FILE):
        open(LOG_FILE, "w").close()
    
    client_log_file = "evals/client_events.log"
    if os.path.exists(client_log_file):
        open(client_log_file, "w").close()

    server_process, log_handle = start_server()
    
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    for i in range(args.runs):
        print(f"\n{'='*20} RUNNING TEST ITERATION {i + 1}/{args.runs} {'='*20}")
        test_passed = False
        error_message = ""

        try:
            with open(client_log_file, "a") as f:
                f.write(f"\n{'='*20} TEST ITERATION {i + 1}/{args.runs} {'='*20}\n")
                sys.stdout = f
                sys.stderr = f
                await test_chat_endpoint()
            test_passed = True

        except AssertionError as e:
            error_message = f"Error: {e}"
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

            if test_passed:
                print(f"--- ITERATION {i + 1}: PASSED ---")
            else:
                print(f"--- ITERATION {i + 1}: FAILED ---")
                print(error_message)
                break  # Exit loop on failure

    # Stop the server at the very end
    if server_process and server_process.poll() is None:
        print("--- Evaluation finished. Stopping server. ---")
        stop_server(server_process, log_handle)


if __name__ == "__main__":
    asyncio.run(main())