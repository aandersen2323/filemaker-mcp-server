# FileMaker 9 Pro MCP Server

An MCP (Model Context Protocol) server that connects to FileMaker 9 Pro databases via ODBC, enabling AI assistants like Claude to query and interact with FileMaker data.

## Prerequisites

### 1. FileMaker ODBC Driver

You need the FileMaker ODBC driver installed on your system:

1. The driver should be included with FileMaker 9 Pro installation
2. Or download from FileMaker's website (may require login)

### 2. Configure ODBC Data Source

1. Open **ODBC Data Sources (64-bit)** from Windows search
2. Go to **System DSN** tab
3. Click **Add...**
4. Select **FileMaker ODBC** driver
5. Configure:
   - **Data Source Name**: `FileMaker` (or your preferred name)
   - **Host**: `localhost` (for local FileMaker)
   - **Database**: Leave empty (will be specified per-query)
6. Click **OK**

### 3. FileMaker Database Setup

For ODBC access to work, each FileMaker database must:

1. Have **ODBC/JDBC sharing** enabled:
   - In FileMaker: File > Sharing > ODBC/JDBC...
   - Set to "All users" or specific privilege set

2. Have an account with ODBC access privileges:
   - File > Manage > Accounts & Privileges
   - Create/edit an account with "Access via ODBC/JDBC" enabled

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/filemaker-mcp-server.git
cd filemaker-mcp-server

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Running the Server

```bash
python filemaker_mcp_server.py
```

### Configuring with Claude Desktop

Add to your Claude Desktop config (`%APPDATA%\Claude\claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "filemaker": {
      "command": "python",
      "args": ["C:\\path\\to\\filemaker_mcp_server.py"],
      "env": {
        "FILEMAKER_DSN": "FileMaker",
        "FILEMAKER_USER": "your_username",
        "FILEMAKER_PASS": "your_password"
      }
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
| `insert_record` | Insert a new record |
| `update_record` | Update existing records |
| `search_patients` | Search patient records by name/ID |
| `get_appointments` | Get appointments by date/patient |
| `get_transactions` | Get transaction history |

## Available Databases

- Appointments
- CLOrders
- Dispenses
- Email
- Lookups
- Open
- OpenAdmin
- OpenMngr
- Patients
- ProdPrices
- Timecards
- Transactions

## Example Queries

```sql
-- Search for patients
SELECT * FROM Patients WHERE LastName LIKE 'Smith%'

-- Get today's appointments
SELECT * FROM Appointments WHERE AppointmentDate = '2024-01-15'

-- View recent transactions
SELECT * FROM Transactions ORDER BY TransactionDate DESC
```

## Security Notes

- Database files (.fp7) are excluded from git via .gitignore
- Never commit credentials to the repository
- Use environment variables for sensitive configuration
- Ensure FileMaker accounts have minimal necessary privileges

## Troubleshooting

### "Data source name not found"
- Verify ODBC DSN is configured in Windows ODBC Data Sources
- Ensure using 64-bit ODBC manager if using 64-bit Python

### "Connection failed"
- Check FileMaker is running and databases are open
- Verify ODBC/JDBC sharing is enabled in FileMaker
- Confirm account credentials are correct

### "Table not found"
- Table names in FileMaker may differ from file names
- Use `list_tables` tool to see available tables

## License

MIT License
