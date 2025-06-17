
import asyncio
import re
import ast
import random
import math
import logging

from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from pyrogram.errors import FloodWait, UserIsBlocked, MessageNotModified, PeerIdInvalid, MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty

from Script import script
from tamilanbotsz import short_url
from utils import get_shortlink, get_size, is_subscribed, get_poster, search_gagala, temp, get_settings, save_group_settings
from database.connections_mdb import active_connection, all_connections, delete_connection, if_active, make_active, make_inactive
from database.users_chats_db import db
from database.ia_filterdb import get_file_details, get_search_results, media_collection
from database.filters_mdb import del_all, find_filter, get_filters
from info import ADMINS, AUTH_CHANNEL, AUTH_USERS, CUSTOM_FILE_CAPTION, AUTH_GROUPS, P_TTI_SHOW_OFF, IMDB, FILE_REQ_CHANNEL, HOW_TO_DOWNLOAD, PICS, SINGLE_BUTTON, SPELL_CHECK_REPLY, IMDB_TEMPLATE, REQ_CHANNEL

logger = logging.getLogger(name)
logger.setLevel(logging.ERROR)

BUTTONS = {}
SPELL_CHECK = {}
FILTER_MODE = {}

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    if query.data in ["stats", "rfrsh"]:
        await query.answer("Fetching MongoDb DataBase" if query.data == "rfrsh" else "")
        buttons = [
            [InlineKeyboardButton('♻️ Rᴇғʀᴇsʜ', callback_data='rfrsh')],
            [InlineKeyboardButton('‹‹‹ Bᴀᴄᴋ', callback_data='about')]
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        total = await media_collection.count_documents({})
        users = await db.total_users_count()
        chats = await db.total_chat_count()
        monsize = await db.get_db_size()
        free = 536870912 - monsize
        monsize = get_size(monsize)
        free = get_size(free)
        await query.message.edit_text(
            text=script.STATUS_TXT.format(total, users, chats, monsize, free),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

@Client.on_message(filters.command("autofilter"))
async def autofilter_cmd(client, message):
    args = message.text.split(None, 1)
    if len(args) < 2:
        return await message.reply("Usage: /autofilter on | off")
    mode = args[1].lower()
    if mode in ["on", "yes", "true"]:
        FILTER_MODE[str(message.chat.id)] = True
        await message.reply("Auto-filter enabled.")
    elif mode in ["off", "no", "false"]:
        FILTER_MODE[str(message.chat.id)] = False
        await message.reply("Auto-filter disabled.")
    else:
        await message.reply("Invalid argument. Use on/off.")

@Client.on_message(filters.command("stats") & filters.user(ADMINS))
async def stats_cmd(client, message):
    total = await media_collection.count_documents({})
    users = await db.total_users_count()
    chats = await db.total_chat_count()
    monsize = await db.get_db_size()
    free = 536870912 - monsize
    monsize = get_size(monsize)
    free = get_size(free)
    await message.reply(script.STATUS_TXT.format(total, users, chats, monsize, free))

@Client.on_message(filters.command("users") & filters.user(ADMINS))
async def list_users(client, message):
    users = await db.get_all_users()
    text = "Users in DB:\n"
    async for user in users:
        text += f"<a href=\"tg://user?id={user['id']}\">{user['name']}</a>\n"
    await message.reply(text, parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("chats") & filters.user(ADMINS))
async def list_chats(client, message):
    chats = await db.get_all_chats()
    text = "Chats in DB:\n"
    async for chat in chats:
        text += f"{chat['title']} | ID: {chat['id']}\n"
    await message.reply(text)
@Client.on_message((filters.group | filters.private) & filters.text & filters.incoming)
async def auto_filter(client, message):
    if message.text.startswith("/"):
        return
    settings = await get_settings(message.chat.id)
    if len(message.text) < 3:
        return
    files, offset, total_results = await get_search_results(message.text.strip(), offset=0, filter=True)
    if not files:
        return
    buttons = [
        [InlineKeyboardButton(f"{file.file_name}", callback_data=f"file#{file.file_id}")]
        for file in files
    ]
    if offset:
        buttons.append([
            InlineKeyboardButton("Next", callback_data=f"next_0_{message.text.strip()}_{offset}")
        ])
    await message.reply("Here are the results:", reply_markup=InlineKeyboardMarkup(buttons))
@Client.on_message((filters.group | filters.private) & filters.text & filters.incoming)
async def auto_filter(client, message):
    if message.text.startswith("/"):
        return
    settings = await get_settings(message.chat.id)
    if len(message.text) < 3:
        return
    files, offset, total_results = await get_search_results(message.text.strip(), offset=0, filter=True)
    if not files:
        return
    buttons = [
        [InlineKeyboardButton(f"{file.file_name}", callback_data=f"file#{file.file_id}")]
        for file in files
    ]
    if offset:
        buttons.append([
            InlineKeyboardButton("Next", callback_data=f"next_0_{message.text.strip()}_{offset}")
        ])
    await message.reply("Here are the results:", reply_markup=InlineKeyboardMarkup(buttons))
