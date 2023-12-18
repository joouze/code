import logging
from telegram.ext import Updater, CommandHandler, CallbackContext
from threading import Timer, Thread
from datetime import datetime, timedelta
import time
# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram configuration
telegram_token = "6462524096:AAHggottkRLwlDkpxhQt0Q1oftZPk7ALmAM"  # Replace with your actual token
updater = Updater(token=telegram_token)

# Initialize free_spots variable
free_spots = 10  # Replace this value with the actual number of free spots

# Dictionary to store the status of each parking spot and the corresponding timers
parking_status = {}
spot_timers = {}
class ParkingTimer:
    def __init__(self, interval, callback, *args):
        self.interval = interval
        self.callback = callback
        self.args = args
        self.start_time = time.time()
        self.thread = Thread(target=self.run)
        self.cancelled = False
        self.thread.start()

    def run(self):
        time.sleep(self.interval)
        # Perform any actions when the timer expires
        self.cleanup()
        # Call the callback function with arguments
        self.callback(*self.args)

    def cleanup(self):
        # You can add cleanup actions here
        pass
    def cancel(self):
        self.cancelled = True
def format_remaining_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
def start(update, context):
    update.message.reply_text('Hello! I am your parking status bot. Use /status to check parking status.')

def status(update, context):
    total_spots = 10  # Replace this value with the actual total number of spots

    status_text = f"Current parking status: {free_spots} free out of {total_spots} total spots."
    update.message.reply_text(status_text)

def add(update, context):
    global free_spots
    spot_number = context.args[0] if context.args else None

    if spot_number is None:
        update.message.reply_text("Please provide the spot number. Usage: /add <spot_number>")
        return

    if spot_number not in parking_status:
        update.message.reply_text(f"Invalid spot number {spot_number}. Please use a valid spot number.")
        return

    if parking_status[spot_number]:
       update.message.reply_text(f"Spot {spot_number} is already occupied.")
    else:
        parking_status[spot_number] = True
        free_spots -= 1
        update.message.reply_text(f"Spot {spot_number} marked as occupied. {free_spots} free spots remaining.")

        # Set a timeout for the spot
        timeout_seconds = 120  # Adjust the timeout duration as needed (e.g., 300 seconds = 5 minutes)
        spot_timers[spot_number] = ParkingTimer(timeout_seconds, clear_spot, spot_number)
def minus(update, context):
    spot_number = context.args[0] if context.args else None

    if spot_number is None:
        update.message.reply_text("Please provide the spot number. Usage: /minus <spot_number>")
        return
    if spot_number not in parking_status or not parking_status[spot_number]:
        update.message.reply_text(f"Spot {spot_number} is not occupied.")
    else:
        clear_spot(spot_number)
def time_left(update, context):
    spot_number = context.args[0] if context.args else None

    if spot_number is None:
        update.message.reply_text("Please provide the spot number. Usage: /timeleft <spot_number>")
        return

    if spot_number not in parking_status:
        update.message.reply_text(f"Invalid spot number {spot_number}. Please use a valid spot number.")
        return

    if not parking_status[spot_number]:
        update.message.reply_text(f"Spot {spot_number} is currently not occupied.")
        return
    if spot_number in spot_timers:
        elapsed_time = int(time.time() - spot_timers[spot_number].start_time)
        remaining_time = spot_timers[spot_number].interval - elapsed_time
        remaining_time_str = format_remaining_time(remaining_time)

        update.message.reply_text(f"Remaining time for Spot {spot_number}: {remaining_time_str}")
    else:
        update.message.reply_text(f"No timer found for Spot {spot_number}.")
def clear_spot(spot_number):
    global free_spots
    parking_status[spot_number] = False
    if spot_number in spot_timers:
        spot_timers[spot_number].cancel()
        del spot_timers[spot_number]

    # Increment free_spots only if it doesn't exceed the total number of spots
    if free_spots < total_spots:
        free_spots += 1

    updater.bot.send_message(chat_id=1030082429, text=f"Spot {spot_number} is now available. {free_spots} free spots remaining.")
def list_slots(update, context):
    status_text = "Parking slots:\n"
    for spot_number, occupied in parking_status.items():
        status_text += f"Spot {spot_number}: {'Occupied' if occupied else 'Available'}\n"
    update.message.reply_text(status_text)

# Set up Telegram bot handlers
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("status", status))
dp.add_handler(CommandHandler("add", add, pass_args=True))
dp.add_handler(CommandHandler("minus", minus, pass_args=True))
dp.add_handler(CommandHandler("list", list_slots))
dp.add_handler(CommandHandler("timeleft", time_left, pass_args=True))

# Initialize parking status (assumes all spots are initially free)
total_spots = 10
parking_status = {str(i): False for i in range(1, total_spots + 1)}

# Start the Telegram bot
updater.start_polling()
updater.idle()
