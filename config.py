from pathlib import Path
from environs import Env

BASE_DIR = Path(__file__).resolve().parent

env = Env()
env.read_env(BASE_DIR / ".env")

BOT_TOKEN = env.str("BOT_TOKEN")
KALI_TOKEN = env.str("KALI_TOKEN")