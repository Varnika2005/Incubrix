from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool
from app.core.config import settings

# SQLite database engine with NullPool to prevent pool exhaustion
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=NullPool
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
            if "original_file_hash" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN original_file_hash VARCHAR(64)"))
                conn.commit()
            if "original_file_size" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN original_file_size INTEGER"))
                conn.commit()
            if "edit_history_json" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN edit_history_json TEXT"))
                conn.commit()
            if "source_integrity_verified" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN source_integrity_verified BOOLEAN DEFAULT 1"))
                conn.commit()
            if "source_integrity_status" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN source_integrity_status VARCHAR(64) DEFAULT 'verified_immutable'"))
                conn.commit()
            if "instruction_history_json" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN instruction_history_json TEXT"))
                conn.commit()
            if "callback_url" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN callback_url VARCHAR(512)"))
                conn.commit()
            if "manifest_json" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN manifest_json TEXT"))
                conn.commit()
            if "s3_key" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN s3_key VARCHAR(512)"))
                conn.commit()
            if "s3_url" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN s3_url VARCHAR(512)"))
                conn.commit()
            if "manifest_s3_url" not in columns:
                conn.execute(text("ALTER TABLE jobs ADD COLUMN manifest_s3_url VARCHAR(512)"))
                conn.commit()
        except Exception as e:
            print(f"[Database Warning] Auto-migration check: {e}")

# Auto-initialize database schema
init_db()
