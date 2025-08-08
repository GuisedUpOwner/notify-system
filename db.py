from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file

PROD_DATABASE_URL = os.getenv("PROD_DATABASE_URL")
DEV_DATABASE_URL = os.getenv("DEV_DATABASE_URL")
AI_DATABASE_URL = os.getenv("AI_DATABASE_URL")

# Production Database
prod_engine = create_engine(PROD_DATABASE_URL)
ProdSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=prod_engine)

# Development Database
dev_engine = create_engine(DEV_DATABASE_URL)
DevSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=dev_engine)

# AI Memory Database
ai_engine = create_engine(AI_DATABASE_URL)
AISessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ai_engine)

# Database selection helper
def get_db(db_type='dev'):
    if db_type == 'prod':
        return ProdSessionLocal()
    elif db_type == 'ai':
        return AISessionLocal()
    elif db_type == 'dev':
        return DevSessionLocal()
    else:
        raise ValueError("Invalid database type. Use 'prod' or 'ai'.")

# Dependency: Get Prod DB
def get_prod_db():
    db = ProdSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency: Get Dev DB
def get_dev_db():
    db = DevSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency: Get AI DB
def get_ai_db():
    db = AISessionLocal()
    try:
        yield db
    finally:
        db.close()
