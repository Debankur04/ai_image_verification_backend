from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")

if not MONGO_URL:
    raise RuntimeError("❌ MONGO_URL is not set")

client = AsyncIOMotorClient(MONGO_URL)
db = client["job_queue_db"]
jobs_collection = db["jobs"]
