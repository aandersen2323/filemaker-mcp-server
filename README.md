# FileMaker 9 Pro MCP Server

An MCP (Model Context Protocol) server that connects to FileMaker 9 Pro databases via ODBC, enabling AI assistants like Claude to query and interact with your FileMaker data.

## Prerequisites

### 1. FileMaker ODBC Driver (DataDirect SequeLink 5.5)

The driver must be installed from the FileMaker installation media:
- Look for "xDBC" or "ODBC" folder on the FileMaker CD/download
- Install the **DataDirect 32-BIT SequeLink 5.5** driver

### 2. Configure ODBC Data Source (32-bit)

**IMPORTANT:** Use the 32-bit ODBC Administrator:
```
C:\Windows\SysWOW64\odbcad32.exe
```

Create a **System DSN** with these settings:

| Field | Value |
|-------|-------|
| Data Source Name | `Filemaker` |
| Host | `127.0.0.1` |
| Port | `2399` |

### 3. FileMaker Pro 9 Setup

For each database file (.fp7) you want to access:

1. Open the database in FileMaker Pro
2. Go to **File → Sharing → ODBC/JDBC...**
3. Set ODBC/JDBC Sharing to **On**
4. Under "Specify which users can access...", enable for your privilege set

**Account Privileges:**
- Go to **File → Manage → Accounts & Privileges**
- Edit your account's Privilege Set
- Enable **"Access via ODBC/JDBC (fmxdbc)"** under Extended Privileges

### 4. 32-bit Python (Required)

The FileMaker ODBC driver is 32-bit only. You must use 32-bit Python:

```bash
# Install 32-bit Python
winget install Python.Python.3.12 --architecture x86
```

## Installation

```bash
# Clone the repository
git clone https://github.com/aandersen2323/filemaker-mcp-server.git
cd filemaker-mcp-server

# Create virtual environment with 32-bit Python
"C:\Users\YOUR_USER\AppData\Local\Programs\Python\Python312-32\python.exe" -m venv venv32
venv32\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials
copy .env.example .env
# Edit .env with your FileMaker username/password
```

## Configuration

### .env File

Create a `.env` file with your credentials:

```ini
FILEMAKER_DSN=Filemaker
FILEMAKER_USER=manager
FILEMAKER_PASS=your_password
```

### Claude Desktop Integration

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

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

## Available Tools

| Tool | Description |
|------|-------------|
| `query` | Execute SQL SELECT queries on any database |
| `list_tables` | List all tables in a database |
| `describe_table` | Get column information for a table |
| `list_all_databases` | List all databases and their tables |
| `search_patients` | Search patient records by name |
| `get_appointments` | Get appointments by date |
| `get_transactions` | Get transaction history |
| `insert_record` | Insert a new record |
| `update_record` | Update existing records |

## Available Databases

| Database | Tables | Description |
|----------|--------|-------------|
| Patients | 26 | Patient records, contact lenses, lookups |
| Appointments | 4 | Appointment scheduling |
| Transactions | 47 | Financial transactions |
| Lookups | 23 | Reference data, procedures |
| ProdPrices | 4 | Product pricing |
| Open | 7 | Office-related tables |
| CLOrders | - | Contact lens orders |
| Dispenses | - | Dispensing records |
| Timecards | - | Employee timecards |

## SQL Query Notes

**Important:** FileMaker ODBC has some limitations:

1. **No LIMIT clause** - The server uses `fetchmany()` to limit results
2. **Field names with spaces** - Use double quotes: `"Last Name"`
3. **Special characters** - Quote fields like `"patient id#"`

### Example Queries

```sql
-- Search patients by last name
SELECT "Last Name", "First Name", "Home Phone"
FROM Patients WHERE "Last Name" LIKE 'Smith%'

-- Get appointments for a date
SELECT * FROM Appointments WHERE dateappt = '2024-01-15'

-- Get product prices
SELECT * FROM ProdPrices
```

## Running FileMaker

**FileMaker Pro must be running** with databases open for ODBC access to work.

Your workflow:
1. Open `Open.fp7` which loads all related databases
2. Patients database becomes the main window
3. Other databases are minimized but accessible

## Testing Connection

Run the test script:
```bash
venv32\Scripts\python.exe test_connection.py
```

Or use the batch file:
```bash
test_connection.bat
```

## Troubleshooting

### "Connection refused"
- Ensure FileMaker Pro is running
- Verify ODBC/JDBC sharing is enabled (File → Sharing → ODBC/JDBC)
- Check port 2399 is not blocked

### "Out of Memory"
- Large tables (like Patients) may fail with `SELECT *`
- Use specific columns: `SELECT "Last Name", "First Name" FROM Patients`
- Add WHERE clauses to filter results

### "Required user name is missing"
- Set credentials in `.env` file
- Or pass them in the connection string

### "Data source name not found"
- Use 32-bit ODBC Administrator: `C:\Windows\SysWOW64\odbcad32.exe`
- Verify DSN name matches exactly (case-sensitive)

### "Module could not be found (Error 126)"
- The ODBC driver DLL or dependencies are missing
- Reinstall the DataDirect SequeLink driver

## Project Structure

```
filemaker-mcp-server/
├── filemaker_mcp_server.py  # Main MCP server
├── test_connection.py       # Connection test script
├── test_connection.bat      # Windows batch launcher
├── requirements.txt         # Python dependencies
├── .env                     # Credentials (git-ignored)
├── .env.example             # Credentials template
├── .gitignore               # Git ignore rules
└── README.md                # This file
```

## Security Notes

- `.env` file with credentials is git-ignored
- Never commit passwords to the repository
- FileMaker database files (.fp7) are git-ignored
- Use minimal necessary privileges for ODBC accounts

## License

MIT License
