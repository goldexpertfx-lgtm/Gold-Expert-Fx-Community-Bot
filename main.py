import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import time
import threading

# ⚠️ APNI DETAILS YAHAN ENTER KAREIN
API_TOKEN = "8702563696:AAE5GVUaomXmBpbk-F8o4NU9qhG991YKmT8"  # Apne Bot ka real token dalein
OWNER_ID = 7415265825  # ⚠️ APNI Telegram numerical ID dalein (taake admin panel aur live chat aapko miley)

# Channels & Groups IDs (Must be integers)
FREE_GROUP_ID = -4477244119  # Gold Expert Fx Community ID
PRIVATE_CHANNEL_ID = -3870933647  # Gold Expert FX | XAUUSD Signals ID

# Invitation Links
FREE_GROUP_LINK = "https://t.me/GoldExpertFxCommunity"  # Public Community Link
PRIVATE_CHANNEL_LINK = "https://t.me/+g8yrkwMU6DQ5M2U9"  # Private Channel Request Link
BROKER_LINK = "https://www.brokeraccountguide.com/"  # Recommended Broker
WHATSAPP_LINK = "https://whatsapp.com/channel/0029Vb5eRVjGzzKNnL7c050y"  # Apna Whatsapp Channel link yahan dalein

bot = telebot.TeleBot(API_TOKEN)

# 🗄️ Database Setup (Users tracking, Requests tracking, Live chat sessions)
def init_db():
    conn = sqlite3.connect("gold_expert_master.db")
    cursor = conn.cursor()
    # Users database
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            status TEXT DEFAULT 'active'
        )
    """)
    # Private Channel Request Tracking
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_requests (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    # Live Chat mapping: Owner message ID -> Target User ID
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_chats (
            message_id INTEGER PRIMARY KEY,
            user_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()


# 🔍 Verification Logic (Checks both: Free Community AND Private Request status)
def verify_user_status(user_id):
    # 1. Check Community Membership
    in_free_group = False
    try:
        member = bot.get_chat_member(FREE_GROUP_ID, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            in_free_group = True
    except ApiTelegramException:
        in_free_group = False

    # 2. Check Private Channel request database
    in_private_channel = False
    conn = sqlite3.connect("gold_expert_master.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM pending_requests WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is not None:
        # Request table mein user exists karta hai (is ka matlab usne join request send kar di hai)
        in_private_channel = True
        
    return in_free_group, in_private_channel


# 🏁 Bot START Command Handler
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    username = message.from_user.username or "No_Username"
    
    # Check if user is banned
    conn = sqlite3.connect("gold_expert_master.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0] == 'banned':
        conn.close()
        return  # Banned users can't use the bot
        
    cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)", (user_id, first_name, username))
    conn.commit()
    conn.close()
    
    in_free, in_private = verify_user_status(user_id)
    
    if in_free and in_private:
        send_main_menu(user_id, first_name)
    else:
        send_force_join_screen(user_id, first_name)


# 🔒 Dynamic Force Join Screen
def send_force_join_screen(user_id, first_name):
    markup = InlineKeyboardMarkup()
    btn_community = InlineKeyboardButton("➕ 🔗 Join Community", url=FREE_GROUP_LINK)
    btn_private = InlineKeyboardButton("➕ 🔑 Request Private Channel", url=PRIVATE_CHANNEL_LINK)
    btn_joined = InlineKeyboardButton("🟢 ✅ Joined / Done", callback_data="check_membership")
    
    markup.add(btn_community)
    markup.add(btn_private)
    markup.add(btn_joined)
    
    welcome_text = (
        f"👋 **Welcome {first_name} to Gold Expert FX!**\n\n"
        f"🤖 **Access Verification:**\n"
        f"Aage barhne ke liye pehle niche diye gaye **dono** channels ko join karein:\n\n"
        f"1️⃣ **Gold Expert Fx Community** (Direct Join)\n"
        f"2️⃣ **Gold Expert FX | XAUUSD Signals** (Join Request Bheinjein)\n\n"
        f"Dono tasks mukamal kar ke **🟢 ✅ Joined / Done** button par click karein!"
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")


# 🔘 Joined/Done Button Verification Logic
@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def callback_check_membership(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name
    
    in_free, in_private = verify_user_status(user_id)
    
    if in_free and in_private:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "🎉 Verification Successful! Access Granted.", show_alert=False)
        send_main_menu(user_id, first_name)
    else:
        # User details pinpoint check
        if not in_free and not in_private:
            err_msg = "⚠️ Aapne dono task nahi kiye! Pehle Community join karein aur Private Channel par request bhejin."
        elif not in_free:
            err_msg = "⚠️ Aapne abhi tak Community Group join nahi kiya! Pehle use join karein."
        else:
            err_msg = "⚠️ Aapne Private Channel par request send nahi ki! Pehle blue button par click kar ke request send karein."
            
        bot.answer_callback_query(call.id, err_msg, show_alert=True)


# 📱 Main Menu Dashboard (Unlocks only when all ok)
def send_main_menu(user_id, first_name):
    markup = InlineKeyboardMarkup(row_width=2)
    
    btn_broker = InlineKeyboardButton("🌐 Recommended Broker", url=BROKER_LINK)
    btn_vip = InlineKeyboardButton("🥇 Join VIP Free", callback_data="join_vip_info")
    btn_whatsapp = InlineKeyboardButton("💬 Whatsapp Channel", url=WHATSAPP_LINK)
    btn_support = InlineKeyboardButton("👤 Contact Owner (Support)", callback_data="contact_owner_live")
    
    markup.add(btn_broker)
    markup.add(btn_vip, btn_whatsapp)
    markup.add(btn_support)
    
    # If the user is the Owner, show an extra button to access Admin panel directly
    if user_id == OWNER_ID:
        btn_admin_shortcut = InlineKeyboardButton("🛠️ Open Admin Panel", callback_data="open_admin_panel")
        markup.add(btn_admin_shortcut)
        
    menu_msg = (
        f"🏆 **Gold Expert FX Main Menu**\n\n"
        f"Hello {first_name}! Hamara system fully verified hai.\n"
        f"Niche diye gaye features ko use karein: 👇"
    )
    bot.send_message(user_id, menu_msg, reply_markup=markup, parse_mode="Markdown")


# ✉️ Callback Menu Router
@bot.callback_query_handler(func=lambda call: call.data in ["join_vip_info", "contact_owner_live", "open_admin_panel"])
def handle_menu_router(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name
    
    if call.data == "join_vip_info":
        vip_text = (
            f"📈 **Gold Expert VIP Signals Group**\n\n"
            f"VIP Channel bilkul free join karne ke liye:\n\n"
            f"1️⃣ Sabse pehle hamare link se Exness account banayein.\n"
            f"2️⃣ Minimum deposit kar ke trading start karein.\n"
            f"3️⃣ Iske baad aap hamare active trading system mein shamil ho jayenge!\n\n"
            f"🔗 **Exness Account Guide:** {BROKER_LINK}"
        )
        bot.send_message(user_id, vip_text, parse_mode="Markdown")
        bot.answer_callback_query(call.id)
        
    elif call.data == "contact_owner_live":
        msg = bot.send_message(user_id, f"📝 **Hi {first_name}!**\n\nHow can I help you? Apna message type kar ke send karein, direct admin ko mil jayega.")
        bot.register_next_step_handler(msg, forward_to_owner)
        bot.answer_callback_query(call.id)
        
    elif call.data == "open_admin_panel":
        bot.answer_callback_query(call.id)
        handle_admin_panel(call.message)


# 🗣️ Live Support Chat: Forward User Message to Owner
def forward_to_owner(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    username = message.from_user.username or "No_Username"
    text = message.text
    
    if text in ["/start", "/admin"]:
        return # Avoid intercepting commands
        
    owner_notification = (
        f"📩 **New Message from User!**\n\n"
        f"👤 **Name:** {first_name} (@{username})\n"
        f"🆔 **User ID:** `{user_id}`\n\n"
        f"💬 **Message:** {text}\n\n"
        f"ℹ️ *Is message par DIRECT REPLY kar ke user ko answer bhejin.*"
    )
    
    try:
        sent_msg = bot.send_message(OWNER_ID, owner_notification, parse_mode="Markdown")
        
        # Save mapping of Owner's Message ID -> User ID
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO support_chats (message_id, user_id) VALUES (?, ?)", (sent_msg.message_id, user_id))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, "✅ **Your message has been sent to the owner! Please wait for a response.**")
    except Exception as e:
        bot.send_message(user_id, "❌ Support team temporarily unavailable. Try again later.")
        print(f"Error forwarding: {e}")


# 🔄 Owner Replies to User
@bot.message_handler(func=lambda msg: msg.reply_to_message is not None)
def process_owner_reply(message):
    if message.from_user.id == OWNER_ID:
        reply_to_id = message.reply_to_message.message_id
        
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM support_chats WHERE message_id = ?", (reply_to_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            user_id = row[0]
            try:
                bot.send_message(user_id, f"💬 **Reply from Admin/Owner:**\n\n{message.text}")
                bot.send_message(OWNER_ID, "✅ **Reply sent to user!**")
            except Exception as e:
                bot.send_message(OWNER_ID, f"❌ Delivering failed: {e}")


# 📥 Join Request Interceptor (Checks for Private Channel Requests)
@bot.chat_join_request_handler()
def handle_incoming_request(update):
    if update.chat.id == PRIVATE_CHANNEL_ID:
        user_id = update.from_user.id
        first_name = update.from_user.first_name
        
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO pending_requests (user_id, first_name, status) VALUES (?, ?, 'pending')", (user_id, first_name))
        conn.commit()
        conn.close()
        
        print(f"📥 Join Request Saved: {first_name} ({user_id})")
        
        # Verify instantly. If they aren't in Free Group, approve them!
        in_free, _ = verify_user_status(user_id)
        if not in_free:
            approve_user_access(user_id, first_name)


# 🔓 Approval Handler
def approve_user_access(user_id, first_name):
    try:
        bot.approve_chat_join_request(PRIVATE_CHANNEL_ID, user_id)
        print(f"✅ Approved: {first_name} ({user_id})")
        
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE pending_requests SET status = 'approved' WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        try:
            bot.send_message(user_id, f"🎉 **Congratulations {first_name}!**\n\nAapki join request accept kar li gayi hai kyun ki aap hamari free community ke member nahi hain. Enjoy VIP signals! 📈")
        except Exception:
            pass
    except ApiTelegramException as e:
        if "USER_ALREADY_PARTICIPANT" in str(e):
            conn = sqlite3.connect("gold_expert_master.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE pending_requests SET status = 'approved' WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()


# 🔄 Background Scheduler (Checks every 30s)
def scan_all_pending_requests():
    while True:
        try:
            conn = sqlite3.connect("gold_expert_master.db")
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, first_name FROM pending_requests WHERE status = 'pending'")
            all_pending = cursor.fetchall()
            conn.close()
            
            for user_id, first_name in all_pending:
                in_free, _ = verify_user_status(user_id)
                if not in_free:
                    print(f"⚡ Live Scan Match! {first_name} left/is not in free group. Approving...")
                    approve_user_access(user_id, first_name)
        except Exception as e:
            print(f"Error in background scanner: {e}")
        time.sleep(30)

threading.Thread(target=scan_all_pending_requests, daemon=True).start()


# 👑 OWNER/ADMIN PANEL
@bot.message_handler(commands=['admin'])
def handle_admin_panel(message):
    if message.from_user.id == OWNER_ID:
        markup = InlineKeyboardMarkup()
        btn_broadcast = InlineKeyboardButton("📢 Publish Post (Broadcast)", callback_data="admin_broadcast")
        btn_remove = InlineKeyboardButton("❌ Remove/Ban User from Bot", callback_data="admin_remove")
        markup.add(btn_broadcast)
        markup.add(btn_remove)
        
        bot.send_message(OWNER_ID, "🛠️ **Gold Expert Admin Panel**\n\nNiche diye gaye operations select karein:", reply_markup=markup, parse_mode="Markdown")


# Admin Panel Callback Actions
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_actions(call):
    if call.from_user.id != OWNER_ID:
        return
        
    if call.data == "admin_broadcast":
        msg = bot.send_message(OWNER_ID, "📝 **Apni Post bhejin ya forward karein** (Text, Image, Video, document sab chalega):")
        bot.register_next_step_handler(msg, prepare_broadcast)
        bot.answer_callback_query(call.id)
        
    elif call.data == "admin_remove":
        msg = bot.send_message(OWNER_ID, "🚫 **User ID send karein** jise aap database aur broadcasting list se permanently remove/ban karna chahte hain:")
        bot.register_next_step_handler(msg, process_remove_user)
        bot.answer_callback_query(call.id)


# Broadcast Prep (With "Send All" Button confirmation)
def prepare_broadcast(message):
    global broadcast_msg_payload
    broadcast_msg_payload = message
    
    markup = InlineKeyboardMarkup()
    btn_send = InlineKeyboardButton("🚀 Send All (Start Broadcasting)", callback_data="confirm_send_all")
    markup.add(btn_send)
    
    bot.send_message(OWNER_ID, "👀 **Post Preview Save Ho Chuki Hai.**\nClick karein sabhi users ko deliver karne ke liye:", reply_markup=markup, parse_mode="Markdown")


# Broadcast Dispatcher
@bot.callback_query_handler(func=lambda call: call.data == "confirm_send_all")
def execute_broadcast(call):
    if call.from_user.id != OWNER_ID:
        return
        
    # Remove button to avoid double taps
    bot.edit_message_reply_markup(chat_id=OWNER_ID, message_id=call.message.message_id, reply_markup=None)
    bot.send_message(OWNER_ID, "🔄 **Broadcasting in progress...**")
    
    conn = sqlite3.connect("gold_expert_master.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE status = 'active'")
    all_users = cursor.fetchall()
    conn.close()
    
    success = 0
    failed = 0
    
    for row in all_users:
        target_id = row[0]
        try:
            bot.copy_message(chat_id=target_id, from_chat_id=OWNER_ID, message_id=broadcast_msg_payload.message_id)
            success += 1
            time.sleep(0.05) # anti-spam delay
        except Exception:
            failed += 1
            
    bot.send_message(OWNER_ID, f"📢 **Broadcast Report:**\n\n✅ **Delivered:** {success}\n❌ **Failed/Blocked:** {failed}")
    bot.answer_callback_query(call.id)


# Admin Action: Ban User
def process_remove_user(message):
    target_id = message.text.strip()
    if target_id.isdigit():
        target_id = int(target_id)
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = 'banned' WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        
        bot.send_message(OWNER_ID, f"✅ User `{target_id}` has been **Banned and Removed** successfully.")
    else:
        bot.send_message(OWNER_ID, "❌ **Error:** Please enter numerical digits ID only.")


# 🚨 ANTI-REPORT LOG SYSTEM (Tracks reporting activity)
@bot.message_handler(func=lambda message: any(word in (message.text or "").lower() for word in ["report", "scam", "spam", "flag", "abuse"]))
def monitor_and_log_reports(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    username = message.from_user.username or "No_Username"
    text = message.text
    chat_title = message.chat.title or "Direct Message / Private"
    
    log_alert = (
        f"🚨 **Anti-Report Logging Alert!**\n\n"
        f"👤 **Triggered By:** {first_name} (@{username})\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"📍 **Target Channel/Group:** {chat_title}\n"
        f"💬 **Keyword Logged:** {text}\n\n"
        f"⚠️ *Owner or Admin checking is advised.*"
    )
    try:
        bot.send_message(OWNER_ID, log_alert, parse_mode="Markdown")
    except Exception:
        pass


# 🏃 SILENT CLEAN: Delete group system messages instantly (Keep community clean)
@bot.message_handler(content_types=['new_chat_members', 'left_chat_member'])
def delete_system_messages(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
        print("Silent Clean: System join/leave message deleted.")
    except Exception as e:
        print(f"Error cleaning system notifications: {e}")


if __name__ == "__main__":
    print("Gold Expert Ultimate VIP Master Robot is running...")
    bot.infinity_polling(timeout=10)
    
