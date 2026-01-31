#!/usr/bin/env python3
"""
FileMaker to Google Sheets Report Generator

Pulls reports from FileMaker databases and updates Google Sheets automatically.
"""

import os
import json
import pyodbc
from datetime import datetime, timedelta
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Configuration
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "1g6sFBwMmOiBSaGrHpj6NhddET_Pn0q99R880Ye5WPwk")
CREDENTIALS_FILE = Path(__file__).parent / "google_credentials.json"

# FileMaker connection settings
FM_DSN = os.environ.get("FILEMAKER_DSN", "Filemaker")
FM_USER = os.environ.get("FILEMAKER_USER", "")
FM_PASS = os.environ.get("FILEMAKER_PASS", "")


class FileMakerReports:
    """Generate reports from FileMaker databases."""

    def __init__(self):
        self.connections = {}

    def get_connection(self, database: str) -> pyodbc.Connection:
        """Get or create a connection to a FileMaker database."""
        if database not in self.connections:
            conn_str = f"DSN={FM_DSN};UID={FM_USER};PWD={FM_PASS};ServerDataSource={database}"
            self.connections[database] = pyodbc.connect(conn_str)
        return self.connections[database]

    def close_all(self):
        """Close all database connections."""
        for conn in self.connections.values():
            conn.close()
        self.connections = {}

    def get_daily_appointments(self, date: str = None) -> dict:
        """Get appointment statistics for a given date."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        conn = self.get_connection("Appointments")
        cursor = conn.cursor()

        # Get all appointments for the day and count in Python
        # (FileMaker ODBC doesn't support GROUP BY well)
        cursor.execute(
            "SELECT doctor, examtype FROM Appointments WHERE dateappt = ?",
            (date,)
        )
        rows = cursor.fetchall()

        total = len(rows)

        # Count by doctor
        by_doctor = {}
        for row in rows:
            doc = row[0] or "Unassigned"
            by_doctor[doc] = by_doctor.get(doc, 0) + 1

        # Count by exam type
        by_type = {}
        for row in rows:
            exam = row[1] or "Unspecified"
            by_type[exam] = by_type.get(exam, 0) + 1

        return {
            "date": date,
            "total_appointments": total,
            "by_doctor": by_doctor,
            "by_exam_type": by_type
        }

    def get_appointment_range(self, start_date: str, end_date: str) -> list:
        """Get daily appointment counts for a date range."""
        conn = self.get_connection("Appointments")
        cursor = conn.cursor()

        # FileMaker ODBC doesn't support GROUP BY, so count in Python
        cursor.execute(
            "SELECT dateappt FROM Appointments WHERE dateappt BETWEEN ? AND ?",
            (start_date, end_date)
        )

        # Count by date
        counts = {}
        for row in cursor.fetchall():
            date_str = str(row[0])
            counts[date_str] = counts.get(date_str, 0) + 1

        return [{"date": d, "count": c} for d, c in sorted(counts.items())]

    def get_patient_stats(self) -> dict:
        """Get patient statistics."""
        conn = self.get_connection("Patients")
        cursor = conn.cursor()

        # This is a simplified version - adjust based on actual data
        stats = {}

        # Count patients by getting a sample and counting
        # (Full count may be too slow for large tables)
        try:
            cursor.execute('SELECT COUNT(*) FROM Patients WHERE "Patient ID#" IS NOT NULL')
            stats["total_patients"] = cursor.fetchone()[0]
        except:
            stats["total_patients"] = "Error counting"

        # New patients this month
        first_of_month = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        try:
            cursor.execute(
                'SELECT COUNT(*) FROM Patients WHERE "Date Entered" >= ?',
                (first_of_month,)
            )
            stats["new_this_month"] = cursor.fetchone()[0]
        except:
            stats["new_this_month"] = "N/A"

        # Recalls due this month
        end_of_month = (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        try:
            cursor.execute(
                'SELECT COUNT(*) FROM Patients WHERE "Recall Date" BETWEEN ? AND ?',
                (first_of_month, end_of_month.strftime("%Y-%m-%d"))
            )
            stats["recalls_due"] = cursor.fetchone()[0]
        except:
            stats["recalls_due"] = "N/A"

        return stats

    def get_transaction_summary(self, start_date: str = None, end_date: str = None) -> dict:
        """Get transaction summary for a date range."""
        if start_date is None:
            start_date = datetime.now().replace(day=1).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        conn = self.get_connection("Transactions")
        cursor = conn.cursor()

        summary = {
            "start_date": start_date,
            "end_date": end_date,
        }

        # Count transactions
        try:
            cursor.execute(
                'SELECT COUNT(*) FROM Transactions WHERE "Transaction Date" BETWEEN ? AND ?',
                (start_date, end_date)
            )
            summary["transaction_count"] = cursor.fetchone()[0]
        except Exception as e:
            summary["transaction_count"] = f"Error: {e}"

        return summary


class GoogleSheetsUpdater:
    """Update Google Sheets with report data."""

    def __init__(self, credentials_file: Path, sheet_id: str):
        self.sheet_id = sheet_id
        self.client = None
        self.spreadsheet = None

        if credentials_file.exists():
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = Credentials.from_service_account_file(
                str(credentials_file),
                scopes=scopes
            )
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(sheet_id)
        else:
            print(f"Warning: Credentials file not found: {credentials_file}")
            print("Google Sheets updates will be skipped.")

    def get_or_create_worksheet(self, title: str, rows: int = 1000, cols: int = 26):
        """Get existing worksheet or create new one."""
        if not self.spreadsheet:
            return None

        try:
            return self.spreadsheet.worksheet(title)
        except gspread.WorksheetNotFound:
            return self.spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)

    def update_daily_summary(self, report_data: dict):
        """Update the daily summary sheet."""
        if not self.spreadsheet:
            print("Skipping Google Sheets update (no credentials)")
            return

        worksheet = self.get_or_create_worksheet("Daily Summary")

        # Find or add today's row
        today = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Headers
        headers = ["Date", "Last Updated", "Total Appointments", "New Patients", "Recalls Due", "Transactions"]
        worksheet.update("A1:F1", [headers])

        # Find existing row for today or append
        try:
            cell = worksheet.find(today)
            row_num = cell.row
        except:
            # Append new row
            row_num = len(worksheet.get_all_values()) + 1

        # Update data
        row_data = [
            today,
            timestamp,
            report_data.get("appointments", {}).get("total_appointments", 0),
            report_data.get("patients", {}).get("new_this_month", 0),
            report_data.get("patients", {}).get("recalls_due", 0),
            report_data.get("transactions", {}).get("transaction_count", 0)
        ]

        worksheet.update(f"A{row_num}:F{row_num}", [row_data])
        print(f"Updated Daily Summary row {row_num}")

    def update_appointments_detail(self, appointments_data: dict):
        """Update detailed appointments sheet."""
        if not self.spreadsheet:
            return

        worksheet = self.get_or_create_worksheet("Appointments Detail")

        today = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H:%M:%S")

        # Headers
        headers = ["Date", "Time Updated", "Doctor", "Exam Type", "Count"]
        worksheet.update("A1:E1", [headers])

        # Clear old data for today and add new
        rows = []

        # By doctor
        for doctor, count in appointments_data.get("by_doctor", {}).items():
            rows.append([today, timestamp, doctor, "ALL", count])

        # By exam type
        for exam_type, count in appointments_data.get("by_exam_type", {}).items():
            rows.append([today, timestamp, "ALL", exam_type, count])

        if rows:
            # Find starting row (after header)
            start_row = 2
            worksheet.update(f"A{start_row}:E{start_row + len(rows) - 1}", rows)
            print(f"Updated Appointments Detail with {len(rows)} rows")


def run_reports(update_sheets: bool = True):
    """Run all reports and optionally update Google Sheets."""
    print("=" * 50)
    print(f"FileMaker Reports - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    fm = FileMakerReports()

    try:
        # Gather all report data
        print("\nGathering appointment data...")
        appointments = fm.get_daily_appointments()
        print(f"  Total appointments today: {appointments['total_appointments']}")

        print("\nGathering patient stats...")
        patients = fm.get_patient_stats()
        print(f"  Total patients: {patients.get('total_patients', 'N/A')}")
        print(f"  New this month: {patients.get('new_this_month', 'N/A')}")

        print("\nGathering transaction summary...")
        transactions = fm.get_transaction_summary()
        print(f"  Transactions this month: {transactions.get('transaction_count', 'N/A')}")

        report_data = {
            "appointments": appointments,
            "patients": patients,
            "transactions": transactions,
            "generated_at": datetime.now().isoformat()
        }

        # Update Google Sheets
        if update_sheets:
            print("\nUpdating Google Sheets...")
            sheets = GoogleSheetsUpdater(CREDENTIALS_FILE, GOOGLE_SHEET_ID)
            sheets.update_daily_summary(report_data)
            sheets.update_appointments_detail(appointments)
            print("Google Sheets updated successfully!")

        # Save local copy
        report_file = Path(__file__).parent / "latest_report.json"
        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2, default=str)
        print(f"\nLocal report saved to: {report_file}")

        return report_data

    finally:
        fm.close_all()


if __name__ == "__main__":
    import sys

    update_sheets = "--no-sheets" not in sys.argv
    run_reports(update_sheets=update_sheets)
