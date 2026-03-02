-- Phase 1 Schema Migration
-- Add SLA tracking columns to ticket table
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS sla_due_at TIMESTAMP NULL;
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS first_response_at TIMESTAMP NULL;
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP NULL;
ALTER TABLE ticket ADD COLUMN IF NOT EXISTS reopened_count INTEGER DEFAULT 0;

-- Create TicketComment table
CREATE TABLE IF NOT EXISTS ticket_comment (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create TicketAttachment table
CREATE TABLE IF NOT EXISTS ticket_attachment (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES ticket(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_size INTEGER,
    content_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
