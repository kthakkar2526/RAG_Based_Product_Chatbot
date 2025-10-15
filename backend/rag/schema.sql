CREATE DATABASE rag_notes;
USE rag_notes;

CREATE TABLE notes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    note_id VARCHAR(50) NOT NULL,
    text TEXT NOT NULL,
    created_at DATETIME
);