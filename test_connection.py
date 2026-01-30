#!/usr/bin/env python3
"""Test FileMaker ODBC connection."""

import pyodbc
import getpass

def test_connection():
    print("FileMaker ODBC Connection Test")
    print("=" * 40)

    dsn = input("DSN name [FileMaker]: ").strip() or "FileMaker"
    username = input("Username: ").strip()
    password = getpass.getpass("Password: ")

    conn_string = f"DSN={dsn};UID={username};PWD={password}"

    print(f"\nConnecting to DSN={dsn} as {username}...")

    try:
        conn = pyodbc.connect(conn_string)
        print("Connected successfully!\n")

        cursor = conn.cursor()

        # List tables
        print("Available tables:")
        print("-" * 40)
        tables = [t.table_name for t in cursor.tables() if t.table_type == "TABLE"]
        for table in tables[:20]:  # Show first 20
            print(f"  - {table}")

        if len(tables) > 20:
            print(f"  ... and {len(tables) - 20} more")

        print(f"\nTotal tables: {len(tables)}")

        conn.close()
        print("\nConnection test passed!")

        # Save credentials hint
        print("\n" + "=" * 40)
        print("To use with MCP server, set these environment variables:")
        print(f"  FILEMAKER_DSN={dsn}")
        print(f"  FILEMAKER_USER={username}")
        print(f"  FILEMAKER_PASS=<your_password>")

    except pyodbc.Error as e:
        print(f"\nConnection failed: {e}")
        return False

    return True

if __name__ == "__main__":
    test_connection()
