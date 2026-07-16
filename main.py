import telebot
from telebot.apihelper import ApiTelegramException
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import time
import threading

# =====================================================================
# CONFIGURATION
# =====================================================================
API_TOKEN = "8702563696:AAE5GVUaomXmBpbk-F8o4NU9qhG991YKmT8"  # Replace with your Bot Token
OWNER_ID = 7415265825  # Replace with your numerical Telegram ID

# Chat IDs
FREE_GROUP_ID = -4477244119  # Gold Expert Fx Community ID
PRIVATE_CHANNEL_ID = -3870933647  # Gold Expert FX | XAUUSD Signals ID

# Links
FREE_GROUP_LINK = "https://t.me/GoldExpertFxCommunity"
PRIVATE_CHANNEL_LINK = "https://t.me/+g8yrkwMU6DQ5M2U9"
BROKER_LINK = "https://www.brokeraccountguide.com/"
WHATSAPP_LINK = "https://whatsapp.com/channel/0029Vb5eRVjGzzKNnL7c050y"
# =====================================================================

bot = telebot.TeleBot(API_TOKEN)

# Database Setup
def init_db():
    conn = sqlite3.connect("gold_expert_master.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            status TEXT DEFAULT 'active'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_requests (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            status TEXT DEFAULT 'pending'
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS support_chats (
            message_id INTEGER PRIMARY KEY,
            user_id INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()


# Verification Logic
def verify_user_status(user_id):
    in_free_group = False
    in_private_channel = False

    # 1. Verify Free Group
    try:
        member = bot.get_chat_member(FREE_GROUP_ID, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            in_free_group = True
    except ApiTelegramException:
        in_free_group = False

    # 2. Verify Private Channel (Database and Live Request Fallbacks)
    conn = sqlite3.connect("gold_expert_master.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM pending_requests WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row is not None:
        in_private_channel = True
    else:
        try:
            member = bot.get_chat_member(PRIVATE_CHANNEL_ID, user_id)
            if member.status in ['member', 'administrator', 'creator', 'restricted', 'left']:
                in_private_channel = True
        except ApiTelegramException:
            in_private_channel = False
            
    return in_free_group, in_private_channel


# Bot /start Command
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    username = message.from_user.username or "No_Username"
    
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


# Force Join Screen (Strictly English & Limited Emojis)
def send_force_join_screen(user_id, first_name):
    markup = InlineKeyboardMarkup()
    btn_community = InlineKeyboardButton("Join Free Community", url=FREE_GROUP_LINK)
    btn_private = InlineKeyboardButton("Request Private VIP", url=PRIVATE_CHANNEL_LINK)
    btn_joined = InlineKeyboardButton("Joined / Done", callback_data="check_membership")
    
    markup.add(btn_community)
    markup.add(btn_private)
    markup.add(btn_joined)
    
    welcome_text = (
        f"Welcome **{first_name}** to Gold Expert FX!\n\n"
        f"**Access Verification Required:**\n"
        f"To proceed and unlock our features, you must complete these two tasks:\n\n"
        f"1. **Join** our Free Community Group.\n"
        f"2. **Send a Join Request** to our Private VIP Channel.\n\n"
        f"Once you have completed both, click **Joined / Done** below."
    )
    bot.send_message(user_id, welcome_text, reply_markup=markup, parse_mode="Markdown")


# Callback Membership Verification (Direct Warnings)
@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def callback_check_membership(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name
    
    in_free, in_private = verify_user_status(user_id)
    
    if in_free and in_private:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "Verification Successful!", show_alert=False)
        send_main_menu(user_id, first_name)
    else:
        if not in_free and not in_private:
            err_msg = "Please join the Free Community and submit a join request to the Private VIP Channel first."
        elif not in_free:
            err_msg = "You have not joined our Free Community yet. Please join the community group to proceed."
        else:
            err_msg = "Please send a join request to our Private VIP Channel before clicking Done."
            
        bot.answer_callback_query(call.id, err_msg, show_alert=True)


# Main Menu Dashboard
def send_main_menu(user_id, first_name):
    markup = InlineKeyboardMarkup(row_width=2)
    
    btn_broker = InlineKeyboardButton("Recommended Broker", url=BROKER_LINK)
    btn_vip = InlineKeyboardButton("Join VIP Free", callback_data="join_vip_info")
    btn_whatsapp = InlineKeyboardButton("WhatsApp Channel", url=WHATSAPP_LINK)
    btn_support = InlineKeyboardButton("Contact Owner", callback_data="contact_owner_live")
    
    markup.add(btn_broker)
    markup.add(btn_vip, btn_whatsapp)
    markup.add(btn_support)
    
    if user_id == OWNER_ID:
        btn_admin_shortcut = InlineKeyboardButton("Open Admin Panel", callback_data="open_admin_panel")
        markup.add(btn_admin_shortcut)
        
    menu_msg = (
        f"**Gold Expert FX Dashboard**\n\n"
        f"Hello **{first_name}**! Your account is verified.\n"
        f"Use the buttons below to access our direct services and channels:"
    )
    bot.send_message(user_id, menu_msg, reply_markup=markup, parse_mode="Markdown")


# Menu Options
@bot.callback_query_handler(func=lambda call: call.data in ["join_vip_info", "contact_owner_live", "open_admin_panel"])
def handle_menu_router(call):
    user_id = call.from_user.id
    first_name = call.from_user.first_name
    
    if call.data == "join_vip_info":
        vip_text = (
            f"**Gold Expert VIP Signals**\n\n"
            f"To access our premium signals for free:\n\n"
            f"1. Create an account through our partner link.\n"
            f"2. Make a minimum deposit to start trading.\n"
            f"3. Once verified, you will secure permanent VIP access.\n\n"
            f"**Exness Registration Guide:** {BROKER_LINK}"
        )
        bot.send_message(user_id, vip_text, parse_mode="Markdown")
        bot.answer_callback_query(call.id)
        
    elif call.data == "contact_owner_live":
        msg = bot.send_message(user_id, f"Hello **{first_name}**!\n\nHow can I help you today? Please type your message below and send it. It will be delivered directly to the owner.")
        bot.register_next_step_handler(msg, forward_to_owner)
        bot.answer_callback_query(call.id)
        
    elif call.data == "open_admin_panel":
        bot.answer_callback_query(call.id)
        handle_admin_panel(call.message)


# Message Forwarder (Live Chat to Owner)
def forward_to_owner(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    username = message.from_user.username or "No_Username"
    text = message.text
    
    if text in ["/start", "/admin"]:
        return
        
    owner_notification = (
        f"**New Message Received**\n\n"
        f"**From:** {first_name} (@{username})\n"
        f"**User ID:** `{user_id}`\n\n"
        f"**Message:** {text}\n\n"
        f"*Reply directly to this message to reply to the user.*"
    )
    
    try:
        sent_msg = bot.send_message(OWNER_ID, owner_notification, parse_mode="Markdown")
        
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO support_chats (message_id, user_id) VALUES (?, ?)", (sent_msg.message_id, user_id))
        conn.commit()
        conn.close()
        
        bot.send_message(user_id, "Your message has been sent. Please wait for a reply.")
    except Exception as e:
        bot.send_message(user_id, "Unable to reach support right now. Please try again later.")
        print(f"Failed to forward: {e}")


# Handle Live Chat Admin Reply
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
                bot.send_message(user_id, f"**Message from Owner:**\n\n{message.text}")
                bot.send_message(OWNER_ID, "Reply successfully sent to user.")
            except Exception as e:
                bot.send_message(OWNER_ID, f"Failed to send reply: {e}")


# Private Channel Join Request Handler
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
        
        print(f"Join Request Logged: {first_name} ({user_id})")
        
        # Approve request immediately if already in the free group
        in_free, _ = verify_user_status(user_id)
        if in_free:
            approve_user_access(user_id, first_name)


# Auto Approver
def approve_user_access(user_id, first_name):
    try:
        bot.approve_chat_join_request(PRIVATE_CHANNEL_ID, user_id)
        print(f"Request Approved: {first_name} ({user_id})")
        
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE pending_requests SET status = 'approved' WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        
        try:
            bot.send_message(user_id, f"Your request to join our VIP Channel has been approved. Welcome, **{first_name}**!")
        except Exception:
            pass
    except ApiTelegramException as e:
        if "USER_ALREADY_PARTICIPANT" in str(e):
            conn = sqlite3.connect("gold_expert_master.db")
            cursor = conn.cursor()
            cursor.execute("UPDATE pending_requests SET status = 'approved' WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()


# Background scan task
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
                if in_free:
                    approve_user_access(user_id, first_name)
        except Exception as e:
            print(f"Background scanner error: {e}")
        time.sleep(15)

threading.Thread(target=scan_all_pending_requests, daemon=True).start()


# Admin Controls Command
@bot.message_handler(commands=['admin'])
def handle_admin_panel(message):
    if message.from_user.id == OWNER_ID:
        markup = InlineKeyboardMarkup()
        btn_broadcast = InlineKeyboardButton("Publish Post", callback_data="admin_broadcast")
        btn_remove = InlineKeyboardButton("Remove / Ban User", callback_data="admin_remove")
        markup.add(btn_broadcast)
        markup.add(btn_remove)
        
        bot.send_message(OWNER_ID, "**Gold Expert Admin Control Panel**\n\nChoose an option:", reply_markup=markup, parse_mode="Markdown")


# Admin Callback Decisions
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_actions(call):
    if call.from_user.id != OWNER_ID:
        return
        
    if call.data == "admin_broadcast":
        msg = bot.send_message(OWNER_ID, "Send or forward the post you want to publish:")
        bot.register_next_step_handler(msg, prepare_broadcast)
        bot.answer_callback_query(call.id)
        
    elif call.data == "admin_remove":
        msg = bot.send_message(OWNER_ID, "Send the numeric Telegram ID of the user you wish to ban:")
        bot.register_next_step_handler(msg, process_remove_user)
        bot.answer_callback_query(call.id)


# Preview Broadcasting Setup
def prepare_broadcast(message):
    global broadcast_msg_payload
    broadcast_msg_payload = message
    
    markup = InlineKeyboardMarkup()
    btn_send = InlineKeyboardButton("Send All", callback_data="confirm_send_all")
    markup.add(btn_send)
    
    bot.send_message(OWNER_ID, "**Post Loaded Successfully.**\nTap the button below to dispatch this message to all bot subscribers:", reply_markup=markup, parse_mode="Markdown")


# Send Broadcast to All
@bot.callback_query_handler(func=lambda call: call.data == "confirm_send_all")
def execute_broadcast(call):
    if call.from_user.id != OWNER_ID:
        return
        
    bot.edit_message_reply_markup(chat_id=OWNER_ID, message_id=call.message.message_id, reply_markup=None)
    bot.send_message(OWNER_ID, "Sending broadcast...")
    
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
            
    bot.send_message(OWNER_ID, f"**Broadcast Finished**\n\n**Delivered:** {success}\n**Blocked:** {failed}", parse_mode="Markdown")
    bot.answer_callback_query(call.id)


# Block User Action
def process_remove_user(message):
    target_id = message.text.strip()
    if target_id.isdigit():
        target_id = int(target_id)
        conn = sqlite3.connect("gold_expert_master.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET status = 'banned' WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        
        bot.send_message(OWNER_ID, f"User `{target_id}` has been successfully banned from using the bot.")
    else:
        bot.send_message(OWNER_ID, "Invalid ID format. Please send numeric characters only.")


# System Clean (Join/Leave messages deleted quietly)
@bot.message_handler(content_types=['new_chat_members', 'left_chat_member'])
def delete_system_messages(message):
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        print(f"Failed to clean system message: {e}")


# Anti-Report Alert Monitor
@bot.message_handler(func=lambda message: any(word in (message.text or "").lower() for word in ["report", "scam", "spam", "flag", "abuse"]))
def monitor_and_log_reports(message):
    user_id = message.chat.id
    first_name = message.from_user.first_name
    username = message.from_user.username or "No_Username"
    text = message.text
    chat_title = message.chat.title or "Direct Message"
    
    log_alert = (
        f"🚨 **Report Activity Flagged**\n\n"
        f"**User:** {first_name} (@{username})\n"
        f"**User ID:** `{user_id}`\n"
        f"**Target Chat:** {chat_title}\n"
        f"**Reported Content:** {text}"
    )
    try:
        bot.send_message(OWNER_ID, log_alert, parse_mode="Markdown")
    except Exception:
        pass


if __name__ == "__main__":
    print("Gold Expert Ultimate VIP Master Robot is running...")
    bot.infinity_polling(timeout=15)
        
