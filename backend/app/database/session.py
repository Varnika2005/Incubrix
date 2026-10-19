from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

# SQLite database engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    import app.database.models  # noqa
    Base.metadata.create_all(bind=engine)

    # Lightweight schema migration for existing SQLite database
    with engine.connect() as conn:
        try:
            # Check existing columns in jobs table
            result = conn.execute(text("PRAGMA table_info(jobs)"))
            columns = {row[1] for row in result.fetchall()}
            
            if "user_id" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN user_id VARCHAR(36)"))
                conn.commit()
            if "is_demo" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN is_demo BOOLEAN DEFAULT 0"))
                conn.commit()
        except Exception as e:
            print(f"[Database Warning] Auto-migration check: {e}")

# Auto-initialize database schema
init_db()
