from .core.database import engine, Base


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database schema ready.")


if __name__ == "__main__":
    init_db()
