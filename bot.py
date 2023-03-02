# Author: brn

import discord
import os
from dotenv import load_dotenv
import re

#######################################  BEGIN CONFIG  #######################################
# select the emoji for the challenge category and for closing the ticket
MAP_EMOJIS_CATEGORY = {'🔑': 'crypto', '🥅': 'network', '📟': 'web', '👾': 'reverse', '🔫': 'pwn', '❓': 'osint', '🍌': 'hardware', '⛔': "delete"}
OPEN_TICKET_EMOJIS = list(MAP_EMOJIS_CATEGORY.keys())[:-1]
CLOSE_TICKET_EMOJI = list(MAP_EMOJIS_CATEGORY.keys())[-1]

# select the category in which the support message and the logs will be sent
TICKET_CATEGORY_NAME = 'Support Tickets'
TICKET_CHANNEL = "support"
LOG_CHANNEL = "log_channel"

# configure the bot messages
MESSAGE_SUPPORT_CHANNEL = """Welcome to the support channel!\n
React with the emoji in order to create a ticket:
Crypto-> 🔑;
Network-> 🥅;
Web -> 📟;
Reverse -> 👾;
Pwn -> 🔫;
Osint -> ❓;
Hardware -> 🍌;"""
MESSAGE_TICKET_OPEN = f""", a team member will soon reply to you.

Message template:
Challenge: CHALLENGE_NAME
Question: QUESTION

Click on {CLOSE_TICKET_EMOJI} to close the ticket!"""

MESSAGE_TICKET_CLOSE = 'The ticket has been closed. Sending the ticket log to the admins...'
MESSAGE_TICKET_SEND_LOG = 'Here is the log of your ticket:'
#######################################  END CONFIG  #######################################

#######################################  BEGIN FUNCTIONS  #######################################
def create_ticket_log(messages, channel):

    log_file = 'temp_log.txt'

    # removing the ticket introduction message, useless
    messages = messages[1:]
    
    # crafting the log message
    log = f'Ticket log {channel.name}:\n\n'
    for message in messages:
        log += f'{message.author}: {message.content}\n'

    # writing the log in a specific file and parsing it for discord use
    with open(log_file, 'w') as f:
        f.write(log)

    return './' + log_file


def get_ticket_owner(messages):

    pattern = r'<([^>]+)>'
    ticket_owner_id = int(re.findall(pattern, messages[0].content)[0][1:])
    ticket_owner = client.get_user(ticket_owner_id)

    return ticket_owner
#######################################  END FUNCTIONS  #######################################

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")


@client.event
async def on_ready():
    """It sends the support message to the selected channel and adds the emojis."""

    print('Bot is ready.')

    # create support category and channel if they do not already exist
    guild = client.guilds[0]
    category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if not category:
        category = await guild.create_category_channel(TICKET_CATEGORY_NAME)
    channel = discord.utils.get(guild.channels, name=TICKET_CHANNEL)
    if not channel:
        ticket_channel_permissions = { # everyone: read permission, bot: read and write permissions
        guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await category.create_text_channel(TICKET_CHANNEL, overwrites=ticket_channel_permissions)   

    # clear the history
    await channel.purge()

    message = await channel.send(MESSAGE_SUPPORT_CHANNEL)

    # add the emojis to the message
    for emoji in OPEN_TICKET_EMOJIS:
        await message.add_reaction(emoji)


@client.event
async def on_reaction_add(reaction, user):
    """It reacts differently based on the raised emoji:
    - if the emoji does not belong to any allowed categories, do nothing;
    - if the emoji belongs to the OPEN_TICKET_EMOJIS it creates the ticket accordingly;
    - if the emoji belogs to the CLOSE_TICKET_EMOJI it closes the ticket and sends the log to the ticket owner;"""
    
    emoji = reaction.emoji

    # if the emoji is not in the selected ones
    if emoji not in MAP_EMOJIS_CATEGORY:
        return
    
    # get category based on the raised emoji. Be sure that exists a role in the server with the same name
    category = MAP_EMOJIS_CATEGORY[emoji]

    # avoid recursive messages from the bot
    if user.id == client.user.id:
        return
    

    guild = reaction.message.guild
    private_ticket_category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)

    ########## Case 1: the emoji belongs to the OPEN_TICKET_EMOJIS
    if str(reaction.emoji) in OPEN_TICKET_EMOJIS and reaction.message.content == MESSAGE_SUPPORT_CHANNEL:

        # create the new channel with the right permissions (role+admin)
        private_ticket_permissions = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True),
            discord.utils.get(guild.roles, name=category): discord.PermissionOverwrite(read_messages=True)
        }
        channel = await guild.create_text_channel(f'{category}-{user.display_name}', overwrites=private_ticket_permissions, category=private_ticket_category)
        message = await channel.send(f"{user.mention}"+MESSAGE_TICKET_OPEN)
        await message.add_reaction(CLOSE_TICKET_EMOJI)
    
    ########## Case 2: the emoji belongs to the CLOSE_TICKET_EMOJI   
    elif str(reaction.emoji) == CLOSE_TICKET_EMOJI and reaction.message.channel.category and reaction.message.channel.category.name == TICKET_CATEGORY_NAME and reaction.message.author == client.user:
        
        channel = reaction.message.channel
        await channel.send(MESSAGE_TICKET_CLOSE)
        
        # create the channel that will receive the log
        guild = client.guilds[0]
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL)
        if not log_channel:
            admin_permissions = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            log_channel = await guild.create_text_channel(LOG_CHANNEL, overwrites=admin_permissions, category=ticket_category)
        

        # get the ticket history
        messages = []
        async for message in channel.history(limit=None):
            messages.insert(0, message)
        
        # get the ticket owner and the path of the log file
        ticket_owner = get_ticket_owner(messages)
        log_path = create_ticket_log(messages, channel)

        # send the log file to the log channel
        discord_ticket_log = discord.File(log_path)
        await log_channel.send(file=discord_ticket_log)
        
        # send the log to the ticket owner
        dm_channel = await ticket_owner.create_dm()
        discord_ticket_log = discord.File(log_path)
        await dm_channel.send(MESSAGE_TICKET_SEND_LOG, file=discord_ticket_log)
        
        await channel.delete()

client.run(TOKEN)