#!/usr/bin/env python
"""Test PostgreSQL database connection"""

import socket
import sys

# Test if 127.0.0.1:5432 is reachable
host = '127.0.0.1'
port = 5432

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    result = sock.connect_ex((host, port))
    sock.close()
    
    if result == 0:
        print(f"✓ PostgreSQL port {port} is accessible on {host}")
        
        # Try actual database connection
        try:
            import psycopg2
            from dotenv import load_dotenv
            import os
            
            load_dotenv()
            conn = psycopg2.connect(
                host='127.0.0.1',
                port=5432,
                user='soporte_user',
                password='soporte123',
                database='soporte_db',
                connect_timeout=3
            )
            print("✓ Successfully connected to PostgreSQL database!")
            
            # Check if ticket table exists
            cur = conn.cursor()
            cur.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'ticket'
            """)
            columns = [row[0] for row in cur.fetchall()]
            print(f"\nTicket table columns: {columns}")
            print(f"\nColumns to add:")
            needed = ['sla_due_at', 'first_response_at', 'resolved_at', 'reopened_count']
            for col in needed:
                status = "✓ exists" if col in columns else "✗ missing"
                print(f"  {col}: {status}")
                
            cur.close()
            conn.close()
            
            # Now apply migrations
            print("\nApplying Phase 1 schema migrations...")
            conn = psycopg2.connect(
                host='127.0.0.1',
                port=5432,
                user='soporte_user',
                password='soporte123',
                database='soporte_db'
            )
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()
            
            migrations = [
                ('sla_due_at', 'ALTER TABLE ticket ADD COLUMN IF NOT EXISTS sla_due_at TIMESTAMP NULL'),
                ('first_response_at', 'ALTER TABLE ticket ADD COLUMN IF NOT EXISTS first_response_at TIMESTAMP NULL'),
                ('resolved_at', 'ALTER TABLE ticket ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP NULL'),
                ('reopened_count', 'ALTER TABLE ticket ADD COLUMN IF NOT EXISTS reopened_count INTEGER DEFAULT 0'),
            ]
            
            for col_name, sql in migrations:
                try:
                    cur.execute(sql)
                    print(f"  OK: Added column {col_name}")
                except Exception as col_err:
                    print(f"  OK: Column {col_name} already exists")
            
            # Create new tables
            cur.execute('''CREATE TABLE IF NOT EXISTS ticket_comment (
                id SERIAL PRIMARY KEY,
                ticket_id INTEGER NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            print("  OK: Created ticket_comment table")
            
            cur.execute('''CREATE TABLE IF NOT EXISTS ticket_attachment (
                id SERIAL PRIMARY KEY,
                ticket_id INTEGER NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
                filename VARCHAR(255) NOT NULL,
                stored_filename VARCHAR(255) NOT NULL,
                file_size INTEGER,
                content_type VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            print("  OK: Created ticket_attachment table")
            
            cur.close()
            conn.close()
            print("\nOK: Phase 1 schema migration completed successfully!")
            
        except Exception as e:
            print(f"Error: Database connection or migration failed: {e}")
            sys.exit(1)
    else:
        print(f"✗ Cannot reach PostgreSQL port {port} on {host}")
        print("PostgreSQL may not be running or firewall may be blocking the connection")
        sys.exit(1)
except Exception as e:
    print(f"✗ Error checking port: {e}")
    sys.exit(1)
