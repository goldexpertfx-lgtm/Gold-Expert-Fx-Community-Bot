import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import time
import threading

# =====================================================================
# ⚠️ CONFIGURATION - ENTER YOUR REAL CREDENTIALS HERE
# =====================================================================
API_TOKEN = "8702563696:AAE5GVUaomXmBpbk-F8o4NU9qhG991YKmT8"  # Paste your Bot Token
OWNER_ID = 7415265825  # Paste your numerical Telegram ID

# Chat IDs (Must be integers)
FREE_GROUP_ID = -4477244119  # Gold Expert Fx Community ID
PRIVATE_CHANNEL_ID = -3870933647  # Gold Expert FX | XAUUSD Signals ID

# Promotional Links
FREE_GROUP_LINK = "https://t.me/GoldExpertFxCommunity"
PRIVATE_CHANNEL_LINK = "https://t.me/+g8yrkwMU6DQ5M2U9"
BROKER_LINK = "https://www.brokeraccountguide.com/"
WHATSAPP_LINK = "https://whatsapp.com/channel/0029Vb5eRVjGzzKNnL7c050y"  # Replace with your WhatsApp channel link
# =====================================================================

bot = telebot.TeleBot(API_TOKEN)

# 🗄️ Database Setup
def init_db():
    conn = sqlite3.connect("gold_expert_master.db")
    cursor = conn.cursor()
    # Registered Users Table
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
    # Live Chat Session Mapping: Admin Message ID -> User ID
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_chats (
            message_id INTEGER PRIMARY KEY,
            user_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()


# 🔍 Dynamic Verification Helper
def verify_user_status(user_id):
    """Accurately checks user membership in both Free Group and Private Channel"""
    # 1. Verify Free Group Membership
    in_free_group = False
    try:
        member = bot.get_chat_member(FREE_GROUP_ID, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            in_free_group = True
    except ApiTelegramException:
        in_free_group = False

    # 2. Verify Private Channel Status (Check Telegram API & Database Backup)
    in_private_channel = False
    try:
        member = bot.get_chat_member(PRIVATE_CHANNEL_ID, user_id)
        if member.status in ['member', 'administrator', 'creator', 'restricted']:
            in_private_channel = True
    except ApiTelegramException:
        # Fallback to local database if Telegram API limits checking unsaved private members
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM pending_requests WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row is not None:
            in_private_channel = True
            
    return in_free_group, in_private_channel


# 🏁 Bot Start Command
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
        return
        
    cursor.execute("INSERT OR IGNORE INTO users (user_id, first_name, username) VALUES (?, ?, ?)", (user_id, first_name, username))
    conn.commit()
    conn.close()
    
    in_free, in_private = verify_user_status(user_id)
    
    if in_free and in_private:
        send_main_menu(user_id, first_name)
    else:
        send_force_join_screen(user_id, first_name)


# 🔒 Clean English Force Join Verification Screen
def send_force_join_screen(user_id, first_name):
    markup = InlineKeyboardMarkup()
    btn_community = InlineKeyboardButton("➕ 🔗 Join Free Community", url=FREE_GROUP_LINK)
    btn_private = InlineKeyboardButton("➕ 🔑 Request Private VIP", url=PRIVATE_CHANNEL_LINK)
    btn_joined = InlineKeyboardButton("🟢 ✅ Joined / Done", callback_data="check_membership")
    
    markup.add(btn_community)
    markup.add(btn_private)
    markup.add(btn_joined)
    
    welcome_text = (
        f"👋 **Welcome {first_name} to Gold Expert FX!**\n\n"
        f"🚨 **Access Verification Required:**\n"
        f"To unlock our premium dashboard, you must complete the two tasks below:\n\n"
        f"1️⃣ **Join our Gold Expert Fx Community** (Free Group)\n"
        f"2️⃣ **Request Access to Gold Expert FX | XAUUSD Signals** (Private Channel)\n\n"
        f"Once done, tap the **🟢 ✅ Joined / Done** button to proceed!"
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")


# 🔘 Handle Membership Check Callback
@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def callback_check_membership(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name
    
    in_free, in_private = verify_user_status(user_id)
    
    if in_free and in_private:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "🎉 Success! Welcome to Gold Expert FX.", show_alert=False)
        send_main_menu(user_id, first_name)
    else:
        # Clear english diagnostic warnings
        if not in_free and not in_private:
            err_msg = "⚠️ You have not joined either channel! Please join the Community and send a join request to our VIP Private Channel."
        elif not in_free:
            err_msg = "⚠️ You have not joined our Free Community Group yet! Please join the community first."
        else:
            err_msg = "⚠️ You have not sent a join request to the Private VIP Channel! Please click the Request button first."
            
        bot.answer_callback_query(call.id, err_msg, show_alert=True)


# 📱 Clean English Main Menu
def send_main_menu(user_id, first_name):
    markup = InlineKeyboardMarkup(row_width=2)
    
    btn_broker = InlineKeyboardButton("🌐 Recommended Broker", url=BROKER_LINK)
    btn_vip = InlineKeyboardButton("🥇 Join VIP Free", callback_data="join_vip_info")
    btn_whatsapp = InlineKeyboardButton("💬 Whatsapp Channel", url=WHATSAPP_LINK)
    btn_support = InlineKeyboardButton("👤 Contact Owner (Support)", callback_data="contact_owner_live")
    
    markup.add(btn_broker)
    markup.add(btn_vip, btn_whatsapp)
    markup.add(btn_support)
    
    if user_id == OWNER_ID:
        btn_admin_shortcut = InlineKeyboardButton("🛠️ Open Admin Panel", callback_data="open_admin_panel")
        markup.add(btn_admin_shortcut)
        
    menu_msg = (
        f"🏆 **Gold Expert FX Dashboard**\n\n"
        f"Hello **{first_name}**! Your account has been verified successfully.\n"
        f"Access our premium systems, guides, and contact support below: 👇"
    )
    bot.send_message(user_id, menu_msg, reply_markup=markup, parse_mode="Markdown")


# ✉️ Inline Button Handlers
@bot.callback_query_handler(func=lambda call: call.data in ["join_vip_info", "contact_owner_live", "open_admin_panel"])
def handle_menu_router(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name
    
    if call.data == "join_vip_info":
        vip_text = (
            f"📈 **Gold Expert VIP Signals Group**\n\n"
            f"To gain lifetime access to our VIP signals for FREE:\n\n"
            f"1️⃣ Create a new account under our link on Exness.\n"
            f"2️⃣ Make a deposit and open your active trades.\n"
            f"3️⃣ After completing this, your system access will become permanent!\n\n"
            f"🔗 **Exness Account Setup Guide:** {BROKER_LINK}"
        )
        bot.send_message(user_id, vip_text, parse_mode="Markdown")
        bot.answer_callback_query(call.id)
        
    elif call.data == "contact_owner_live":
        msg = bot.send_message(user_id, f"📝 **Hi {first_name}!**\n\nHow can I help you today? Please type your message below and send it. Our support team will get back to you shortly.")
        bot.register_next_step_handler(msg, forward_to_owner)
        bot.answer_callback_query(call.id)
        
    elif call.data == "open_admin_panel":
        bot.answer_callback_query(call.id)
        handle_admin_panel(call.message)


# 👤 Live Support Message Forwarder
def forward_to_owner(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    username = message.from_user.username or "No_Username"
    text = message.text
    
    if text in ["/start", "/admin"]:
        return
        
    owner_notification = (
        f"📩 **New Message from User!**\n\n"
        f"👤 **Name:** {first_name} (@{username})\n"
        f"🆔 **User ID:** `{user_id}`\n\n"
        f"💬 **Message:** {text}\n\n"
        f"ℹ️ *Simply REPLY to this message to send your response directly to the user.*"
    )
    
    try:
        sent_msg = bot.send_message(OWNER_ID, owner_notification, parse_mode="Markdown")
        
        # Save mapping
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO support_chats (message_id, user_id) VALUES (?, ?)", (sent_msg.message_id, user_id))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, "✅ **Your message has been sent to the owner! Please stand by.**")
    except Exception as e:
        bot.send_message(user_id, "❌ Support temporarily unavailable. Please try again later.")
        print(f"Support forward failed: {e}")


# 🔄 Direct Admin Replies
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
                bot.send_message(user_id, f"💬 **Message from Owner:**\n\n{message.text}")
                bot.send_message(OWNER_ID, "✅ **Reply successfully delivered to the user!**")
            except Exception as e:
                bot.send_message(OWNER_ID, f"❌ Delivery failed: {e}")


# 📥 Join Request Interceptor
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
        
        print(f"📥 Request registered: {first_name} ({user_id})")
        
        # Instant validation
        in_free, _ = verify_user_status(user_id)
        if not in_free:
            approve_user_access(user_id, first_name)


# 🔓 Request Approver
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
            bot.send_message(user_id, f"🎉 **Congratulations {first_name}!**\n\nYour request has been approved since you are not in the free community. Enjoy our Private VIP signals! 📈")
        except Exception:
            pass
    except ApiTelegramException as e:
        if "USER_ALREADY_PARTICIPANT" in str(e):
            conn = sqlite3.connect("gold_expert_master.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE pending_requests SET status = 'approved' WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()


# 🔄 Background Scanner
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
                    print(f"⚡ Scanner: {first_name} is active in premium criteria. Approving...")
                    approve_user_access(user_id, first_name)
        except Exception as e:
            print(f"Scanner error: {e}")
        time.sleep(30)

threading.Thread(target=scan_all_pending_requests, daemon=True).start()


# 👑 Admin Panel commands
@bot.message_handler(commands=['admin'])
def handle_admin_panel(message):
    if message.from_user.id == OWNER_ID:
        markup = InlineKeyboardMarkup()
        btn_broadcast = InlineKeyboardButton("📢 Publish Post (Broadcast)", callback_data="admin_broadcast")
        btn_remove = InlineKeyboardButton("❌ Remove/Ban User", callback_data="admin_remove")
        markup.add(btn_broadcast)
        markup.add(btn_remove)
        
        bot.send_message(OWNER_ID, "🛠️ **Gold Expert Admin Panel**\n\nSelect administrative task:", reply_markup=markup, parse_mode="Markdown")


# Admin Actions Callbacks
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_actions(call):
    if call.from_user.id != OWNER_ID:
        return
        
    if call.data == "admin_broadcast":
        msg = bot.send_message(OWNER_ID, "📝 **Send or forward the post** you wish to publish (supports Text, Images, Videos, Documents):")
        bot.register_next_step_handler(msg, prepare_broadcast)
        bot.answer_callback_query(call.id)
        
    elif call.data == "admin_remove":
        msg = bot.send_message(OWNER_ID, "🚫 **Send the User ID** of the user you want to permanently remove/ban from the bot:")
        bot.register_next_step_handler(msg, process_remove_user)
        bot.answer_callback_query(call.id)


# Broadcast Prep
def prepare_broadcast(message):
    global broadcast_msg_payload
    broadcast_msg_payload = message
    
    markup = InlineKeyboardMarkup()
    btn_send = InlineKeyboardButton("🚀 Send All (Start Broadcasting)", callback_data="confirm_send_all")
    markup.add(btn_send)
    
    bot.send_message(OWNER_ID, "👀 **Broadcast Preview successfully loaded.**\nTap the button below to send this post to all bot users:", reply_markup=markup, parse_mode="Markdown")


# Broadcast Dispatcher
@bot.callback_query_handler(func=lambda call: call.data == "confirm_send_all")
def execute_broadcast(call):
    if call.from_user.id != OWNER_ID:
        return
        
    bot.edit_message_reply_markup(chat_id=OWNER_ID, message_id=call.message.message_id, reply_markup=None)
    bot.send_message(OWNER_ID, "🔄 **Dispatching broadcast. Please wait...**")
    
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
            time.sleep(0.05)
        except Exception:
            failed += 1
            
    bot.send_message(OWNER_ID, f"📢 **Broadcast Report Finished!**\n\n✅ **Delivered:** {success}\n❌ **Failed/Blocked:** {failed}")
    bot.answer_callback_query(call.id)


# Remove/Ban User
def process_remove_user(message):
    target_id = message.text.strip()
    if target_id.isdigit():
        target_id = int(target_id)
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = 'banned' WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        
        bot.send_message(OWNER_ID, f"✅ User `{target_id}` successfully **Banned & Removed** from the database.")
    else:
        bot.send_message(OWNER_ID, "❌ **Error:** Please enter numerical digits only.")


# 🚨 Anti-Report Alert logger
@bot.message_handler(func=lambda message: any(word in (message.text or "").lower() for word in ["report", "scam", "spam", "flag", "abuse"]))
def monitor_and_log_reports(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    username = message.from_user.username or "No_Username"
    text = message.text
    chat_title = message.chat.title or "Private Chat"
    
    log_alert = (
        f"🚨 **Anti-Report Logging Triggered!**\n\n"
        f"👤 **Triggered By:** {first_name} (@{username})\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"📍 **Target Chat/Channel:** {chat_title}\n"
        f"💬 **Keyword Logged:** {text}\n\n"
        f"⚠️ *Owner or Admin monitoring is advised.*"
    )
    try:
        bot.send_message(OWNER_ID, log_alert, parse_mode="Markdown")
    except Exception:
        pass


# 🏃 Silent Clean: Auto delete join/leave system notifications
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
    
