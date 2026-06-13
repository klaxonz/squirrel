from infrastructure.database import session as database


def get_session():
    return database.get_session()
