#!/usr/bin/env python3
import uvicorn
from app.init_db import init_db

if __name__ == "__main__":
    print("Initializing database...")
    init_db()
    print("\nStarting server...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
