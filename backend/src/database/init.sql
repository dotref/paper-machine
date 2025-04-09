CREATE EXTENSION IF NOT EXISTS vector;

-- User authentication table
CREATE TABLE IF NOT EXISTS users (
  username VARCHAR(100) PRIMARY KEY,
  password_hash VARCHAR(255) NOT NULL,
  last_login TIMESTAMP
);

-- Objects table
CREATE TABLE IF NOT EXISTS objects (
  object_key VARCHAR(255) PRIMARY KEY,
  content_type VARCHAR(100),
  size INTEGER
);

-- Embeddings table
CREATE TABLE IF NOT EXISTS embeddings (
  id SERIAL PRIMARY KEY,
  object_key VARCHAR(255) NOT NULL REFERENCES objects(object_key) ON DELETE CASCADE,
  embedding vector,
  text text
);

-- File mapping table
CREATE TABLE IF NOT EXISTS user_files (
  id SERIAL PRIMARY KEY,
  username VARCHAR(100) NOT NULL REFERENCES users(username) ON DELETE CASCADE,
  object_key VARCHAR(255) NOT NULL REFERENCES objects(object_key) ON DELETE CASCADE,
  original_filename VARCHAR(255) NOT NULL,
  content_type VARCHAR(100),
  UNIQUE(username, object_key)
);