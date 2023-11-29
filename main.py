from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters import ChatTypeFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
import asyncio
import re
import os
import time
import uuid
import json

API_TOKEN = 'bot_token'
OWNER_ID = user_id
OWNER_ID2 = user_id

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

user_data = {}
global_tasks = {}


class TaskManager:
    
        

    async def _send_message_at_interval(self, group_id, message, message_type, file_id, interval, callback):
        while True:
            await callback(group_id, message, message_type, file_id)
            await asyncio.sleep(interval)

    def add_to_tasks(self, task_info):
        """Add task information to the tasks dictionary."""
        group_id = task_info['group_id']
        if group_id not in global_tasks:
            global_tasks[group_id] = []
        global_tasks[group_id].append(task_info)
        logging.info(f"Task {task_info['task_id']} added to tracking for group {group_id}")

    async def start_task(self, group_id, group_name, message, message_type, file_id, interval, callback):
        # Generate a new task ID each time
        task_id = f"{group_id}_{int(time.time())}"
    
        task_info = {
            'task_id': task_id,
            'group_id': group_id,
            'group_name': group_name,
            'message': message,
            'message_type': message_type,
            'file_id': file_id,
            'interval': interval,
            'task': asyncio.create_task(
                self._send_message_at_interval(group_id, message, message_type, file_id, interval, callback)
            )
        }
    
        if group_id not in global_tasks:
            global_tasks[group_id] = []
        global_tasks[group_id].append(task_info)
        logging.info(f"Task started: {global_tasks}")
    
        # Append task to file for persistence
        append_task_to_file(task_id, group_id, group_name, message, message_type, file_id, interval)





    def stop_task(self, task_id):
        task_found = False
        updated_tasks = []
        # Read all tasks from the file and filter out the task to be stopped
        with open("task_data.txt", "r") as file:
            for line in file:
                task_data = json.loads(line)
                if task_data['task_id'] != task_id:
                    updated_tasks.append(line)
                else:
                    task_found = True
                    # Cancel the running task
                    for group_id, tasks in global_tasks.items():
                        for task_info in tasks:
                            if task_info['task_id'] == task_id:
                                task_info['task'].cancel()
                                tasks.remove(task_info)
                                logging.info(f"Task stopped: {task_id} for group {group_id}")
                                file_id = task_info.get('file_id')
                                if file_id and os.path.exists(file_id):
                                    os.remove(file_id)
                                    logging.info(f"Deleted file: {file_id}")
        # Rewrite the file without the stopped task
        if task_found:
            with open("task_data.txt", "w") as file:
                file.writelines(updated_tasks)
            return True
        else:
            logging.warning(f"Task not found: {task_id}")
            return False

    


task_manager = TaskManager()



async def load_and_start_existing_tasks(task_manager, callback):
    try:
        with open("task_data.txt", "r") as file:
            lines = file.readlines()
            logging.info(f"Found {len(lines)} tasks in task_data.txt")

        for line in lines:
            try:
                task_data = json.loads(line)
                logging.info(f"Loaded task data: {task_data}")

                # Check if group_name is present and then start the task with the existing ID
                if task_data.get('group_name'):
                    # Start the task with the existing task ID
                    task_info = {
                        'task_id': task_data['task_id'],
                        'group_id': task_data['group_id'],
                        'group_name': task_data['group_name'],
                        'message': task_data['message'],
                        'message_type': task_data['message_type'],
                        'file_id': task_data['file_id'],
                        'interval': task_data['interval'],
                        'task': asyncio.create_task(
                            task_manager._send_message_at_interval(task_data['group_id'], task_data['message'], task_data['message_type'], task_data['file_id'], task_data['interval'], callback)
                        )
                    }
                    task_manager.add_to_tasks(task_info)
            except json.JSONDecodeError as e:
                logging.error(f"Error parsing JSON in task_data.txt: {line}. Error: {e}")
    except FileNotFoundError:
        logging.info("task_data.txt not found. No tasks to load.")




def get_active_tasks():
    active_tasks = []
    for _, tasks in global_tasks.items():
        for task in tasks:
            task_info = {
                'task_id': task['task_id'],
                'group_id': task['group_id'],
                'group_name': task['group_name'],
                'message': task['message'],
                'message_type': task['message_type'],
                'file_id': task['file_id'],
                'interval': task['interval'],
            }
            active_tasks.append(task_info)
    return active_tasks


def sanitize_group_name(group_name):
    return re.sub(r'\W+', '', group_name.replace(' ', '_'))

def append_group_to_file(group_id, group_title):
    file_exists = os.path.exists("group_data.txt")
    new_line = f"{group_id}:{group_title}\n"
    if file_exists:
        with open("group_data.txt", "r+") as file:
            lines = file.readlines()
            file.seek(0)
            file.truncate()
            group_id_str = str(group_id)
            if any(group_id_str in line for line in lines):
                lines = [line if group_id_str not in line else new_line for line in lines]
            else:
                lines.append(new_line)
            file.writelines(lines)
    else:
        with open("group_data.txt", "w") as file:
            file.write(new_line)

def append_task_to_file(task_id, group_id, group_name, message, message_type, file_id, interval):
    task_data = {
        'task_id': task_id,
        'group_id': group_id,
        'group_name': group_name,
        'message': message,
        'message_type': message_type,
        'file_id': file_id,
        'interval': interval
    }
    with open("task_data.txt", "a") as file:
        file.write(json.dumps(task_data) + "\n")


def get_list_of_groups_as_commands():
    try:
        with open("group_data.txt", "r") as file:
            groups = file.readlines()
        if not groups:
            return ["No groups available"]
        return [f"/{sanitize_group_name(name.strip().split(':')[1])}" for name in groups if len(name.strip().split(':')) >= 2]
    except FileNotFoundError:
        return ["No groups available"]

async def send_message_to_group(group_id, message, message_type='text', file_id=None):
    if message_type == 'text':
        await bot.send_message(chat_id=group_id, text=message)
    elif message_type == 'photo':
        with open(file_id, 'rb') as photo:
            await bot.send_photo(chat_id=group_id, photo=photo, caption=message)
    elif message_type == 'video':
        with open(file_id, 'rb') as video:
            await bot.send_video(chat_id=group_id, video=video, caption=message)

# Ensure the media directory exists
if not os.path.exists("media"):
    os.makedirs("media")

# Handlers for media files
# Handlers for media files



@dp.my_chat_member_handler(ChatTypeFilter(chat_type=types.ChatType.SUPERGROUP))
async def bot_added_to_group(update: types.ChatMemberUpdated):
    if update.new_chat_member.status == 'member':
        group_id = update.chat.id
        group_title = update.chat.title
        append_group_to_file(group_id, group_title)
        logging.info(f"Added to group: {group_title} (ID: {group_id})")

@dp.message_handler(commands=['start'], user_id=[OWNER_ID, OWNER_ID2])
async def start_command_handler(message: types.Message):
    commands = get_list_of_groups_as_commands()
    command_list_message = "\n".join(commands)
    await message.reply(f"guruhni tanlang:\n{command_list_message}")
    user_data[message.from_user.id] = {'stage': 'awaiting_group_selection'}

@dp.message_handler(content_types=['photo'], user_id=[OWNER_ID, OWNER_ID2])
async def handle_photo(message: types.Message):
    user_id = message.from_user.id

    if 'group' not in user_data.get(user_id, {}):
        await message.reply("/start ni kiritib guruhni tanlang.")
        return

    if not message.caption:
        await message.reply("rasmni text xabar bilan yuboring.")
        return

    unique_filename = str(uuid.uuid4()) + '.jpg'
    await message.photo[-1].download(destination=os.path.join('media', unique_filename))

    user_data[user_id].update({
        'file_id': os.path.join('media', unique_filename),
        'scheduled_message': message.caption,
        'message_type': 'photo',
        'stage': 'awaiting_timer',
        'group': user_data[user_id].get('group')  # Preserve existing group
    })

    scheduling_options = "/har_soat \n/har_kun \n/har_hafta \n/har_6_sekund "
    await message.reply(" qancha vaqtda yuborilsin?\n" + scheduling_options)


    
@dp.message_handler(content_types=['video'], user_id=[OWNER_ID, OWNER_ID2])
async def handle_video(message: types.Message):
    user_id = message.from_user.id

    if 'group' not in user_data.get(user_id, {}):
        await message.reply("iltimos /start ni kiritib guruhni tanlang.")
        return

    if not message.caption:
        await message.reply("videoni text xabar bilan yuboring.")
        return

    unique_filename = str(uuid.uuid4()) + '.mp4'
    await message.video.download(destination=os.path.join('media', unique_filename))

    user_data[user_id].update({
        'file_id': os.path.join('media', unique_filename),
        'scheduled_message': message.caption,
        'message_type': 'video',
        'stage': 'awaiting_timer',
        'group': user_data[user_id].get('group')  # Preserve existing group
    })

    scheduling_options = "/har_soat \n/har_kun \n/har_hafta \n/har_6_sekund "
    await message.reply("video saqlandi. qancha vaqtda yuborilsin?\n" + scheduling_options)


@dp.message_handler(content_types=['text', 'photo', 'video'], user_id=[OWNER_ID, OWNER_ID2])
async def handle_message(message: types.Message):
    user_id = message.from_user.id

    if user_id not in user_data:
        return

    # if message.text.startswith('/stop_task'):
    #     parts = message.text.split()
    #     if len(parts) == 3:
    #         _, command_group_name, task_id = parts
    #         await handle_stop_task_by_group_name_and_id(message, command_group_name, task_id)
    #     else:
    #         await message.reply("quyidagi buyqurni kiriting: /stop_task [group_name] [task_id]")
    #     return

    if message.text.startswith('/stop'):
        await stop_command_handler(message)
        return

    if user_data[user_id]['stage'] == 'awaiting_group_selection':
        command = message.get_command()[1:]  # Extract command from message
        selected_group_id = None
        try:
            with open('group_data.txt', 'r') as file:
                for group in file:
                    parts = group.strip().split(':')
                    if len(parts) >= 2:
                        gid, name = parts[0], parts[1]
                        if sanitize_group_name(name) == command:
                            selected_group_id = gid
                            break

            if selected_group_id:
                user_data[user_id] = {'stage': 'awaiting_message', 'group': selected_group_id}
                await message.reply("tanlangan guruhga yuborilishi kerak bolgan xabarni kiriting.")
            else:
                await message.reply("xato tanlov. guruhni togri tanlang.")
        except FileNotFoundError:
            await message.reply("guruh malumoti topilmadi.")
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            await message.reply("muommo paydo boldi.")

    elif user_data[user_id]['stage'] == 'awaiting_message':
        if message.content_type == 'text':
            user_data[user_id]['scheduled_message'] = message.text
            user_data[user_id]['message_type'] = 'text'
        elif message.content_type == 'photo':
            # Assuming photo file ID is already stored in user_data
            user_data[user_id]['scheduled_message'] = message.caption
            user_data[user_id]['message_type'] = 'photo'
        elif message.content_type == 'video':
            # Assuming video file ID is already stored in user_data
            user_data[user_id]['scheduled_message'] = message.caption
            user_data[user_id]['message_type'] = 'video'

        user_data[user_id]['stage'] = 'awaiting_timer'
        scheduling_options = "/har_soat \n/har_kun \n/har_hafta \n/har_6_sekund "
        await message.reply("rasm saqlandi. qancha vaqtda yuborilsin?\n" + scheduling_options)

    elif user_data[user_id]['stage'] == 'awaiting_timer':
        if message.text.startswith('/har_'):
            interval = get_interval_from_command(message.text)
            if interval is not None:
                selected_group_id = user_data[user_id]['group']
                scheduled_message = user_data[user_id]['scheduled_message']
                message_type = user_data[user_id].get('message_type', 'text')
                file_id = user_data[user_id].get('file_id', None)
                group_name = None
                try:
                    with open('group_data.txt', 'r') as file:
                        for group in file.readlines():
                            parts = group.strip().split(':')
                            if len(parts) >= 2 and parts[0] == selected_group_id:
                                group_name = parts[1]
                                break
                    if group_name:
                        await task_manager.start_task(selected_group_id, group_name, scheduled_message, message_type, file_id, interval, send_message_to_group)
                        await message.reply(f" '{scheduled_message[:20]}... xabari'  har{message.text[7:]} da  {group_name} guruhiga yuboriladi.")
                        user_data[user_id]['stage'] = None
                    else:
                        await message.reply("guruh topilmadi.")
                except FileNotFoundError:
                    await message.reply("guruh topilmadi.")
            else:
                await message.reply("xato tanlov. quyidagilardan birini tanlang")
        else:
            await message.reply("quyidagilardan birini tanlang.")

def get_interval_from_command(command):
    command_to_interval = {
        '/har_soat': 3600,
        '/har_kun': 86400,
        '/har_hafta': 604800,
        '/har_6_sekund': 6
    }
    return command_to_interval.get(command)

# async def handle_stop_task_by_group_name_and_id(message: types.Message, command_group_name: str, task_id: str):
#     for i in get_active_tasks(task_manager):
#         sanitized_group_name = sanitize_group_name(i['group_name'])
#         if sanitized_group_name == command_group_name and i['task_id'] == task_id:
#             task_manager.stop_task(i['task_id'])
#             await message.reply(f"Task {task_id} for group {sanitized_group_name} has been stopped")
#             return
#     await message.reply("Task not found.")

@dp.message_handler(commands=['stop'], user_id=[OWNER_ID, OWNER_ID2])
async def stop_command_handler(message: types.Message):
    activee = get_active_tasks()
    logging.info(f"Active tasks: {activee}")
    if not activee:
        await message.reply("No active tasks.")
        return

    inline_kb = InlineKeyboardMarkup(row_width=1)
    for task_info in activee:
        button_text = f"Stop: {task_info['group_name']} - '{task_info['message'][:80]}...' (har {task_info['interval']}s)"
        callback_data = f"stop_{task_info['task_id']}"
        inline_kb.add(InlineKeyboardButton(button_text, callback_data=callback_data))

    await message.reply("toxtatish uchun topshiriqni tanlang:", reply_markup=inline_kb)

@dp.callback_query_handler(lambda c: c.data.startswith('stop_'), user_id=[OWNER_ID, OWNER_ID2])
async def handle_callback_stop_task(callback_query: types.CallbackQuery):
    task_id_to_stop = '_'.join(callback_query.data.split('_')[1:])

    stopped_task_info = None
    for task in get_active_tasks():
        if task_id_to_stop == task['task_id']:
            stopped_task_info = task
            break

    if stopped_task_info and task_manager.stop_task(task_id_to_stop):
        response_message = (
            f"quyidagi id ga ega bolgan xabar toxtatildi {task_id_to_stop}\n"
            f"guruh: {stopped_task_info['group_name']}\n"
            f"xabar: '{stopped_task_info['message']}'\n"
            f"takrorlash: {stopped_task_info['interval']}s"
        )
        await bot.send_message(callback_query.from_user.id, response_message)
    else:
        await bot.send_message(callback_query.from_user.id, "topshiriq topilmadi.")


async def main():
    # Initialize Task Manager
    task_manager = TaskManager()

    # Load and start existing tasks
    await load_and_start_existing_tasks(task_manager, send_message_to_group)

    # Start polling
    await dp.start_polling()


if __name__ == '__main__':
    asyncio.run(main())
