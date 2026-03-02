-- Phase 1 Schema Migration for Ticket System
-- Run this SQL script directly in your PostgreSQL database

-- 1. Add SLA tracking columns to the ticket table
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS sla_due_at TIMESTAMP;
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS first_response_at TIMESTAMP;
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP;
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS reopened_count INTEGER DEFAULT 0;

-- 2. Create ticket_comment table for tracking comments
CREATE TABLE IF NOT EXISTS ticket_comment (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Create ticket_attachment table for file uploads
CREATE TABLE IF NOT EXISTS ticket_attachment (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_size INTEGER,
    content_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Verify the changes
SELECT 'Phase 1 Schema Applied Successfully' as status;
SELECT column_name FROM information_schema.columns WHERE table_name = 'ticket' ORDER BY ordinal_position;
