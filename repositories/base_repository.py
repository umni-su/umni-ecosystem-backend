import database.database as db


class BaseRepository:
    @staticmethod
    def query():
        return db.get_separate_session()
