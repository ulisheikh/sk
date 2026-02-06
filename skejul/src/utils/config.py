from pathlib import Path
from environs import Env

# skejul/src/utils/config.py -> 3 marta parent = skejul/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = Env()
env.read_env(path=str(BASE_DIR / ".env"))

BOT_TOKEN = env.str("BOT_TOKEN")