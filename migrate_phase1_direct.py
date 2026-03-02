#!/usr/bin/env python
"""Apply Phase 1 database schema migration"""

import psycopg2
import sys

def main():
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(
            host='127.0.0.1',
            port=5432,
            user='soporte_user',
            password='soporte123',
            database='soporte_db',
            connect_timeout=5
        )
        cur = conn.cursor()
        
        print("Phase 1 Schema Migration Starting...")
        
        # Get current columns
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'ticket'
        """)
        columns = {row[0] for row in cur.fetchall()}
        
        # Add missing columns to ticket table
        columns_to_add = {
            'sla_due_at': 'TIMESTAMP NULL',
            'first_response_at': 'TIMESTAMP NULL',
            'resolved_at': 'TIMESTAMP NULL',
            'reopened_count': 'INTEGER DEFAULT 0'
        }
        
        for col_name, col_type in columns_to_add.items():
            if col_name not in columns:
                sql = f'ALTER TABLE ticket ADD COLUMN {col_name} {col_type}'
                cur.execute(sql)
                print(f"✓ Added {col_name} column")
            else:
                print(f"✓ {col_name} column already exists")
        
        conn.commit()
        print("✓ Committed ticket table changes")
        
        # Create TicketComment table
        create_comment_sql = """
        CREATE TABLE IF NOT EXISTS ticket_comment (
            id SERIAL PRIMARY KEY,
            ticket_id INTEGER NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
            user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cur.execute(create_comment_sql)
        print("✓ Created ticket_comment table")
        
        # Create TicketAttachment table
        create_attachment_sql = """
        CREATE TABLE IF NOT EXISTS ticket_attachment (
            id SERIAL PRIMARY KEY,
            ticket_id INTEGER NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
            filename VARCHAR(255) NOT NULL,
            stored_filename VARCHAR(255) NOT NULL,
            file_size INTEGER,
            content_type VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cur.execute(create_attachment_sql)
        print("✓ Created ticket_attachment table")
        
        conn.commit()
        print("\n✅ OK Phase1 schema applied successfully!")
        
        cur.close()
        conn.close()
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during migration: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
