import os

IS_DEV = os.getenv("ENV", "prod").lower() == "dev"
