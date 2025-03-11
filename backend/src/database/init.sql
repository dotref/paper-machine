CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS embeddings (
  id SERIAL PRIMARY KEY,
  object_key VARCHAR(255) NOT NULL,
  embedding vector,
  text text,
  -- created_at timestamptz DEFAULT now(),
  FOREIGN KEY (object_key) REFERENCES objects(object_key) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS objects (
  id SERIAL PRIMARY KEY,
  object_key VARCHAR(255) NOT NULL,
  content_type VARCHAR(100),
  size INTEGER,
  -- created_at timestamptz DEFAULT now(),
  UNIQUE(object_key)
);

-- User authentication tables
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    -- created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- File mapping table
CREATE TABLE IF NOT EXISTS user_files (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    object_key VARCHAR(255) NOT NULL REFERENCES objects(object_key) ON DELETE CASCADE,
    original_filename VARCHAR(255) NOT NULL,
    content_type VARCHAR(100),
    -- is_owner BOOLEAN NOT NULL DEFAULT FALSE,
    -- owned_by INTEGER NOT NULL REFERENCES users(id),
    -- created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    UNIQUE(user_id, object_key)
);