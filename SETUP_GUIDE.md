# FileMaker MCP Server - Complete Setup Guide

## Quick Reference

| Item | Value |
|------|-------|
| GitHub Repo | https://github.com/aandersen2323/filemaker-mcp-server |
| Google Sheet | https://docs.google.com/spreadsheets/d/1g6sFBwMmOiBSaGrHpj6NhddET_Pn0q99R880Ye5WPwk |
| FileMaker Login | manager / eynner |
| DSN Name | Filemaker |
| 32-bit Python | `C:\Users\CL ROOM OP\AppData\Local\Programs\Python\Python312-32\python.exe` |
| Project Folder | `C:\Users\CL ROOM OP\OneDrive - Professional Eyecare\Desktop\test` |

---

## What's Already Done

- [x] MCP Server created (`filemaker_mcp_server.py`)
- [x] ODBC connection working to all 8 databases
- [x] 32-bit Python virtual environment (`venv32`)
- [x] Report generation script (`filemaker_reports.py`)
- [x] Auto-launcher script (`run_reports.py`)
- [x] Google Sheets libraries installed
- [x] All code pushed to GitHub

---

## What's Still Needed

### 1. Google Cloud Credentials (5 minutes)

**Step 1: Create Google Cloud Project**
1. Go to: https://console.cloud.google.com/
2. Click "Select a project" → "New Project"
3. Name it: `filemaker-reports`
4. Click "Create"

**Step 2: Enable Google Sheets API**
1. Go to: https://console.cloud.google.com/apis/library/sheets.googleapis.com
2. Click "Enable"

**Step 3: Create Service Account**
1. Go to: https://console.cloud.google.com/iam-admin/serviceaccounts
2. Click "Create Service Account"
3. Name: `filemaker-reports`
4. Click "Create and Continue"
5. Skip role selection, click "Continue"
6. Click "Done"

**Step 4: Download JSON Key**
1. Click on the service account you created
2. Go to "Keys" tab
3. Click "Add Key" → "Create new key"
4. Choose "JSON"
5. Save as: `C:\Users\CL ROOM OP\OneDrive - Professional Eyecare\Desktop\test\google_credentials.json`

**Step 5: Share Google Sheet with Service Account**
1. Open your Google Sheet
2. Click "Share"
3. Add the service account email (e.g., `filemaker-reports@your-project.iam.gserviceaccount.com`)
4. Give "Editor" access

---

### 2. Claude Desktop Integration

Edit `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "filemaker": {
      "command": "C:\\Users\\CL ROOM OP\\OneDrive - Professional Eyecare\\Desktop\\test\\venv32\\Scripts\\python.exe",
      "args": ["C:\\Users\\CL ROOM OP\\OneDrive - Professional Eyecare\\Desktop\\test\\filemaker_mcp_server.py"]
    }
  }
}
```

Then restart Claude Desktop.

---

### 3. Schedule Daily Reports (Windows Task Scheduler)

1. Open Task Scheduler (search "Task Scheduler" in Windows)
2. Click "Create Basic Task"
3. Name: `FileMaker Daily Report`
4. Trigger: Daily at your preferred time (e.g., 6:00 AM)
5. Action: Start a program
6. Program: `C:\Users\CL ROOM OP\OneDrive - Professional Eyecare\Desktop\test\run_daily_report.bat`
7. Finish

---

## How to Run Reports Manually

### Option 1: Double-click batch file
```
C:\Users\CL ROOM OP\OneDrive - Professional Eyecare\Desktop\test\run_daily_report.bat
```

### Option 2: Command line
```bash
cd "C:\Users\CL ROOM OP\OneDrive - Professional Eyecare\Desktop\test"
venv32\Scripts\python.exe run_reports.py
```

### Option 3: Without Google Sheets update
```bash
venv32\Scripts\python.exe filemaker_reports.py --no-sheets
```

---

## Files in Project

| File | Purpose |
|------|---------|
| `filemaker_mcp_server.py` | MCP server for Claude Desktop |
| `filemaker_reports.py` | Report generation + Google Sheets |
| `run_reports.py` | Auto-opens FileMaker, then runs reports |
| `run_daily_report.bat` | Windows batch file for Task Scheduler |
| `test_connection.py` | Test ODBC connection |
| `.env` | Credentials (git-ignored) |
| `google_credentials.json` | Google API key (you need to create this) |
| `FIELD_REFERENCE.md` | FileMaker field names reference |

---

## Troubleshooting

### "Connection refused"
- FileMaker Pro must be running
- ODBC sharing must be enabled in each database

### "Out of Memory"
- Large tables need specific columns, not SELECT *
- The scripts already handle this

### "Google Sheets not updating"
- Check `google_credentials.json` exists
- Verify service account has Editor access to sheet

### "Module not found"
- Make sure using 32-bit Python from venv32
- Run: `venv32\Scripts\pip.exe install -r requirements.txt`

---

## Future: Web Interface Chatbot

Still to be built:
- Streamlit or Flask web interface
- Direct chat with FileMaker data
- Can be added later on top of existing MCP server

---

## Support

GitHub Issues: https://github.com/aandersen2323/filemaker-mcp-server/issues
