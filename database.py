from config import MONGO_URL
from pymongo import MongoClient
client = MongoClient(MONGO_URL)
db = client["meetingNotes"]

meeting_notes_collection = db["notes"]
meeting_details_collection = db["meetings"]
name = db["users"]
niaz_meeting_summaries = db["niaz_meeting_summaries"]