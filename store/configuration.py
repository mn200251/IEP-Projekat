import os

databaseUrl = os.environ["DATABASE_URL"]
# databaseUrl = "localhost"


class Configuration:
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://root:root@{databaseUrl}/store"
    REDIS_HOST = "localhost"
    REDIS_THREADS_LIST = "threads"
    JWT_SECRET_KEY="JWT_SECRET_DEV_KEY"
