import os  # 👈 Render ရဲ့ Port ကို ဖတ်ဖို့အတွက်
import asyncio
import random
import time
import re  # 👈 Pick Command များကို Regex ဖြင့် တိကျစွာဆွဲထုတ်ရန်
from telethon import TelegramClient, events, errors
from telethon.sessions import StringSession
from motor.motor_asyncio import AsyncIOMotorClient

# ==========================================
# ⚙️ CONFIGURATION (Updated Credentials)
# ==========================================
MONGO_URI = "mongodb+srv://khantphyoemin537_db_user:9VRKiaeZkz7rJdpz@cluster0.w6tgi8j.mongodb.net/telegram_bot?appName=Cluster0&tlsAllowInvalidCertificates=true"
APP_ID = 31541615                               # 👈 [UPDATED] App ID အသစ်
APP_HASH = '6355273371999439125c0a57e21abb0f'   # 👈 [UPDATED] App Hash အသစ်
BOT_TOKEN = '8111794244:AAGpkLE7h5x_IYFvjkVCbJosDC1TFbCGxcQ'

OWNER_ID = 6015356597          
SPECIFIC_GROUP = -1003944491355 

# 🎯 PICK BOT CONFIGURATIONS 
PICK_BOT_ID = 8532697507        
PICK_CHEAT_BOT_ID = 8499894036  
PICK_CHEAT_GROUP = -1003944491355 
PICK_REGEX = re.compile(r"(/pick\s+[^\n]+)") 

# Global States
pick_tracker = {}              
last_pick_chat_id = None       
is_pick_stopped = False        

# MongoDB Setup
client_mongo = AsyncIOMotorClient(MONGO_URI)
db = client_mongo["telegram_bot"]
logan_col = db["logan_col"]                    # 👈 [UPDATED] logan_col သို့ ပြောင်းလဲပြီး

# Initialize Official Bot Client
bot = TelegramClient('official_bot_session', APP_ID, APP_HASH)
userbot = None  

# ==========================================
# 🌍 DUMMY HTTP SERVER FOR RENDER HEALTH CHECK
# ==========================================
async def handle_render_health_check(reader, writer):
    await reader.read(100)
    response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: 2\r\n\r\nOK"
    writer.write(response.encode('utf-8'))
    await writer.drain()
    writer.close()

async def start_dummy_web_server():
    port = int(os.environ.get("PORT", 10000))
    try:
        server = await asyncio.start_server(handle_render_health_check, '0.0.0.0', port)
        print(f"🌍 Dummy HTTP Server started on port {port} for Render Health Check!")
        async with server:
            await server.serve_forever()
    except Exception as e:
        print(f"❌ Failed to start Dummy Web Server: {e}")

# ==========================================
# 🗑️ ANTI-FLOOD DELAYED DELETION TASK
# ==========================================
async def delete_pick_message_delayed(client, chat_id, msg_id):
    """ /pick command အား ၁ စက္ကန့်အကြာတွင် အလိုအလျောက် ပြန်ဖျက်ပေးမည့် သီးသန့် Task """
    try:
        await asyncio.sleep(1)
        await client.delete_messages(chat_id, msg_id)
        print(f"🗑️ Auto-deleted /pick message {msg_id} after 1 second.")
    except Exception as e:
        print(f"❌ Failed to delete /pick message: {e}")

# ==========================================
# ⚔️ PICK BOT DETECTOR & SOLVER HANDLERS
# ==========================================
async def pick_detector_handler(event):
    global last_pick_chat_id, pick_tracker
    """ Pick Bot ထံမှ စာသားပေါ်လာပါက Cheat Group ထံ forward လှမ်းပို့မည့်စနစ် """
    if event.sender_id == PICK_BOT_ID and event.text:
        if "A character materializes in the shadows..." in event.text:
            
            orig_chat_id = event.chat_id
            last_pick_chat_id = orig_chat_id
            
            try:
                # စာနှင့် ဗီဒီယိုကို Cheat Group ဆီ တိုက်ရိုက် forward ပို့မည်
                fwd_msg = await event.message.forward_to(PICK_CHEAT_GROUP)
                
                # Cheat Bot က Reply ပြန်လာလျှင် ခြေရာခံနိုင်ရန် ID ကို သိမ်းဆည်းခြင်း
                pick_tracker[fwd_msg.id] = orig_chat_id
                
                if len(pick_tracker) > 100:
                    pick_tracker.pop(next(iter(pick_tracker)))
                    
                print(f"📦 Pick Character Materialized! Forwarded to Cheat Group from {orig_chat_id}")
            except Exception as e:
                print(f"❌ Pick Forward Error: {e}")

async def pick_solver_handler(event):
    global last_pick_chat_id, pick_tracker, is_pick_stopped
    """ Pick Cheat Bot ဆီမှ /pick command အား ကူးယူပြီး မူရင်း Group ဆီ ပြန်အော်ပေးမည့်စနစ် """
    if is_pick_stopped:
        return

    if event.chat_id == PICK_CHEAT_GROUP and event.sender_id == PICK_CHEAT_BOT_ID and event.text:
        match = PICK_REGEX.search(event.text)
        if match:
            pick_command = match.group(1).strip(" `\n\r")
            target_group = last_pick_chat_id
            
            # Cheat bot က Forward မက်ဆေ့ခ်ျကို Reply ပြန်ပြီး စာပို့ခဲ့လျှင် မူရင်း Group ကို ရှာဖွေခြင်း
            if event.reply_to_msg_id and event.reply_to_msg_id in pick_tracker:
                target_group = pick_tracker[event.reply_to_msg_id]
                
            if target_group:
                try:
                    delay_time = random.uniform(0.4, 0.6)  
                    async with event.client.action(target_group, 'typing'):
                        await asyncio.sleep(delay_time)
                        
                    # မူရင်း Group ဆီသို့ /pick xxx လှမ်းပို့ခြင်း
                    sent_msg = await event.client.send_message(target_group, pick_command)
                    print(f"⚡ Picked character with delay {delay_time:.2f}s")
                    
                    # ပို့ပြီးတာနဲ့ အဖွဲ့ထဲ စာမရှုပ်စေရန် ၁ စက္ကန့်အကြာတွင် /pick မက်ဆေ့ခ်ျကို ပြန်ဖျက်ခြင်း
                    asyncio.create_task(delete_pick_message_delayed(event.client, target_group, sent_msg.id))
                    
                except Exception as e:
                    print(f"❌ Pick Command Send Error: {e}")

# ==========================================
# 🤖 OFFICIAL BOT COMMAND HANDLERS
# ==========================================
@bot.on(events.NewMessage(chats=SPECIFIC_GROUP))
async def handle_bot_commands(event):
    global userbot, is_pick_stopped
    
    if event.sender_id != OWNER_ID:
        return

    cmd = event.message.text.strip() if event.message.text else ""

    if cmd.startswith("/logan"):                # 👈 [UPDATED] /marcuz မှ /logan သို့ ပြောင်းလဲပြီး
        args = cmd.split(maxsplit=1)
        session_str = None
        
        if len(args) > 1:
            session_str = args[1].strip()
        elif event.is_reply:
            reply_msg = await event.get_reply_message()
            if reply_msg and reply_msg.text:
                session_str = reply_msg.text.strip()
                
        if not session_str:
            await event.reply("❌ **String Session မတွေ့ရှိပါ။ ပြန်လည်စစ်ဆေးပါ။**")
            return
            
        await logan_col.update_one(             # 👈 logan_col သို့ သိမ်းဆည်းခြင်း
            {"key": "string_session"},
            {"$set": {"value": session_str}},
            upsert=True
        )
        await event.reply("✅ String Session ကို `logan_col` DB ထဲမှာ အောင်မြင်စွာ သိမ်းပြီးပါပြီ။ Userbot ချိတ်ဆက်နေသည်...")
        
        try:
            if userbot:
                await userbot.disconnect()
            userbot = TelegramClient(StringSession(session_str), APP_ID, APP_HASH)
            await userbot.start()
            await userbot.get_dialogs()
            
            # Register Only Pick Handlers
            userbot.add_event_handler(pick_detector_handler, events.NewMessage())
            userbot.add_event_handler(pick_solver_handler, events.NewMessage())
            
            await event.reply("🚀 Userbot is Live with Pick Sniper System (Logan Mod)!")
        except Exception as e:
            await event.reply(f"❌ Userbot အလုပ်မလုပ်ပါ: {e}")

    elif cmd == "/stop":
        is_pick_stopped = True 
        await event.reply("🛑 **Chief! `/pick` လုပ်ငန်းစဉ်ကို ရပ်ဆိုင်းလိုက်ပါပြီ။**")

    elif cmd == "/start":
        is_pick_stopped = False 
        await event.reply("✅ **Chief! `/pick` လုပ်ငန်းစဉ်ကို ပြန်လည်စတင်လိုက်ပါပြီ။**")

# ==========================================
# 🚀 SYSTEM STARTUP LOGIC
# ==========================================
async def startup():
    global userbot
    print("⏳ System starting up and loading configurations from MongoDB...")
    
    asyncio.create_task(start_dummy_web_server())

    session_doc = await logan_col.find_one({"key": "string_session"}) # 👈 logan_col မှ session ပြန်ဖတ်ခြင်း
    if session_doc:
        try:
            session_str = session_doc.get("value")
            userbot = TelegramClient(StringSession(session_str), APP_ID, APP_HASH)
            await userbot.start()
            await userbot.get_dialogs()
            
            # Register Handlers at Startup
            userbot.add_event_handler(pick_detector_handler, events.NewMessage())
            userbot.add_event_handler(pick_solver_handler, events.NewMessage())
            
            print("🚀 Userbot Session Successfully Loaded from DB with Pick Bot Mod!")
        except Exception as e:
            print(f"⚠️ Failed to load existing Userbot Session: {e}")
    else:
        print("💡 No String Session found in DB yet.")

    await bot.start(bot_token=BOT_TOKEN)
    print("🤖 Official Bot is running...")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(startup())

