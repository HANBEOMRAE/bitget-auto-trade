import os
from dotenv import load_dotenv

load_dotenv()

EX_API_KEY = os.getenv("EX_API_KEY")
EX_API_SECRET = os.getenv("EX_API_SECRET")
EX_API_PASSPHRASE = os.getenv("EX_API_PASSPHRASE")
