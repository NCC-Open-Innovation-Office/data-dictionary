#!/usr/bin/env python3
"""Wait for the PostgreSQL test server to become available."""

import os
import sys
import time

import psycopg2


POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = int(os.environ.get("POSTGRES_PORT", "54320"))
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")


def main():
    for attempt in range(30):
        try:
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                dbname=POSTGRES_DB,
            )
            conn.close()
            print("PostgreSQL is ready")
            sys.exit(0)
        except Exception as exc:
            print(f"Attempt {attempt + 1}: {exc}")
            time.sleep(2)

    print("PostgreSQL never became ready")
    sys.exit(1)


if __name__ == "__main__":
    main()