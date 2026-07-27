#!/usr/bin/env python3
"""Wait for the MSSQL test server to become available."""

import os
import sys
import time

import pymssql

MSSQL_HOST = os.environ.get("MSSQL_HOST", "127.0.0.1")
MSSQL_PORT = int(os.environ.get("MSSQL_PORT", "14333"))
MSSQL_USER = os.environ.get("MSSQL_USER", "sa")
MSSQL_PASSWORD = os.environ.get("MSSQL_PASSWORD", "DataDictionary!234")


def main():
    for attempt in range(30):
        try:
            conn = pymssql.connect(
                server=MSSQL_HOST,
                port=MSSQL_PORT,
                user=MSSQL_USER,
                password=MSSQL_PASSWORD,
            )
            conn.close()
            print("SQL Server is ready")
            sys.exit(0)
        except Exception as exc:
            print(f"Attempt {attempt + 1}: {exc}")
            time.sleep(2)

    print("SQL Server never became ready")
    sys.exit(1)


if __name__ == "__main__":
    main()