#!/usr/bin/env python3
"""
Auto-launcher for FileMaker Reports

This script:
1. Checks if FileMaker is running
2. Opens FileMaker with Open.fp7 if not
3. Waits for ODBC to become available
4. Runs the reports and updates Google Sheets
"""

import subprocess
import time
import sys
import os
import pyodbc
from pathlib import Path
from datetime import datetime

# Paths - adjust these if needed
FILEMAKER_EXE = r"C:\Program Files (x86)\FileMaker\FileMaker Pro 9\FileMaker Pro.exe"
OPEN_DATABASE = r"C:\Users\CL ROOM OP\OneDrive - Professional Eyecare\Desktop\test\Open.fp7"

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))


def is_filemaker_running() -> bool:
    """Check if FileMaker Pro is running."""
    try:
        output = subprocess.check_output(
            'tasklist /FI "IMAGENAME eq FileMaker Pro.exe"',
            shell=True,
            text=True
        )
        return "FileMaker Pro.exe" in output
    except:
        return False


def is_odbc_available() -> bool:
    """Check if ODBC connection is available."""
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")

    dsn = os.environ.get("FILEMAKER_DSN", "Filemaker")
    user = os.environ.get("FILEMAKER_USER", "")
    pwd = os.environ.get("FILEMAKER_PASS", "")

    try:
        conn = pyodbc.connect(
            f"DSN={dsn};UID={user};PWD={pwd};ServerDataSource=Patients",
            timeout=5
        )
        conn.close()
        return True
    except:
        return False


def open_filemaker():
    """Open FileMaker with the Open.fp7 database."""
    print(f"Opening FileMaker Pro...")

    if not Path(FILEMAKER_EXE).exists():
        print(f"ERROR: FileMaker not found at {FILEMAKER_EXE}")
        print("Please update FILEMAKER_EXE path in this script.")
        return False

    if not Path(OPEN_DATABASE).exists():
        print(f"ERROR: Database not found at {OPEN_DATABASE}")
        print("Please update OPEN_DATABASE path in this script.")
        return False

    # Open FileMaker with the database
    subprocess.Popen([FILEMAKER_EXE, OPEN_DATABASE])
    return True


def wait_for_odbc(max_wait: int = 120) -> bool:
    """Wait for ODBC connection to become available."""
    print("Waiting for ODBC connection...")

    start_time = time.time()
    while time.time() - start_time < max_wait:
        if is_odbc_available():
            print("ODBC connection ready!")
            return True

        elapsed = int(time.time() - start_time)
        print(f"  Waiting... ({elapsed}s)", end="\r")
        time.sleep(5)

    print(f"\nTimeout after {max_wait} seconds")
    return False


def main():
    print("=" * 60)
    print(f"FileMaker Report Auto-Launcher")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Check if FileMaker is already running
    if is_filemaker_running():
        print("FileMaker Pro is already running.")
    else:
        print("FileMaker Pro is not running.")
        if not open_filemaker():
            print("Failed to start FileMaker Pro.")
            sys.exit(1)

    # Wait for ODBC to be available
    # Give FileMaker time to load databases
    print("\nWaiting 10 seconds for FileMaker to initialize...")
    time.sleep(10)

    if not wait_for_odbc():
        print("\nERROR: Could not connect to FileMaker via ODBC.")
        print("Please check:")
        print("  1. FileMaker is running with databases open")
        print("  2. ODBC sharing is enabled in each database")
        print("  3. Credentials in .env are correct")
        sys.exit(1)

    # Run the reports
    print("\n" + "=" * 60)
    print("Running reports...")
    print("=" * 60 + "\n")

    from filemaker_reports import run_reports

    try:
        report_data = run_reports(update_sheets=True)
        print("\n" + "=" * 60)
        print("Reports completed successfully!")
        print("=" * 60)
    except Exception as e:
        print(f"\nERROR running reports: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
