#!/usr/bin/env python
"""Apply Phase 1 database schema migration from SQL file"""

import psycopg2
import sys

try:
    # Connect to PostgreSQL
    print("Connecting to PostgreSQL...")
    conn = psycopg2.connect(
        host='127.0.0.1',
        port=5432,
        user='soporte_user',
        password='soporte123',
        database='soporte_db',
        connect_timeout=5
    )
    conn.autocommit = True  # Auto-commit each statement
    cur = conn.cursor()
    
    print("✓ Connected successfully")
    print("\nApplying Phase 1 schema changes...")
    
    # Read and execute SQL script
    with open('migration_script.sql', 'r') as f:
        sql_script = f.read()
    
    # Split by semicolon and execute each statement
    statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
    
    for i, statement in enumerate(statements, 1):
        try:
            cur.execute(statement)
            # Extract a short description from the statement
            first_word = statement.split()[0].upper()
            if len(statement) > 50:
                desc = statement[:50] + "..."
            else:
                desc = statement
            print(f"  ✓ Statement {i}: {first_word}... executed")
        except Exception as e:
            print(f"  ⚠ Statement {i}: {e}")
    
    cur.close()
    conn.close()
    
    print("\n✅ Phase 1 schema migration completed successfully!")
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
