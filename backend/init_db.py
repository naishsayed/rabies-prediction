# init_db.py
import sqlite3

# Connect to the database file (it will be created if it doesn't exist)
connection = sqlite3.connect('users.db')

# Create a cursor object to execute SQL commands
cursor = connection.cursor()

# Create the users table with an auto-incrementing ID, a unique username, and a password hash
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL
    )
''')

# Commit the changes and close the connection
connection.commit()
connection.close()

print("Database 'users.db' initialized successfully.")