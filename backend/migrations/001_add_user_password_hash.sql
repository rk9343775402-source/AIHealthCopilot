-- Additive, non-destructive authentication prerequisite.
-- Review and back up the database before applying in a deployment window.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

-- Authenticated registration normalizes email addresses to lowercase.
-- This index intentionally fails if legacy records contain case-insensitive
-- duplicate addresses; resolve those identities through a verified process first.
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_casefold
    ON users (lower(email))
    WHERE email IS NOT NULL;
