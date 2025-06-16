import bcrypt


class Hasher:

    @staticmethod
    def hash(value: str):
        b = value.encode('utf-8')
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(b, salt).decode()

    @staticmethod
    def verify(value: str, string_hash: str) -> bool:
        ch = value.encode('utf-8')
        h = string_hash.encode('utf-8')
        return bcrypt.checkpw(ch, h)
