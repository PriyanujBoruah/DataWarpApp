# updater.py
import sys
import os
import time
import subprocess
import psutil

def main():
    try:
        pid_to_kill_str, old_exe_path, new_exe_path = sys.argv[1:4]
        pid_to_kill = int(pid_to_kill_str)
    except (IndexError, ValueError):
        print(f"FATAL: Updater called with invalid arguments: {sys.argv}")
        sys.exit(1)

    # 1. Kill the old process gracefully
    try:
        if psutil.pid_exists(pid_to_kill):
            old_process = psutil.Process(pid_to_kill)
            print(f"Terminating old process (PID: {pid_to_kill})...")
            old_process.terminate()
            old_process.wait(timeout=5)
            print("Old process terminated.")
        else:
            print(f"Old process with PID {pid_to_kill} was already gone.")
    except psutil.NoSuchProcess:
        print(f"Old process with PID {pid_to_kill} was already gone (NoSuchProcess).")
    except Exception as e:
        print(f"Warning: Error during process termination: {e}")

    # Give the OS a moment to release file handles
    time.sleep(2)

    # 2. Retry loop for replacing the executable (to handle file locks)
    for i in range(5): # Retry up to 5 times
        try:
            print(f"Attempt {i+1}: Removing old executable at {old_exe_path}")
            if os.path.exists(old_exe_path):
                os.remove(old_exe_path)
            
            print("Attempting to rename new executable...")
            os.rename(new_exe_path, old_exe_path)
            
            print("File replacement successful.")
            break # Exit the loop if successful
        except PermissionError as e:
            print(f"Warning: PermissionError on attempt {i+1} - file may be locked. Retrying in 1 second...")
            print(f"    Details: {e}")
            time.sleep(1)
        except Exception as e:
            print(f"FATAL: An unexpected error occurred during file replacement: {e}")
            # If replacement fails, don't try to relaunch.
            sys.exit(1)
    else:
        # This 'else' belongs to the 'for' loop. It runs if the loop finishes without a 'break'.
        print("FATAL: Could not replace the executable after multiple attempts.")
        sys.exit(1)

    # 3. Relaunch the application
    print(f"Relaunching application from {old_exe_path}")
    subprocess.Popen([old_exe_path])
    print("Update complete. Exiting updater.")
    sys.exit(0)

if __name__ == "__main__":
    # Ensure this log file is created in a writable directory.
    # The directory of the updater script itself is a good choice.
    log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "updater-log.txt")
    try:
        with open(log_file_path, 'a') as log_file:
            sys.stdout = log_file
            sys.stderr = log_file
            print(f"\n--- Updater started at {time.ctime()} ---")
            main()
    except Exception as e:
        # If logging fails, we can't do much, but the script can still run.
        main()