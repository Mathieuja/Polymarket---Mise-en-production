"""Main entry point for worker application."""

def main():
    """Main function that initializes the worker."""
    from app_shared.database import init_db
    
    # Initialize database tables
    init_db()
    print("Worker initialized. Shared database models ready.")
    print("TODO: Implement polymarket API ingestion logic")


if __name__ == "__main__":
    main()
