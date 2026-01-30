#!/usr/bin/env python3
"""
FileMaker 9 Pro MCP Server

An MCP (Model Context Protocol) server that connects to FileMaker 9 Pro
databases via ODBC, enabling AI assistants to query and interact with
FileMaker data.
"""

import asyncio
import json
import logging
import os
import pyodbc
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp.server import Server

# Load environment variables from .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    CallToolResult,
    ListResourcesResult,
    ListToolsResult,
    ReadResourceResult,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("filemaker-mcp-server")

# FileMaker ODBC DSN name - configure this in Windows ODBC Data Sources
DEFAULT_DSN = os.environ.get("FILEMAKER_DSN", "FileMaker")
DEFAULT_USER = os.environ.get("FILEMAKER_USER", "")
DEFAULT_PASS = os.environ.get("FILEMAKER_PASS", "")


@dataclass
class FileMakerConfig:
    """Configuration for FileMaker ODBC connection."""
    dsn: str = DEFAULT_DSN
    username: str = DEFAULT_USER
    password: str = DEFAULT_PASS
    database: str = ""


class FileMakerConnection:
    """Manages ODBC connections to FileMaker databases."""

    def __init__(self, config: FileMakerConfig):
        self.config = config
        self._connection = None

    def connect(self, database: str = None) -> pyodbc.Connection:
        """Establish connection to FileMaker via ODBC."""
        db = database or self.config.database

        # Build connection string for FileMaker ODBC
        # SequeLink driver uses ServerDataSource to specify the database
        conn_parts = [f"DSN={self.config.dsn}"]

        if db:
            conn_parts.append(f"ServerDataSource={db}")
        if self.config.username:
            conn_parts.append(f"UID={self.config.username}")
        if self.config.password:
            conn_parts.append(f"PWD={self.config.password}")

        connection_string = ";".join(conn_parts)

        try:
            self._connection = pyodbc.connect(connection_string)
            logger.info(f"Connected to FileMaker database: {db or 'default'}")
            return self._connection
        except pyodbc.Error as e:
            logger.error(f"Failed to connect to FileMaker: {e}")
            raise

    def close(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("FileMaker connection closed")

    def execute_query(self, query: str, params: tuple = None, limit: int = 100) -> list[dict]:
        """Execute a SQL query and return results as list of dicts.

        Note: FileMaker ODBC doesn't support FETCH FIRST or LIMIT clauses,
        so we use cursor.fetchmany() to limit results instead.
        """
        if not self._connection:
            raise RuntimeError("Not connected to database")

        cursor = self._connection.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # Fetch limited results (FileMaker doesn't support SQL LIMIT clause)
            rows = cursor.fetchmany(limit)

            # Convert to list of dicts
            results = []
            for row in rows:
                results.append(dict(zip(columns, row)))

            return results
        finally:
            cursor.close()

    def execute_update(self, query: str, params: tuple = None) -> int:
        """Execute an INSERT/UPDATE/DELETE and return affected row count."""
        if not self._connection:
            raise RuntimeError("Not connected to database")

        cursor = self._connection.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            self._connection.commit()
            return cursor.rowcount
        finally:
            cursor.close()

    def get_tables(self) -> list[str]:
        """Get list of tables in the connected database."""
        if not self._connection:
            raise RuntimeError("Not connected to database")

        cursor = self._connection.cursor()
        try:
            tables = []
            for row in cursor.tables():
                # Filter to just user tables
                if row.table_type == "TABLE":
                    tables.append(row.table_name)
            return tables
        finally:
            cursor.close()

    def get_columns(self, table_name: str) -> list[dict]:
        """Get column information for a table."""
        if not self._connection:
            raise RuntimeError("Not connected to database")

        cursor = self._connection.cursor()
        try:
            columns = []
            for row in cursor.columns(table=table_name):
                columns.append({
                    "name": row.column_name,
                    "type": row.type_name,
                    "size": row.column_size,
                    "nullable": row.nullable == 1
                })
            return columns
        finally:
            cursor.close()


# Available FileMaker databases (based on .fp7 files)
FILEMAKER_DATABASES = [
    "Appointments",
    "CLOrders",
    "Dispenses",
    "Email",
    "Lookups",
    "Open",
    "OpenAdmin",
    "OpenMngr",
    "Patients",
    "ProdPrices",
    "Timecards",
    "Transactions"
]


def create_server(config: FileMakerConfig = None) -> Server:
    """Create and configure the MCP server."""

    server = Server("filemaker-mcp-server")
    fm_config = config or FileMakerConfig()
    connections: dict[str, FileMakerConnection] = {}

    def get_connection(database: str) -> FileMakerConnection:
        """Get or create a connection for a database."""
        if database not in connections:
            conn = FileMakerConnection(fm_config)
            conn.connect(database)
            connections[database] = conn
        return connections[database]

    @server.list_resources()
    async def list_resources() -> ListResourcesResult:
        """List available FileMaker databases as resources."""
        resources = []
        for db in FILEMAKER_DATABASES:
            resources.append(
                Resource(
                    uri=f"filemaker://{db}",
                    name=f"FileMaker: {db}",
                    description=f"FileMaker database: {db}.fp7",
                    mimeType="application/json"
                )
            )
        return ListResourcesResult(resources=resources)

    @server.read_resource()
    async def read_resource(uri: str) -> ReadResourceResult:
        """Read schema information for a FileMaker database."""
        # Parse the URI to get database name
        if not uri.startswith("filemaker://"):
            raise ValueError(f"Invalid URI scheme: {uri}")

        database = uri.replace("filemaker://", "")

        try:
            conn = get_connection(database)
            tables = conn.get_tables()

            schema_info = {
                "database": database,
                "tables": []
            }

            for table in tables:
                columns = conn.get_columns(table)
                schema_info["tables"].append({
                    "name": table,
                    "columns": columns
                })

            return ReadResourceResult(
                contents=[
                    TextContent(
                        type="text",
                        text=json.dumps(schema_info, indent=2, default=str)
                    )
                ]
            )
        except Exception as e:
            logger.error(f"Error reading resource {uri}: {e}")
            return ReadResourceResult(
                contents=[
                    TextContent(
                        type="text",
                        text=json.dumps({"error": str(e)})
                    )
                ]
            )

    @server.list_tools()
    async def list_tools() -> ListToolsResult:
        """List available tools for interacting with FileMaker."""
        return ListToolsResult(tools=[
            Tool(
                name="query",
                description="Execute a SELECT query on a FileMaker database. Use standard SQL syntax.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database": {
                            "type": "string",
                            "description": f"Database name. Available: {', '.join(FILEMAKER_DATABASES)}"
                        },
                        "sql": {
                            "type": "string",
                            "description": "SQL SELECT query to execute"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of rows to return (default: 100)",
                            "default": 100
                        }
                    },
                    "required": ["database", "sql"]
                }
            ),
            Tool(
                name="list_tables",
                description="List all tables in a FileMaker database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database": {
                            "type": "string",
                            "description": f"Database name. Available: {', '.join(FILEMAKER_DATABASES)}"
                        }
                    },
                    "required": ["database"]
                }
            ),
            Tool(
                name="describe_table",
                description="Get column information for a table in a FileMaker database",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database": {
                            "type": "string",
                            "description": f"Database name. Available: {', '.join(FILEMAKER_DATABASES)}"
                        },
                        "table": {
                            "type": "string",
                            "description": "Table name to describe"
                        }
                    },
                    "required": ["database", "table"]
                }
            ),
            Tool(
                name="insert_record",
                description="Insert a new record into a FileMaker table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database": {
                            "type": "string",
                            "description": f"Database name. Available: {', '.join(FILEMAKER_DATABASES)}"
                        },
                        "table": {
                            "type": "string",
                            "description": "Table name"
                        },
                        "data": {
                            "type": "object",
                            "description": "Key-value pairs of column names and values to insert"
                        }
                    },
                    "required": ["database", "table", "data"]
                }
            ),
            Tool(
                name="update_record",
                description="Update records in a FileMaker table",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "database": {
                            "type": "string",
                            "description": f"Database name. Available: {', '.join(FILEMAKER_DATABASES)}"
                        },
                        "table": {
                            "type": "string",
                            "description": "Table name"
                        },
                        "data": {
                            "type": "object",
                            "description": "Key-value pairs of column names and values to update"
                        },
                        "where": {
                            "type": "string",
                            "description": "WHERE clause condition (without 'WHERE' keyword)"
                        }
                    },
                    "required": ["database", "table", "data", "where"]
                }
            ),
            Tool(
                name="list_all_databases",
                description="List all available FileMaker databases and their tables",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            Tool(
                name="search_patients",
                description="Search for patients by name, ID, or other criteria",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "search_term": {
                            "type": "string",
                            "description": "Search term (name, patient ID, phone, etc.)"
                        },
                        "field": {
                            "type": "string",
                            "description": "Field to search in. Use quotes for fields with spaces: '\"Last Name\"', '\"First Name\"', '\"patient id#\"'",
                            "default": "\"Last Name\""
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results to return",
                            "default": 50
                        }
                    },
                    "required": ["search_term"]
                }
            ),
            Tool(
                name="get_appointments",
                description="Get appointments for a specific date or date range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date in YYYY-MM-DD format"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date for range query (optional)"
                        },
                        "patient_id": {
                            "type": "string",
                            "description": "Filter by patient ID (optional)"
                        }
                    },
                    "required": ["date"]
                }
            ),
            Tool(
                name="get_transactions",
                description="Get transactions for a patient or date range",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "patient_id": {
                            "type": "string",
                            "description": "Patient ID to look up transactions for"
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Start date in YYYY-MM-DD format (optional)"
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in YYYY-MM-DD format (optional)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum results",
                            "default": 100
                        }
                    },
                    "required": []
                }
            )
        ])

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> CallToolResult:
        """Handle tool calls."""
        try:
            if name == "query":
                database = arguments["database"]
                sql = arguments["sql"]
                limit = arguments.get("limit", 100)

                # FileMaker ODBC doesn't support FETCH FIRST or LIMIT
                # We pass limit to execute_query which uses fetchmany()
                conn = get_connection(database)
                results = conn.execute_query(sql, limit=limit)

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps({
                                "success": True,
                                "row_count": len(results),
                                "data": results
                            }, indent=2, default=str)
                        )
                    ]
                )

            elif name == "list_tables":
                database = arguments["database"]
                conn = get_connection(database)
                tables = conn.get_tables()

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps({
                                "success": True,
                                "database": database,
                                "tables": tables
                            }, indent=2)
                        )
                    ]
                )

            elif name == "describe_table":
                database = arguments["database"]
                table = arguments["table"]
                conn = get_connection(database)
                columns = conn.get_columns(table)

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps({
                                "success": True,
                                "database": database,
                                "table": table,
                                "columns": columns
                            }, indent=2)
                        )
                    ]
                )

            elif name == "insert_record":
                database = arguments["database"]
                table = arguments["table"]
                data = arguments["data"]

                columns = ", ".join(data.keys())
                placeholders = ", ".join(["?" for _ in data])
                values = tuple(data.values())

                sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

                conn = get_connection(database)
                affected = conn.execute_update(sql, values)

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps({
                                "success": True,
                                "message": f"Inserted {affected} record(s)"
                            }, indent=2)
                        )
                    ]
                )

            elif name == "update_record":
                database = arguments["database"]
                table = arguments["table"]
                data = arguments["data"]
                where = arguments["where"]

                set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
                values = tuple(data.values())

                sql = f"UPDATE {table} SET {set_clause} WHERE {where}"

                conn = get_connection(database)
                affected = conn.execute_update(sql, values)

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps({
                                "success": True,
                                "message": f"Updated {affected} record(s)"
                            }, indent=2)
                        )
                    ]
                )

            elif name == "list_all_databases":
                all_db_info = {}
                for db in FILEMAKER_DATABASES:
                    try:
                        conn = get_connection(db)
                        tables = conn.get_tables()
                        all_db_info[db] = {"tables": tables, "count": len(tables)}
                    except Exception as e:
                        all_db_info[db] = {"error": str(e)}

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps({
                                "success": True,
                                "databases": all_db_info
                            }, indent=2)
                        )
                    ]
                )

            elif name == "search_patients":
                search_term = arguments["search_term"]
                field = arguments.get("field", "\"Last Name\"")
                limit = arguments.get("limit", 50)

                # Select specific columns to avoid memory issues with large records
                sql = f"""SELECT "Last Name", "First Name", "Middle Initial",
                         "Street Address", "City", "State", "Zip",
                         "Home Phone", "Work Phone", "birth date"
                         FROM Patients WHERE {field} LIKE ?"""

                conn = get_connection("Patients")
                results = conn.execute_query(sql, (f"%{search_term}%",), limit=limit)

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps({
                                "success": True,
                                "row_count": len(results),
                                "data": results
                            }, indent=2, default=str)
                        )
                    ]
                )

            elif name == "get_appointments":
                date = arguments["date"]
                end_date = arguments.get("end_date")
                patient_id = arguments.get("patient_id")
                limit = arguments.get("limit", 100)

                # FileMaker field names have spaces: dateappt, timeappt, "patient id#"
                if end_date:
                    sql = "SELECT * FROM Appointments WHERE dateappt BETWEEN ? AND ?"
                    params = (date, end_date)
                else:
                    sql = "SELECT * FROM Appointments WHERE dateappt = ?"
                    params = (date,)

                if patient_id:
                    sql += " AND \"patient id#\" = ?"
                    params = params + (patient_id,)

                sql += " ORDER BY timeappt"

                conn = get_connection("Appointments")
                results = conn.execute_query(sql, params, limit=limit)

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps({
                                "success": True,
                                "row_count": len(results),
                                "data": results
                            }, indent=2, default=str)
                        )
                    ]
                )

            elif name == "get_transactions":
                patient_id = arguments.get("patient_id")
                start_date = arguments.get("start_date")
                end_date = arguments.get("end_date")
                limit = arguments.get("limit", 100)

                conditions = []
                params = []

                # Note: Field names may need adjustment based on actual schema
                if patient_id:
                    conditions.append("\"patient id#\" = ?")
                    params.append(patient_id)
                if start_date:
                    conditions.append("\"trans date\" >= ?")
                    params.append(start_date)
                if end_date:
                    conditions.append("\"trans date\" <= ?")
                    params.append(end_date)

                sql = "SELECT * FROM Transactions"
                if conditions:
                    sql += " WHERE " + " AND ".join(conditions)

                conn = get_connection("Transactions")
                results = conn.execute_query(sql, tuple(params) if params else None, limit=limit)

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps({
                                "success": True,
                                "row_count": len(results),
                                "data": results
                            }, indent=2, default=str)
                        )
                    ]
                )

            else:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=json.dumps({"error": f"Unknown tool: {name}"})
                        )
                    ],
                    isError=True
                )

        except Exception as e:
            logger.error(f"Tool error ({name}): {e}")
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": str(e)
                        }, indent=2)
                    )
                ],
                isError=True
            )

    return server


async def main():
    """Run the MCP server."""
    server = create_server()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
