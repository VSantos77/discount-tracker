import psycopg2
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def get_db_connection(db_settings):
    # In production, use environment variables or a config file for these values
    conn = psycopg2.connect(**db_settings)
    try:
        yield conn
    finally:
        conn.close()

def get_project_root_path() -> Path:
    """Returns the root directory of the project."""
    # Start from the current file's directory
    current_path = Path(__file__).resolve()
    
    # Climb up until we find the root marker (e.g., pyproject.toml or .git)
    for parent in current_path.parents:
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
            
    # Fallback: return the directory of the entry script if no marker found
    return current_path.parent