import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
import asyncio
from asyncio_mqtt import Client as AsyncioMqttClient
import time
from aiogram import executor
import asyncio_mqtt

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram configuration
telegram_token = "6462524096:AAHggottkRLwlDkpxhQt0Q1oftZPk7ALmAM"  # Replace with your actual token
bot = Bot(token=telegram_token)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# MQTT configuration
mqtt_broker_address = "localhost"
mqtt_port = 1883
mqtt_topic = "parking_status"

# Initialize MQTT client
mqtt_client = AsyncioMqttClient(hostname=mqtt_broker_address, port=mqtt_port)

loop = asyncio.get_event_loop()

async def on_connect(client, flags, rc):
    print("Connected to MQTT broker with result code " + str(rc))
    # Subscribe to the MQTT topic
    await client.subscribe(mqtt_topic)

async def on_message(client, topic, payload, qos, properties):
    received_message = payload.decode("utf-8")
    print(f"Received message: {received_message}")

# Connection parameters for MQTT
connect_params = {
    "hostname": mqtt_broker_address,
    "port": mqtt_port,
    "on_connect": on_connect,
    "on_message": on_message,
}

async def connect_to_mqtt():
    await mqtt_client.connect(**connect_params)

# Initialize free_spots variable
free_spots = 10  # Replace this value with the actual number of free spots

# Dictionary to store the status of each parking spot and the corresponding timers
total_spots = 10
parking_status = {str(i): False for i in range(1, total_spots + 1)}
spot_timers = {}

class ParkingTimer:
    def __init__(self, interval, callback, *args):
        self.interval = interval
        self.callback = callback
        self.args = args
        self.start_time = time.time()
        self.cancelled = False
        asyncio.create_task(self.run())

    async def run(self):
        await asyncio.sleep(self.interval)
        # Perform any actions when the timer expires
        self.cleanup()
        # Call the callback function with arguments
        self.callback(*self.args)

    def cleanup(self):
        # Notify when the timer expires and the spot is now available
        spot_number = self.args[0]
        message = self.args[1]
        global free_spots, total_spots

        if spot_number in parking_status and parking_status[spot_number]:
            parking_status[spot_number] = False
            if spot_number in spot_timers:
                del spot_timers[spot_number]

                # Increment free_spots only if it doesn't exceed the total number of spots
                if free_spots < total_spots:
                    free_spots += 1
                loop.create_task(notify_spot_available(spot_number, message))
            else:
                print(f"No timer found for Spot {spot_number}.")

    def cancel(self):
        self.cancelled = True

async def get_remaining_time(spot_number):
    remaining_time = 0
    if spot_number in spot_timers:
        elapsed_time = time.time() - spot_timers[spot_number].start_time
        remaining_time = max(0, spot_timers[spot_number].interval - elapsed_time)
    return remaining_time

def format_remaining_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer('Hello! I am your parking status bot. Use /status to check parking status.')

@dp.message_handler(commands=['status'])
async def status(message: types.Message):
    status_text = f"Current parking status: {free_spots} free out of {total_spots} total spots."
    await message.answer(status_text)

@dp.message_handler(commands=['add'])
async def add(message: types.Message):
    global free_spots, total_spots
    loop = message.bot.loop
    spot_number = message.get_args()
    if spot_number is None or not spot_number.isdigit():
        await message.answer("Please provide a valid spot number. Usage: /add <spot_number>")
        return
 spot_number = int(spot_number)
    if spot_number < 1 or spot_number > total_spots:
        await message.answer(f"Invalid spot number {spot_number}. Please use a valid spot number.")
        return

    if spot_number in parking_status and parking_status[spot_number]:
        await message.answer(f"Spot {spot_number} is already occupied.")
    else:
        parking_status[spot_number] = True
        free_spots -= 1
        await message.answer(f"Spot {spot_number} marked as occupied. {free_spots} free spots remaining.")

        # Set a timeout for the spot
        timeout_seconds = 20  # Adjust the timeout duration as needed (e.g., 300 seconds = 5 minutes)
        spot_timers[spot_number] = ParkingTimer(timeout_seconds, clear_spot, spot_number, message)

        # Publish the status update to the MQTT topic
        await publish_to_mqtt(f"Spot {spot_number} is now occupied. {free_spots} free spots remaining.")

@dp.message_handler(commands=['minus'])
async def minus(message: types.Message):
    global free_spots, total_spots
    spot_number = message.get_args()

    if spot_number is None or not spot_number.isdigit():
        await message.answer("Please provide a valid spot number. Usage: /minus <spot_number>")
        return

    spot_number = int(spot_number)

    if spot_number < 1 or spot_number > total_spots:
        await message.answer(f"Invalid spot number {spot_number}. Please use a valid spot number.")
        return

    if spot_number not in parking_status or not parking_status[spot_number]:
        await message.answer(f"Spot {spot_number} is not occupied.")
    else:
        await clear_spot(spot_number, message)

@dp.message_handler(commands=['timeleft'])
async def timeleft(message: types.Message):
    spot_number = message.get_args()

    if spot_number is None or not spot_number.isdigit():
        await message.answer("Please provide a valid spot number. Usage: /timeleft <spot_number>")
        return
    spot_number = int(spot_number)

    if spot_number < 1 or spot_number > total_spots:
        await message.answer(f"Invalid spot number {spot_number}. Please use a valid spot number.")
        return

    if not parking_status[spot_number]:
        await message.answer(f"Spot {spot_number} is currently not occupied.")
    else:
        remaining_time = await get_remaining_time(spot_number)
        await message.answer(f"Remaining time for Spot {spot_number}: {format_remaining_time(remaining_time)}")
@dp.message_handler(commands=['list'])
async def list_slots(message: types.Message):
    occupied_spots = [spot_number for spot_number, occupied in parking_status.items() if occupied]

    if not occupied_spots:
        await message.answer("No spots are currently occupied.")
    else:
        status_text = "Occupied parking spots:\n"
        for spot_number in occupied_spots:
            status_text += f"Spot {spot_number}\n"
        await message.answer(status_text)

async def notify_spot_available(spot_number, message):
    global free_spots
    # Increment free_spots only if it doesn't exceed the total number of spots
    if free_spots < total_spots:
        free_spots += 1

    try:
        # Publish the status update to the MQTT topic
        loop.create_task(publish_to_mqtt(f"Spot {spot_number} is now available. {free_spots} free spots remaining."))

        # Send a message to a specific chat ID
        chat_id = 1030082429  # Replace with your actual chat ID
        loop.create_task(message.bot.send_message(chat_id, f"Spot {spot_number} is now available. {free_spots} free spots remaining."))
    except asyncio_mqtt.error.MqttCodeError as e:
        print(f"Error publishing to MQTT: {e}")
        # Handle the error as needed, for example, log it or retry the connection
        pass

async def clear_spot(spot_number, message):
    global spot_timers
    parking_status[spot_number] = False
    if spot_number in spot_timers:
        spot_timers[spot_number].cancel()
        del spot_timers[spot_number]

        # Notify that the spot is available
        await notify_spot_available(spot_number, message)
    else:
        print(f"No timer found for Spot {spot_number}.")

async def publish_to_mqtt(message):
    await mqtt_client.publish(mqtt_topic, message)

if __name__ == '__main__':
    loop.create_task(connect_to_mqtt())
    executor.start_polling(dp, loop=loop, skip_updates=True)
    try:
        loop.run_forever()
    finally:
        loop.close()


