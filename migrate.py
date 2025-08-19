#!/usr/bin/env python3
"""
Migration script that handles existing tables gracefully.
This script checks if tables exist and stamps the migration accordingly.
"""

import os
import sys
from flask import Flask
from flask_migrate import Migrate, upgrade, stamp
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

# Import your app
from run import app

def check_if_tables_exist():
    """Check if the main tables already exist in the database."""
    try:
        with app.app_context():
            inspector = inspect(app.extensions['migrate'].db.engine)
            tables = inspector.get_table_names()
            return 'users' in tables and 'games' in tables and 'bets' in tables
    except Exception as e:
        print(f"Error checking tables: {e}")
        return False

def check_migration_history():
    """Check if there are any migration records in alembic_version table."""
    try:
        with app.app_context():
            result = app.extensions['migrate'].db.engine.execute(
                text("SELECT COUNT(*) FROM alembic_version")
            )
            count = result.scalar()
            return count > 0
    except Exception as e:
        # Table doesn't exist or other error
        print(f"No migration history found: {e}")
        return False

def main():
    """Run migrations with proper handling of existing tables."""
    with app.app_context():
        tables_exist = check_if_tables_exist()
        has_migration_history = check_migration_history()
        
        print(f"Tables exist: {tables_exist}")
        print(f"Has migration history: {has_migration_history}")
        
        if tables_exist and not has_migration_history:
            # Tables exist but no migration history - stamp as current
            print("Tables exist but no migration history. Stamping current migration...")
            stamp(revision='001')
            print("Migration stamped successfully!")
        elif not tables_exist:
            # No tables - run normal upgrade
            print("No tables found. Running migration...")
            upgrade()
            print("Migration completed successfully!")
        else:
            # Tables exist and have history - run upgrade normally
            print("Running migration upgrade...")
            upgrade()
            print("Migration upgrade completed!")

if __name__ == '__main__':
    main()