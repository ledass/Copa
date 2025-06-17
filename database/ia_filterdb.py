import logging
import re
import base64
from struct import pack

from pyrogram.file_id import FileId
from pymongo.errors import DuplicateKeyError
from motor.motor_asyncio import AsyncIOMotorClient

from info import DATABASE_URI, DATABASE_NAME, COLLECTION_NAME, USE_CAPTION_FILTER

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Mongo client
client = AsyncIOMotorClient(DATABASE_URI)
db = client[DATABASE_NAME]
media_collection = db[COLLECTION_NAME]

# Ensure index
async def ensure_indexes():
    try:
        await db.command("ping")
        await media_collection.create_index([("file_name", "text")])
        logger.info("Indexes ensured on Media collection.")
    except Exception as e:
        logger.exception(f"Error while ensuring indexes: {e}")

# Save file
async def save_file(media):
    file_id, file_ref = unpack_new_file_id(media.file_id)
    file_name = re.sub(r"(_|-|\.|\+)", " ", str(media.file_name or "Unnamed"))

    document = {
        "_id": file_id,
        "file_ref": file_ref,
        "file_name": file_name,
        "file_size": media.file_size,
        "file_type": media.file_type,
        "mime_type": media.mime_type,
        "caption": media.caption.html if media.caption else None,
    }

    try:
        await media_collection.insert_one(document)
        logger.info(f"{file_name} is saved to database")
        return True, 1
    except DuplicateKeyError:
        logger.warning(f"{file_name} is already saved in database")
        return False, 0
    except Exception as e:
        logger.exception(f"Error saving file: {e}")
        return False, 2

# Search files
async def get_search_results(query, file_type=None, max_results=6, offset=0):
    query = query.strip()
    if not query:
        raw_pattern = "."
    elif " " not in query:
        raw_pattern = r"(\b|[\.\+\-_])" + re.escape(query) + r"(\b|[\.\+\-_])"
    else:
        raw_pattern = ".*".join(map(re.escape, query.split()))

    try:
        regex = re.compile(raw_pattern, flags=re.IGNORECASE)
    except re.error as e:
        logger.exception(f"Invalid regex pattern: {e}")
        return [], "", 0

    filter_ = {'$or': [{'file_name': regex}, {'caption': regex}]} if USE_CAPTION_FILTER else {'file_name': regex}
    if file_type:
        filter_['file_type'] = file_type

    total_results = await media_collection.count_documents(filter_)
    next_offset = offset + max_results if (offset + max_results) < total_results else ""

    cursor = media_collection.find(filter_).sort('$natural', -1).skip(offset).limit(max_results)
    files = await cursor.to_list(length=max_results)

    return files, next_offset, total_results

# Get file details
async def get_file_details(file_id):
    file = await media_collection.find_one({"_id": file_id})
    return file

# Helpers
def encode_file_id(s: bytes) -> str:
    r = b""
    n = 0
    for i in s + bytes([22]) + bytes([4]):
        if i == 0:
            n += 1
        else:
            if n:
                r += b"\x00" + bytes([n])
                n = 0
            r += bytes([i])
    return base64.urlsafe_b64encode(r).decode().rstrip("=")

def encode_file_ref(file_ref: bytes) -> str:
    return base64.urlsafe_b64encode(file_ref).decode().rstrip("=")

def unpack_new_file_id(new_file_id):
    decoded = FileId.decode(new_file_id)
    file_id = encode_file_id(
        pack(
            "<iiqq",
            int(decoded.file_type),
            decoded.dc_id,
            decoded.media_id,
            decoded.access_hash
        )
    )
    file_ref = encode_file_ref(decoded.file_reference)
    return file_id, file_ref
