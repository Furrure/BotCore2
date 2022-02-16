import nextcord as discord

try:
    import OS_patch as patch
except ImportError:
    import os
    import shutil
    class patch:
        import os
        import shutil

        def print(*args, end="\n"):
            final = ""
            for param in args:
                final += " " + str(param)
                
            print(final + str(end))

        def input(string):
            return input(string)
            
        def write_file(file_path, contents):
            with open(file_path, "wb") as file:
                file.write(contents)

        def read_file(file_path):
            content = None
            with open(file_path, "rb") as file:
                content = file.read()
            return content

        def append_to_file(file_path, content):
            with open(file_path, "ab") as file:
                file.write(content.encode())
            
        def openfile(*args, **kwargs):
            return open(*args, **kwargs)

        def mkdir(file_path):
            os.mkdir(file_path)

        def rmtree(file_path):
            shutil.rmtree(file_path)

        def isfile(file_path):
            return os.path.isfile(file_path)

        def isdir(file_path):
            return os.path.isdir(file_path)

        def listdir(file_path):
            return os.listdir(file_path)

        def config_read(file_path, value_if_non_existant):
            if not(isfile(file_path)):
                opened = patch.openfile(file_path, "wb")
                opened.write(value_if_non_existant.encode("utf-8"))
                opened.close()
                opened = patch.openfile(file_path, "rb")
                content = opened.read()
                opened.close()
                return content.decode("utf-8")
            else:
                return patch.read_file(file_path).decode()

        def get_working_directory():
            return os.getcwd()

import time
import os
import asyncio
import sys
import threading
import re
import getopt
import pickle

'''
Event types:
System
Bot
Extension - dependant on name
FangCore

Universal Events:
Notice
Error
Startup
Shutdown

Bot Events:
command

EVENT: headers

event extensions have a dictionary passed to them that provide event-specific information

EVENT:init
EVENT:message
EVENT:ioloop *
EVENT:shutdown *
EVENT:command
EVENT:botready
EVENT:prefix

COMMAND:x

INTERVAL:x


Big Todo:

Fix Search log

Completely Static extensions

fix errors again

Better Config

Application->Discord shell

Little Todo:

Make All input fields accept a list of items
Add banned users
DeleteMessage Function
Finish Message Object, add IDs, storage functions, and so on
Add buttons, Dropdowns, and whatnot
add channel limiter
Fix Timeout handling?
Set Status Functions - static status
Add Configuration functions
Add command line Folder specification
Add help function
"Disabled Commands" for internal commands
Fix error Handling
Add as many functions as possible
legacy variables
More messages features
Easy embedding/nice features
Command blacklist
internal commands
Rest of the events
Packages
Start and Stop Bot
SYSTEM shows available object spaces
Button/Dropdown Interaction system
add reply commands
'''

VERSION = "2.0.0"
COMMAND_INTERPRETER = "BotCore 2"
API_WRAPPER = "nextcord"

working_directory = patch.get_working_directory()
config = {}
extension_share = {}
bot_started = False
client = None
fang = None
loop = None
fatal_state = False
command_blacklist = []

send_buffer = {}

#{ChannelID:[{"Type":"Plain", "Content":"Test", "Meta":{"Combine":True}}]}

active_inputs = {}
input_id_counter = 0

#{ChannelID:[{"Whitelisted IDs":[], "Response Prefix":[], "Result Function":None, "Timeout":0}]}
interval_tasks = []
async_run_buffer = []

async def interval_extension_runner(extension_header, delay):
    global client
    try:
        while True:
            system_object = generate_system_object(extension_header)
            bot_object = generate_bot_object(client)
            call_extensions(extension_header, {"SYSTEM":system_object, "BOT":bot_object})
            await asyncio.sleep(delay)
    except Exception:
        pass


async def set_status(content, activity_type=1):
    global client
    await client.change_presence(activity=discord.Activity(name=str(content), type=activity_type))

async def async_runner():
    global async_run_buffer
    while 1:
        try:
            if len(async_run_buffer) > 0:
                async_run_buffer[0][1](await async_run_buffer[0][0])
                del async_run_buffer[0]
        except Exception as exc:
            log("System", "Error", "An error occured while trying to run an asynchronous function: " + str(exc), get_config("bot_folder"))
            del async_run_buffer[0]
        await asyncio.sleep(0.1)


def start_interval_extensions(bot_folder):
    ensure_folder(bot_folder + "/Extensions")
    extension_paths = patch.listdir(bot_folder + "/Extensions")
    for path in extension_paths:
        try:
            content = patch.read_file(bot_folder + "/Extensions/" + path).decode()
            if "'''" in content.strip().split("\n")[0]:
                if content.strip().split("\n")[0][:12].strip() == "'''INTERVAL:":
                    try:
                        interval = int(content.strip().split("\n")[0][12:].strip().replace("'''", ""))
                        interval_tasks.append(asyncio.create_task(interval_extension_runner("INTERVAL:" + str(interval), interval)))
                    except Exception:
                        log("System", "Error", f"Interval extension in " + str(path) + " does not provide a valid number for delay", bot_folder)
                    
        except Exception as exc:
            log("System", "Error", f"Python error when checking extension file for header {header} - {str(exc)}", bot_folder)

def stop_interval_extensions():
    global interval_tasks
    for task in interval_tasks:
        task.cancel()
    interval_tasks = []

def call_extensions(header, pass_globals={}, pass_locals={}): #Execute all functions with a certain header
    bot_folder = get_config("bot_folder")
    ensure_folder(bot_folder + "/Extensions")
    extension_paths = patch.listdir(bot_folder + "/Extensions")
    extensions_to_run = []
    for path in extension_paths:
        try:
            content = patch.read_file(bot_folder + "/Extensions/" + path).decode()
            if "'''" in content.strip().split("\n")[0]:
                if content.strip().split("\n")[0].strip() == "'''" + str(header).strip() + "'''":
                    extensions_to_run.append([content, path])
        except Exception as exc:
            log("System", "Error", f"Python error when checking extension file for header {header} - {str(exc)}", bot_folder)
    if extensions_to_run != []:
        for content in extensions_to_run:
            try:
                exec(content[0], pass_globals)
            except Exception as exc:
                log("System", "Error", f"{content[1]} failed with the following error during execution: {str(exc)}", bot_folder)
    else:
        return False


def check_for_extension_header(header):
    bot_folder = get_config("bot_folder")
    ensure_folder(bot_folder + "/Extensions")
    extension_paths = patch.listdir(bot_folder + "/Extensions")
    for path in extension_paths:
        try:
            content = patch.read_file(bot_folder + "/Extensions/" + path).decode("utf-8")
            if "'''" in content.strip().split("\n")[0]:
                if content.strip().split("\n")[0].strip() == "'''" + str(header).strip() + "'''":
                    return True
        except Exception as exc:
            log("System", "Error", f"Python error when checking extension file for header {header} - {str(exc)}", bot_folder)
    return False


def log(event_type, event, content, bot_folder_path): #Universal logging function for the bot
    log_string = f"[{time.ctime()}] [{event_type}/{event}] - {content}"
    log_string = log_string.replace("\\", "\\\\")
    log_string = log_string.replace("\n", "\\n")
    log_string += "\n"
    patch.print(log_string)
    if patch.isfile(bot_folder_path + "/bot_log.log"):
        patch.append_to_file(bot_folder_path + "/bot_log.log", log_string)

def raise_fatal_error(error_type, error_text, bot_folder):
    global loop
    global fatal_state
    fatal_state = True 
    log("System", "Error", "Fatal error occurred - " + str(error_text), bot_folder)
    try:
        loop.create_task(stop_bot("Fatal error occurred"))
    except Exception:
        try:
            loop.stop()
            loop.close()
        except Exception:
            sys.exit()
    

	
def initialize(file_path, keep_authority=None): #Initializes all functions, also runs any extensions with the EVENT:init FangOS Extension Header
    global fang
    global bot_started
    global active_inputs

    active_inputs = {}

    stop_interval_extensions()
    if not(patch.isdir(file_path)):
        patch.mkdir(file_path)
    patch.config_read(file_path + "/bot_log.log", "")
    log("System", "Notice", "Starting initialization from {}".format(file_path), file_path)
    if not(keep_authority):
        config['authority'] = patch.config_read(file_path + "/authority.txt", "").strip()
    config['callsign'] = patch.config_read(file_path + "/callsign.txt", "botcore").strip()
    config['intents'] = patch.config_read(file_path + "/intents.txt", "").strip()
    config['command_blacklist'] = patch.config_read(file_path + "/command_blacklist.txt", "").strip()
    if config['callsign'].strip() == "":
        raise_fatal_error(RuntimeError, "A callsign is not defined for this bot", file_path)
    config['channel'] = patch.config_read(file_path + "/channel.txt", "ALL").strip()
    if config['channel'].strip() == "":
        raise_fatal_error(RuntimeError, "A channel limiter is not defined for this bot", file_path)
    config['help'] = patch.config_read(file_path + "/help.txt", "The developer has not yet included help instructions.").strip()
    config['token'] = patch.config_read(file_path + "/token.txt", "").strip()
    if config['token'].strip() == "":
        raise_fatal_error(RuntimeError, "A token is not defined for this bot", file_path)
    if not(patch.isdir(file_path + "/Extensions")):
        patch.mkdir(file_path + "/Extensions")
    if not(patch.isdir(file_path + "/Apps")):
        patch.mkdir(file_path + "/Apps")
    if not(patch.isdir(file_path + "/Storage")):
        patch.mkdir(file_path + "/Storage")
    if not(patch.isdir(file_path + "/Storage/UserStorage")):
        patch.mkdir(file_path + "/Storage/UserStorage")
    if not(patch.isdir(file_path + "/Storage/ChannelStorage")):
        patch.mkdir(file_path + "/Storage/ChannelStorage")
    if not(patch.isdir(file_path + "/Storage/GuildStorage")):
        patch.mkdir(file_path + "/Storage/GuildStorage")
    if not(patch.isdir(file_path + "/Storage/BotStorage")):
        patch.mkdir(file_path + "/Storage/BotStorage")
    
    config["bot_folder"] = file_path
    log("Bot", "Notice", "Stopping any existing Interval Extensions", get_config("bot_folder"))
    stop_interval_extensions()

    command_blacklist = get_config("command_blacklist").strip().split("\n")

    log("System", "Notice", "Running Initialization Event Extensions", file_path)
    system_object = generate_system_object("EVENT:init")
    call_extensions("EVENT:init", {"SYSTEM":system_object})
    log("System", "Notice", "Initialization Event Extension execution complete", file_path)
    
    log("System", "Notice", "Completed initialization", file_path)
    start_bot("Initialization Complete")


def ensure_folder(file_path):
    if not(patch.isdir(file_path)):
        patch.mkdir(file_path)





def start_bot(reason=None): #Starts the bot, and puts it online
    global client
    global bot_started
    global loop
    if bot_started:
        return
    else:
        log("Bot", "Startup", f"Starting Bot - {str(reason)}", get_config("bot_folder"))
        intents = discord.Intents.default()
        if "members" in get_config("intents").strip().split("\n"):
            intents.members = True
        log("Bot", "Startup", "Initializing event loop and client...", get_config("bot_folder"))
        loop = asyncio.new_event_loop()
        client = discord.Client(intents=intents, loop=loop)
        loop.set_exception_handler(on_error)
        
        log("Bot", "Startup", "Starting event loop and initializing event functions...", get_config("bot_folder"))
        asyncio.set_event_loop(loop)
        client.event(on_ready)
        client.event(on_message)
        loop.create_task(io_handler())
        loop.create_task(async_runner())
        log("Bot", "Startup", "Starting and connecting bot...", get_config("bot_folder"))
        loop.run_until_complete(client.start(get_config("token").strip()))
        

async def stop_bot(reason=None): #Stops the bot, and puts it offline
    global bot_started
    global client
    global loop
    if bot_started:
        if reason:
            log("Bot", "Shutdown", f"Stopping Bot - {str(reason)}", get_config("bot_folder"))
        bot_started = False
        log("Bot", "Shutdown", "Clearing client cache and logging out...", get_config("bot_folder"))
        client.clear()
        log("System", "Shutdown", "Closing and clearing event loop...", get_config("bot_folder"))
        await client.close()
        loop.stop()
        loop.close()
        

def check_for_prefix(string, prefix_list): #Returns false if no prefix, returns string without prefix if the prefix is detected
    string = str(string)
    for prefix in prefix_list:
        try:
            if prefix.strip().lower() in string.strip()[:len(prefix)].lower():
                if len(prefix.strip()) == len(string.strip()):
                    return ""
                return string.strip()[len(prefix):]

        except Exception as exc:
            pass
    return None

def parse_command(string):
        try:
            string = string.strip()
            string = string.replace("\r\n", " ")
            string = string.replace("\n", " ")
        except Exception:
            return
        #[[commands],[options],commandword,raw rest of command,[simple_commands],simple_command_word, simple_raw_rest of command]
        parsed = [[],[],"","", string.split(" "), string.split(" ")[0].strip(), string.strip()[len(string.split(" ")[0].strip()):]]
        letter_number = 0
        letter = ""
        ignore_state = False
        last_letter_space = False
        option_state = False
        temp_split_parse = ""
        if len(string) == 0:
            return parsed

        while True:
            letter = string[letter_number]
            if letter == "\\":
                if ignore_state:
                    temp_split_parse += "\\"
                    ignore_state = False
                else:
                    ignore_state = True

            if letter == " ":
                if not(last_letter_space) and not(ignore_state):
                    if option_state:
                        parsed[1].append(temp_split_parse)
                    else:
                        parsed[0].append(temp_split_parse)
                    temp_split_parse = ""
                    option_state = False
                else:
                    if ignore_state:
                        temp_split_parse += " "
                        ignore_state = False
                    if last_letter_space:
                        pass


            if letter == "-":
                if option_state:
                    temp_split_parse += letter
                if not(ignore_state) and not(option_state):
                    option_state = True
                    parsed[0].append(temp_split_parse)
                    temp_split_parse = ""
                else:
                    temp_split_parse += letter
                    ignore_state = False

            if letter != " " and letter != "\\" and letter != "-":
                temp_split_parse += letter
                last_letter_space = False
                
            letter_number += 1
            if letter_number == len(string):
                if not(temp_split_parse.strip() == ""):
                    if option_state:
                        parsed[1].append(temp_split_parse)
                    else:
                        parsed[0].append(temp_split_parse)
                break
        if len(parsed[0]) >= 1:
            parsed[2] = parsed[0][0]
            parsed[3] = string[len(parsed[0][0]):]
            del parsed[0][0]



        return parsed

def get_config(key):
    if key in config.keys():
        return config[key]
    else:
        return ""

def set_config(key, content):
    config[key] = str(content)

def HasAuthority(ID):
    for test_ID in get_config("authority").split("\n"):
        if test_ID.strip() == str(ID).strip():
            return True
    return False

def user_store(ID, varname, content):
    ensure_folder(get_config("bot_folder") + "/Storage/UserStorage/" + str(ID))
    patch.write_file(get_config("bot_folder") + "/Storage/UserStorage/" + str(ID) + "/" + str(varname), pickle.dumps(content))

def channel_store(ID, varname, content):
    ensure_folder(get_config("bot_folder") + "/Storage/ChannelStorage/" + str(ID))
    patch.write_file(get_config("bot_folder") + "/Storage/ChannelStorage/" + str(ID) + "/" + str(varname), pickle.dumps(content))

def guild_store(ID, varname, content):
    ensure_folder(get_config("bot_folder") + "/Storage/GuildStorage/" + str(ID))
    patch.write_file(get_config("bot_folder") + "/Storage/GuildStorage/" + str(ID) + "/" + str(varname), pickle.dumps(content))

def general_store(varname, content):
    patch.write_file(get_config("bot_folder") + "/Storage/BotStorage/" + str(varname), pickle.dumps(content))

def user_read(ID, varname):
    if patch.isfile(get_config("bot_folder") + "/Storage/UserStorage/" + str(ID) + "/" + str(varname)):
        return pickle.loads(patch.read_file(get_config("bot_folder") + "/Storage/UserStorage/" + str(ID) + "/" + str(varname)))
    return None

def channel_read(ID, varname):
    if patch.isfile(get_config("bot_folder") + "/Storage/ChannelStorage/" + str(ID) + "/" + str(varname)):
        return pickle.loads(patch.read_file(get_config("bot_folder") + "/Storage/ChannelStorage/" + str(ID) + "/" + str(varname)))
    return None

def guild_read(ID, varname):
    if patch.isfile(get_config("bot_folder") + "/Storage/GuildStorage/" + str(ID) + "/" + str(varname)):
        return pickle.loads(patch.read_file(get_config("bot_folder") + "/Storage/GuildStorage/" + str(ID) + "/" + str(varname)))
    return None

def general_read(varname):
    if patch.isfile(get_config("bot_folder") + "/Storage/BotStorage/" + str(varname)):
        return pickle.loads(patch.read_file(get_config("bot_folder") + "/Storage/BotStorage/" + str(varname)))
    return None

def extension_share_add(key, value):
    global extension_share
    extension_share[str(key)] = value

def extension_share_get(key):
    global extension_share
    if str(key) in extension_share.keys():
        return extension_share[str(key)]
    else:
        return None

def send_message(channel_ID, content, view=None, _context_message=None):
    if type(content) == type(special_message()):
        if int(channel_ID) not in send_buffer.keys():
            send_buffer[int(channel_ID)] = []
        if view:
            send_buffer[int(channel_ID)].append({"Type":"Special", "Content":content, "View":view, "Context":(_context_message if _context_message else None)})
        else:
            send_buffer[int(channel_ID)].append({"Type":"Special", "Content":content, "View":None, "Context":(_context_message if _context_message else None)})
    else:
        if int(channel_ID) not in send_buffer.keys():
            send_buffer[int(channel_ID)] = []
        if view:
            send_buffer[int(channel_ID)].append({"Type":"Plain", "Content":str(content), "View":view})
        else:
            send_buffer[int(channel_ID)].append({"Type":"Plain", "Content":str(content), "View":None})

def direct_send_message(channel_ID, *args, **kwargs):
    global client
    channel = client.get_channel(channel_ID)
    client.loop.create_task(channel.send(*args, **kwargs))

def get_input(function, channel_id, content, whitelisted_ids=[], response_prefixes=[], timeout=0, _context_message=None):
    global active_inputs

    if type(response_prefixes) != type([]):
        response_prefixes = [str(response_prefixes)]
    if type(whitelisted_ids) != type([]):
        whitelisted_ids = [int(whitelisted_id)]
    if not(channel_id in active_inputs.keys()):
        active_inputs[channel_id] = []
    breaker = False
    for input_index in range(len(active_inputs[channel_id])):
        for whitelisted_id in whitelisted_ids:
            if whitelisted_id in active_inputs[channel_id][input_index]["Whitelisted ID"]:
                del active_inputs[channel_id][input_index]
                breaker = True
                break
        if breaker: break

    active_inputs[channel_id].append({"Whitelisted ID":whitelisted_ids, "Response Prefix":response_prefixes, "Result Function":function, "Timeout":timeout, "Start Time":time.time(), "Type":"TEXT_INPUT"})
    send_message(channel_id, content, _context_message=_context_message)

def get_button_input(function, channel_id, content, button_options, whitelisted_ids=[], timeout=None, _context_message=None):

    if type(whitelisted_ids) != type([]):
        whitelisted_ids = [int(whitelisted_id)]

    view = discord.ui.View(timeout=timeout)
    class counter:
        pass
    counter.count = 0
    button_mappings = {}
    for button_index in range(len(button_options)):
        view.add_item(discord.ui.Button(label=str(button_options[button_index]), custom_id=str(button_index)))
        button_mappings[str(button_index)] = button_options[button_index]

    async def interaction_manager(interaction):
        counter.count += 1
        allow = False
        if len(whitelisted_ids) > 0:
            if interaction.user.id in whitelisted_ids:
                allow = True
        else:
            allow = True
        if allow:
            interaction_obj = generate_interaction_object(interaction_obj=interaction, button_mappings=button_mappings, view_obj=view, activation_count=counter.count)
            function(interaction_obj)

    async def on_timeout():
        view.clear_items()


    view.on_timeout = on_timeout
    view.interaction_check = interaction_manager
    
    send_message(channel_id, content, view, _context_message)




def on_error(loop, context):
    global client
    log("System", "Error", "An uncaught error occurred within the asyncio loop. Please report this to the developer. Exception: " + str(context["exception"]) + ", Future Information: " + str(context["future"]), get_config("bot_folder"))
    #log("System", "Notice", "Attempting to restart " + str(context["future"]) + " coroutine.")
    #client.loop.create_task(context["future"].coro())

async def io_handler():
    global async_run_buffer
    global client
    while 1:
        try:
            keys = send_buffer.keys()
            for channel_ID in keys:
                channel_list = send_buffer[channel_ID]
                channel = client.get_channel(channel_ID)
                for ID_index in range(len(send_buffer[channel_ID])): 
                    if channel_list[0]["Type"] == "Plain":
                        if len(channel_list[0]["Content"]) > 2000:
                            separated = []
                            index = 1999
                            while 1:
                                if channel_list[0]["Content"][index] == "." or channel_list[0]["Content"][index] == "!" or channel_list[0]["Content"][index] == "?" or channel_list[0]["Content"][index] == " ":

                                    separated.append(channel_list[0]["Content"][:index+1])

                                    channel_list[0]["Content"] = channel_list[0]["Content"][index+1:].strip()
                                    if len(channel_list[0]["Content"]) > 2000:
                                        index = 1999
                                if index == 0:
                                    separated.append(channel_list[0]["Content"][:1999])
                                    channel_list[0]["Content"] = channel_list[0]["Content"][1999:]
                                    if len(channel_list[0]["Content"]) > 2000:
                                        index = 1999
                                if len(channel_list[0]["Content"]) <= 2000:
                                    separated.append(channel_list[0]["Content"])
                                    break
                                index -= 1


                            for message_index in range(len(separated)):
                                if channel_list[0]["View"] and message_index == len(separated) - 1:
                                    await channel.send(separated[message_index], view=channel_list[0]["View"])
                                else:
                                    await channel.send(separated[message_index])
                        else:
                            if not(send_buffer[channel_ID][0]["Content"].strip() == ""):
                                if channel_list[0]["View"]:
                                    await channel.send(send_buffer[channel_ID][0]["Content"], view=channel_list[0]["View"])
                                else:
                                    await channel.send(send_buffer[channel_ID][0]["Content"])
                    elif channel_list[0]["Type"] == "Special":
                        try:
                            if channel_list[0]["Context"]:
                                channel_list[0]["Content"]._set_message_object(await channel_list[0]["Content"]._send_message(message_context=channel_list[0]["Context"], view=channel_list[0]["View"]))
                            else:
                                channel_list[0]["Content"]._set_message_object(await channel_list[0]["Content"]._send_message(channel=channel, view=channel_list[0]["View"]))
                        except Exception as exc:
                            log("Bot", "Error", "An error occured while trying to send a special message object: " + str(exc) + ". This may be because of permissions, message size, or message content.", get_config("bot_folder"))


                    del send_buffer[channel_ID][0]




            

            await asyncio.sleep(0.1)
        except Exception as exc:
            log("Bot", "Error", "An error occured while trying to send a message: " + str(exc) + ". This may be because of permissions or message content.", get_config("bot_folder"))


async def on_ready():
    global bot_started
    bot_started = True
    log("Bot", "Notice", "Bot is connected and ready", get_config("bot_folder"))
    log("Bot", "Notice", "Running On Ready Event Extensions", get_config("bot_folder"))
    system_object = generate_system_object("EVENT:botready")
    bot_object = generate_bot_object(client)
    call_extensions("EVENT:botready", {"SYSTEM":system_object, "BOT":bot_object})
    log("Bot", "Notice", "On Ready Event Extension execution complete", get_config("bot_folder"))
    log("Bot", "Notice", "Preparing and starting interval extensions", get_config("bot_folder"))
    start_interval_extensions(get_config("bot_folder"))
    log("Bot", "Notice", "Interval extensions started", get_config("bot_folder"))



async def on_message(message):
    global active_inputs
    global fatal_state
    if client.user.id == message.author.id:
        return
    result = False
    prefix_check = check_for_prefix(message.content, get_config("callsign").strip().split("\n"))
    if prefix_check:
        result = parse_command(prefix_check)
        result[0][:] = [x for x in result[0] if x.strip() != ""]
        call_extensions("EVENT:prefix", {"SYSTEM":generate_system_object("EVENT:prefix"), "BOT":generate_bot_object(client), "MESSAGE":generate_message_object(client, message), "ARGS":generate_argument_object(result)})
    call_extensions("EVENT:message", {"SYSTEM":generate_system_object("EVENT:message"), "BOT":generate_bot_object(client), "MESSAGE":generate_message_object(client, message)})
    

    if message.channel.id in active_inputs.keys():
        inputs = active_inputs[message.channel.id]
        for input_index in range(len(inputs)):
            if (message.author.id in inputs[input_index]["Whitelisted ID"]) or (len(inputs[input_index]["Whitelisted ID"]) == 0):
                if inputs[input_index]["Timeout"] != 0:
                    if inputs[input_index]["Timeout"] < time.time() - inputs[input_index]["Start Time"]:
                        del inputs[input_index]
                        break
                if check_for_prefix(message.content, inputs[input_index]["Response Prefix"]):
                    interaction_object = generate_interaction_object(message, prefix_remove=inputs[input_index]["Response Prefix"])
                    relevant_input = inputs[input_index]
                    try:
                        inputs[input_index]["Result Function"](interaction_object)
                    except Exception as exc:
                        log("Bot", "Error", f"The following error occured while trying to respond to an input: {str(exc)}", get_config("bot_folder"))

                    if relevant_input in inputs:
                        del inputs[input_index]

                    return
                if len(inputs[input_index]["Response Prefix"]) == 0:
                    interaction_object = generate_interaction_object(message)
                    relevant_input = inputs[input_index]
                    try:
                        inputs[input_index]["Result Function"](interaction_object)
                    except Exception as exc:
                        log("Bot", "Error", f"The following error occured while trying to respond to an input: {str(exc)}", get_config("bot_folder"))

                    if relevant_input in inputs:
                        del inputs[input_index]

                    return

    if result:
        if result[2].strip() in get_config("command_blacklist").strip().split("\n"):
            if not(HasAuthority(message.author.id)):
                await message.channel.send("This command is currently unavailable.")
                log("Bot", "Command", f"User {str(message.author)} ({message.author.id}), in {str(message.channel)} ({message.channel.id}) - {str(message.guild)} ({message.guild.id}), ran the following command: {message.content}", get_config("bot_folder"))
                log("Bot", "Notice", f"User {str(message.author)} was declined authority to run " + result[2].strip() + " because the command is blacklisted", get_config("bot_folder"))
            else:
                if check_for_extension_header("COMMAND:" + result[2].lower().strip()):
                    log("Bot", "Command", f"User {str(message.author)} ({message.author.id}), in {str(message.channel)} ({message.channel.id}) - {str(message.guild)} ({message.guild.id}), ran the following command: {message.content}", get_config("bot_folder"))
                    call_extensions("COMMAND:" + result[2].lower().strip(), {"SYSTEM":generate_system_object("COMMAND:" + result[2].strip().lower()), "BOT":generate_bot_object(client), "MESSAGE":generate_message_object(client, message), "ARGS":generate_argument_object(result)})
                    call_extensions("EVENT:command", {"SYSTEM":generate_system_object("EVENT:command"), "BOT":generate_bot_object(client), "MESSAGE":generate_message_object(client, message), "ARGS":generate_argument_object(result)})

        elif check_for_extension_header("COMMAND:" + result[2].lower().strip()):
            log("Bot", "Command", f"User {str(message.author)} ({message.author.id}), in {str(message.channel)} ({message.channel.id}) - {str(message.guild)} ({message.guild.id}), ran the following command: {message.content}", get_config("bot_folder"))
            call_extensions("COMMAND:" + result[2].lower().strip(), {"SYSTEM":generate_system_object("COMMAND:" + result[2].strip().lower()), "BOT":generate_bot_object(client), "MESSAGE":generate_message_object(client, message), "ARGS":generate_argument_object(result)})
            call_extensions("EVENT:command", {"SYSTEM":generate_system_object("EVENT:command"), "BOT":generate_bot_object(client), "MESSAGE":generate_message_object(client, message), "ARGS":generate_argument_object(result)})
        ### BEGIN INTERNAL COMMANDS
        else:
            if result[2].strip() == 'reinit':
                if HasAuthority(message.author.id):
                    if len(result[0]) < 1:
                        bot_folder = get_config("bot_folder")

                    else:
                        bot_folder = result[0][0]
                    try:
                        ensure_folder(bot_folder)
                        patch.config_read(bot_folder + "/bot_log.log", "")
                        patch.append_to_file(bot_folder + "/bot_log.log", "\n\n\n--------------------\n")
                        log("System", "Notice", "System reinitializing from command", bot_folder)
                        if "keepauthority" in result[1]:
                            await message.channel.send("Retaining Authority for reinitialization...")
                        initialize(bot_folder, (True if "keepauthority" in result[1] else None))
                        if fatal_state:
                            log("System", "Error", "A fatal error occurred while reinitializing.", bot_folder)
                            await message.channel.send("A fatal error occured while trying to reinitialize, and the bot is shutting down, please check logs.")
                            return
                        await on_ready()
                        await message.channel.send("Sucessfully Reinitialized.")
                    except Exception as exc:
                        raise_fatal_error(exc, "The following fatal python error occurred while trying to reinitialize: " + str(exc), bot_folder)
                else:
                    await message.channel.send("You do not have the authority to access this command.")
                    log("Bot", "Notice", f"User {str(message.author)} was declined authority to run " + result[2].strip())

            if result[2].strip() == 'searchlog':
                if HasAuthority(message.author.id):
                    try:
                        opened = patch.openfile(get_config("bot_folder") + "/bot_log.log", "rb")
                        bot_log = opened.read().decode("utf-8")
                        opened.close()
                        bot_log = bot_log.replace("\n\n\n--------------------\n", "")
                        final_list = []
                        regex = ("regex" in result[1])
                        if regex:
                            await message.channel.send("Searching log with regex...")
                        else:
                            await message.channel.send("Searching log for strings...")
                        record_counter = 0
                        last_op = None
                        for line in bot_log.strip().split("\n"):
                            allow = False
                            for logic_op in result[1]:
                                if not(regex):
                                    logic_op = logic_op.lower()
                                if logic_op[:4].strip() == "has=":
                                    if regex:
                                        if len(re.findall(logic_op[4:], line)) != 0:
                                            allow = True
                                        else:
                                            allow = False
                                    else:
                                        if logic_op[4:].lower() in line.lower():
                                            allow = True
                                        else:
                                            allow = False
                                if logic_op[:4].strip() == "and=":
                                    if regex:
                                        if len(re.findall(logic_op[4:], line)) != 0:
                                            allow = True
                                        else:
                                            allow = False
                                    else:
                                        if logic_op[4:].lower() in line.lower():
                                            allow = True
                                        else:
                                            allow = False
                                    last_op = "and"
                                if logic_op[:4].strip() == "not=":
                                    if regex:
                                        if len(re.findall(logic_op[4:], line)) != 0:
                                            allow = False
                                    else:
                                        if logic_op[4:].lower() in line.lower():
                                            allow = False
                                    last_op = "not"

                            if allow:
                                record_counter += 1
                                final_list.append(line)
                        final_string = f"---There were {record_counter} log(s) found with these parameters---"
                        for line in final_list:
                            final_string += "\n-------------------------\n"
                            final_string += line.replace("<@!", "<Pinged User - ").replace("@everyone", "<Pinged Everyone>").replace("@here", "<Pinged Here>")
                        final_string += "\n-------------------------"


                        send_message(message.channel.id, final_string)
                    except Exception as exc:
                        await message.channel.send("An error occured when trying to execute this command.")
                        log("Bot", "Error", "An error occured when searching the log file: " + str(exc), get_config("bot_folder"))


                else:
                    await message.channel.send("You do not have the authority to access this command.")

            if result[2].strip() == 'shutdown':
                if HasAuthority(message.author.id):
                    await message.channel.send("Shutting down...")
                    log("Bot", "Notice", f"Bot Shutdown Issued from command by {str(message.author)}", get_config("bot_folder"))
                    await stop_bot("Stopped from command")
                   
                else:
                    await message.channel.send("You do not have the authority to access this command.")
                    log("Bot", "Notice", f"User {str(message.author)} was declined authority to run " + result[2].strip())


def generate_subargument_object(string):
    result = parse_command(str(string))
    result[0][:] = [x for x in result[0] if x.strip() != ""]

    return generate_argument_object(result)

def generate_system_object(extension_header, extension_bot_object=None): #generates an object to be passed to extensions
    class SYSTEM:
        pass
    obj = SYSTEM()
    obj.GetConfig = get_config #Returns values of configuration based on given key
    obj.SetConfig = set_config #sets a value of the configuration based on given key
    obj.GeneralStore = general_store #Stores values as files based on given varname
    obj.GeneralRead = general_read #Reads stored values based on varname
    obj.ExtensionShareSet = extension_share_add #Adds a value to the extensions share based on key
    obj.ExtensionShareAdd = extension_share_add
    obj.ExtensionShareGet = extension_share_get #Gets a value from the extension share based on key
    obj.LogError = lambda value: log(f"Extensions:{extension_header}", "Error", value, get_config("bot_folder")) #Logs an error based on content
    obj.LogNotice = lambda value: log(f"Extensions:{extension_header}", "Notice", value, get_config("bot_folder")) #Logs a notice based on content
    obj.CheckForPrefix = check_for_prefix #Check for a prefix in the second parameter, return false if none, return clipped string if it exists
    obj.CallExtensions = call_extensions #Call extensions given a header
    obj.Print = patch.print
    obj.Input = patch.input
    obj.Open = patch.openfile
    obj.EnsureFolder = ensure_folder
    obj.ListDirectory = patch.listdir
    obj.MakeDirectory = patch.mkdir
    obj.RemoveDirectory = patch.rmtree
    obj.IsFile = patch.isfile
    obj.IsDirectory = patch.isdir
    obj.WriteFile = patch.write_file
    obj.ReadFile = patch.read_file
    obj.AppendToFile = patch.append_to_file
    def _temp(coro):
        def _temp2(function):
            async_run_buffer.append([coro, function])
        return _temp2
    obj.RunAsyncFunction = _temp
    obj.BotFolder = get_config("bot_folder")

    obj.Globals = globals()
    obj.Version = VERSION
    obj.CommandInterpreterName = COMMAND_INTERPRETER
    obj.ApiWrapperName = API_WRAPPER
    return obj

    #passthrough patch things
    #"extension passthrough"




def generate_bot_object(client): #generates an object to be passed to extensions
    class BOT:
        pass
    obj = BOT()
    obj.SetStatus = lambda content, type=1:client.loop.create_task(set_status(content, type))
    obj.HasAuthority = HasAuthority # Checks if a user has authority
    obj.UserStore = user_store # Stores data of a user given an ID
    obj.UserRead = user_read # reads stored data of a user
    obj.ChannelStore = channel_store 
    obj.ChannelRead = channel_read
    obj.GuildStore = guild_store
    obj.GuildRead = guild_read
    obj.SendMessage = send_message
    obj.DirectSendMessage = direct_send_message
    obj.SpecialMessage = special_message
    obj.HasBotPrefix = lambda string: check_for_prefix(string, get_config("callsign").strip().split("\n"))
    def _temp(channel_id, content, whitelisted_ids=[], response_prefixes=["!"], timeout=0):
        return lambda function: get_input(function, channel_id, content, whitelisted_ids, response_prefixes, timeout)
    obj.GetInput = _temp

    def _temp(channel_id, content, button_options, whitelisted_ids=[], timeout=180):
        return lambda function: get_button_input(function, channel_id, content, button_options, whitelisted_ids, timeout=timeout)
    obj.GetButtonInput =  _temp

    obj.ClientObject = client

    return obj

def generate_message_object(client, message): #Generates an object to be passed to extensions
    class MESSAGE:
        pass
    obj = MESSAGE()
    obj.MessageObject = message # The direct discord.py message object
    obj.SendMessage = lambda send: send_message(message.channel.id, send, _context_message=message) #Send a message in the relevant channel
    obj.DirectSendMessage = lambda *args, **kwargs: direct_send_message(message.channel.id, *args, **kwargs)
    obj.HasBotPrefix = lambda: check_for_prefix(message.content, get_config("callsign").strip().split("\n"))
    def _temp(content, whitelisted_ids=[message.author.id], timeout=0):
        return lambda function: get_input(function, message.channel.id, content, whitelisted_ids, timeout=0, _context_message=message)
    obj.GetInput =  _temp

    def _temp(content, button_options, whitelisted_ids=[message.author.id], timeout=180):
        return lambda function: get_button_input(function, message.channel.id, content, button_options, whitelisted_ids, timeout=timeout, _context_message=message)
    obj.GetButtonInput =  _temp
    obj.Content = message.content
    obj.GuildStore = lambda varname, content: guild_store(message.guild.id, varname, content)
    obj.GuildRead = lambda varname: guild_read(message.guild.id, varname)
    obj.ChannelStore = lambda varname, content: channel_store(message.channel.id, varname, content)
    obj.ChannelRead = lambda varname: channel_read(message.channel.id, varname)
    obj.UserStore = lambda varname, content: user_store(message.author.id, varname, content)
    obj.UserRead = lambda varname: user_read(message.author.id, varname)
    obj.HasAuthority = lambda: HasAuthority(message.author.id)
    obj.AuthorID = message.author.id 
    obj.ChannelID = message.channel.id 
    obj.GuildID = message.guild.id
    obj.AuthorName = str(message.author)
    obj.ChannelName = str(message.channel)
    obj.GuildName = str(message.guild)
    obj.IsNSFW = message.channel.nsfw
    obj.IsBot = message.author.bot

    return obj

def generate_argument_object(args):
    class ARGS:
        pass
    obj = ARGS()
    obj.Arguments = args[0]
    obj.Options = args[1]
    obj.Command = args[2]
    obj.CommandRemoved = args[3]
    obj.SimpleArguments = args[4]
    obj.SimpleCommand = args[5]
    obj.SimpleCommandRemoved = args[6]
    obj._sub_commands = []


    def _temp(command):
        obj._sub_commands.append(str(command).strip().lower())
        def _temp2(function):

            prefix_check = check_for_prefix(args[3].strip().lower(), [str(command).strip().lower()])

            if prefix_check or prefix_check == "":

                function(generate_subargument_object(args[3].strip()))

        return _temp2
    obj.SubCommand = _temp

    def _temp():
        def _temp2(function):
            if not(obj.CommandRemoved.strip() == "") and not(check_for_prefix(args[3].strip().lower(), obj._sub_commands) != None):
                function(generate_subargument_object(args[3].strip()))
        return _temp2


    obj.UnknownSubCommand = _temp


    def _temp():
        def _temp2(function):
            if obj.CommandRemoved.strip() == "":
                function()
        return _temp2

    obj.NoSubCommand = _temp

    return obj

def generate_interaction_object(message_obj=None, interaction_obj=None, button_mappings=None, prefix_remove=None, view_obj=None, activation_count=None):
    global client
    class interaction:
        pass
    obj = interaction()
    obj.Content = None
    obj.UserResponseID = None
    obj.MessageObject = None
    obj.InteractionObject = None
    obj.ButtonInteger = None
    obj.CompleteInteraction = None
    obj.SetOriginalMessage = None
    obj.InteractionAmount = None

    if message_obj:
        obj.Content = message_obj.content 
        obj.UserResponseID = message_obj.author.id  
        obj.MessageObject = message_obj
        if prefix_remove:
            obj.Content = check_for_prefix(message_obj.content, [prefix_remove])

    if interaction_obj:
        obj.Content = button_mappings[interaction_obj.data["custom_id"]]
        obj.UserResponseID = interaction_obj.user.id 
        obj.InteractionObject = interaction_obj
        obj.ButtonInteger = int(interaction_obj.data["custom_id"])
        obj.InteractionAmount = activation_count
        def _temp(content):
            if type(content) == type(special_message()):
                client.loop.create_task(interaction_obj.message.edit(embed=content))
            else:
                client.loop.create_task(interaction_obj.message.edit(content=content))

        obj.SetOriginalMessage = _temp
        def _temp():
            view_obj.clear_items()
            view_obj.stop()
            client.loop.create_task(interaction_obj.message.edit(view=view_obj))

            
        obj.StopInteraction = _temp

        def _temp():
            client.loop.create_task(interaction_obj.response.defer())
        obj.DeferInteraction = _temp

    return obj

class special_message:
    def __init__(self):
        self.is_reply = False
        self.is_hidden = False
        self.is_embed = False

        self.fields = []
        self.title = None
        self.content = None
        self.thumbnail = None
        self.image = None
        self.url = None
        self.color = None
        self.footer = None
        self._message_object = None

        self._total_char_count = 0
        self._field_count = 0

    def SetReply(self):
        self.is_reply = True
        return self

    def DisableReply(self):
        self.is_reply = False
        return self

    def SetHidden(self):
        self.is_hidden = True
        return self

    def DisableHidden(self):
        self.is_hidden = False
        return self

    def SetEmbed(self):
        self.is_embed = True
        return self

    def DisableEmbed(self):
        self.is_embed = False
        return self

    def AddField(self, name, value, inline=True):
        self.fields.append([name, value, inline])
        return self

    def EditField(self, fieldindex, name, value, inline=True):
        self.fields[fieldindex] = [name, value, inline]
        return self

    def RemoveField(self, fieldindex):
        del self.fields[fieldindex]
        return self

    def ClearFields(self):
        self.fields = []
        return self

    def SetTitle(self, title):
        self.title = str(title)
        return self

    def SetContent(self, content):
        self.content = str(content)
        return self

    def SetThumbnail(self, thumbnail):
        self.thumbnail = str(thumbnail)
        return self

    def SetImage(self, image):
        self.image = str(image)
        return self

    def SetURL(self, url):
        self.url = str(url)
        return self

    def SetColor(self, r, g, b):
        self.color = discord.Colour.from_rgb(r, g, b)
        return self

    def SetFooter(self, content, icon_url=None):
        self.footer = (content, icon_url)
        return self

    def _set_message_object(self, message_obj):
        self._message_object = message_obj
    
    def _render_message(self): #(type, content (embed or whatnot))
        kwargs = {}
        if self.is_embed:
            if self.color:
                kwargs['colour'] = self.color
            if self.title:
                kwargs['title'] = self.title
            if self.url:
                kwargs['url'] = self.url
            if self.content:
                kwargs['description'] = self.content

            embed = discord.Embed(**kwargs)
            for field in self.fields:
                embed.add_field(name=field[0], value=field[1], inline=field[2])
            if self.image:
                embed.set_image(url=self.image)
            if self.thumbnail:
                embed.set_thumbnail(url=self.thumbnail)
            if self.footer:
                if self.footer[1]:
                    embed.set_footer(text=self.footer[0], icon_url=self.footer[1])
                else:
                    embed.set_footer(text=self.footer[0])
            return "embed", embed
        else:
            final = ""
            if self.title:
                final += "**" + self.title + "**\n"
            if self.content:
                final += str(self.content)
            return "text", final


            

    def _send_message(self, channel=None, message_context=None, view=None):
        messagetype, message = self._render_message()
        if message_context:
            if self.is_reply:
                if messagetype == "embed":
                   return message_context.reply(embed=message, view=view)
                if messagetype == "text":
                    return message_context.reply(message, view=view)
            else:
                if messagetype == "embed":
                    return message_context.channel.send(embed=message, view=view)
                if messagetype == "text":
                    return message_context.channel.send(message, view=view)
        elif channel:
            if messagetype == "embed":
                return channel.send(embed=message, view=view)
            if messagetype == "text":
                return channel.send(message, view=view)


        
        

    def EditOriginal(self): #Unfinished
        global client
        if not(self._message_object):
            raise RuntimeError("Message hasn't yet been sent.")
        else:
            messagetype, message = self._render_message()
            if messagetype == "embed":
                client.loop.create_task(self._message_object.edit(embed=message))
            if messagetype == "text":
                client.loop.create_task(self._message_object.edit(message))


def main(bot_folder): #Called by main check, but also can be called through import. The bot_folder can be changed accordingly
    try:

        ensure_folder(bot_folder)
        try:
            patch.config_read(bot_folder + "/bot_log.log", "")
        except UnicodeDecodeError:
            patch.print("Error when ensuring bot log, please resolve UnicodeDecodeError.")
        patch.append_to_file(bot_folder + "/bot_log.log", "\n\n\n--------------------\n")
        log("System", "Startup", "System started from main", bot_folder)
        initialize(bot_folder)
    except Exception as exc:
        raise_fatal_error(exc, "The following fatal python error occurred while trying to initialize: " + str(exc), bot_folder)

if __name__ == "__main__": #Runs needed startup functions for the bot, assuming the script is run directly, and not from an import
    bot_name = None
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hf:w:",["folder=", "workingdirectory="])
    except getopt.GetoptError:
        patch.print("Usage: -f <botfolder> -w <workingdirectory>")
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            patch.print('Usage: -f <botfolder> -w <workingdirectory>')
            sys.exit()
        elif opt in ("-f", "--folder"):
            bot_name = arg
        elif opt in ("-w", "--workingdirectory"):
            working_directory = arg

    if not(bot_name):
        bot_folder = working_directory + "/" + input("Please enter your Bot's folder name\n> ")
    else:
        bot_folder = working_directory + "/" + bot_name
    main(bot_folder)


'''
                        mappings = {
                        'ConsolePrint':self.ConsolePrint, 
                        'CALLER_ID':self.caller_id,
                        'CHANNEL_ID':self.channel_id,
                        'GUILD_ID':self.guild_id, 
                        'HasAuthority':HasAuthority, 
                        'UserExists': self.UserExists,
                        'UserStore':self.UserStore,
                        'UserRead':self.UserRead, 
                        'ChannelStore':self.ChannelStore,
                        'ChannelRead':self.ChannelRead,
                        'GuildStore':self.GuildStore,
                        'GuildRead':self.GuildRead,
                        'ExtractID':self.ExtractID,
                        'GetConfigParameter':self.GetConfigParameter,
                        'EasyEmbed':self.EasyEmbed,
                        'REF_CALLER':'<@!' + str(self.caller_id) + '>', 
                        'REFERENCE_CALLER':'<@!' + str(self.caller_id) + '>',
                        'CALLER':self.caller, 
                        'GUILD':str(self.guild), 
                        'CHANNEL':self.channel,
                        'RAW_MESSAGE':take_in,
                        'VERSION':version,
                        'BOT_CLIENT':client,
                        'ARGS':passto.strip().split(),
                        'print':self.print, 
                        'input':self.input, 
                        'argv':['python3'] + passto.strip().split(), 
                        'sys.argv':['python3'] + passto.strip().split()}
'''