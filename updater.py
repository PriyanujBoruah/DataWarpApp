# updater.py
import sys
import os
import time
import subprocess
import psutil  # Make sure you have run: pip install psutil

def main():
    try:
        # Command line arguments passed from the main app
        pid_to_kill_str, old_exe_path, new_exe_path = sys.argv[1:4]
        pid_to_kill = int(pid_to_kill_str)
    except (IndexError, ValueError):
        print("Usage: updater.py <pid> <old_exe_path> <new_exe_path>")
        sys.exit(1)

    # 1. Kill the old process gracefully
    try:
        if psutil.pid_exists(pid_to_kill):
            old_process = psutil.Process(pid_to_kill)
            print(f"Terminating old process (PID: {pid_to_kill})...")
            old_process.terminate()
            # Wait for it to die
            old_process.wait(timeout=5)
    except psutil.NoSuchProcess:
        print(f"Old process with PID {pid_to_kill} already gone.")
    except Exception as e:
        print(f"Error terminating process: {e}")
        # Continue anyway, it might have already exited

    # Give the OS a moment to release file handles
    time.sleep(2)

    # 2. Replace the old executable with the new one
    try:
        print(f"Replacing {old_exe_path} with {new_exe_path}")
        if os.path.exists(old_exe_path):
             os.remove(old_exe_path)
        else:
             print(f"Warning: Old executable {old_exe_path} not found, proceeding anyway.")
        os.rename(new_exe_path, old_exe_path)
        print("File replacement successful.")
    except Exception as e:
        print(f"FATAL: Error replacing executable: {e}")
        # Attempt to relaunch the old exe if replacement fails but it still exists
        if os.path.exists(old_exe_path):
            subprocess.Popen([old_exe_path])
        sys.exit(1)

    # 3. Relaunch the application
    print(f"Relaunching application from {old_exe_path}")
    subprocess.Popen([old_exe_path])
    print("Update complete. Exiting updater.")
    sys.exit(0)

if __name__ == "__main__":
    # For debugging, you can create a log file.
    # This helps see what the updater is doing since it runs invisibly.
    log_file_path = os.path.join(os.path.dirname(sys.executable), "updater-log.txt")
    try:
        with open(log_file_path, 'a') as log_file:
            # Redirect stdout and stderr to the log file
            sys.stdout = log_file
            sys.stderr = log_file
            print(f"\n--- Updater started at {time.ctime()} with args: {sys.argv} ---")
            main()
    except Exception as e:
        # Fallback if logging fails
        print(f"Updater failed to initialize logging: {e}")
        main()