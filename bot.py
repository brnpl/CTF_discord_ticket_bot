# Author: brn

import discord
from discord import Permissions
import os
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

###############CONFIG###############
EMOJIS = ['🔑', '🥅', '📟', '👾', '🔫', '❓', '🍌'] # crypto, network, web, reverse, pwn, osint, hardware
DELETE_EMOJI = '⛔'
MAP_EMOJIS_CATEGORY = {'🔑': 'crypto', '🥅': 'network', '📟': 'web', '👾': 'reverse', '🔫': 'pwn', '❓': 'osint', '🍌': 'hardware', '⛔': "delete"}

TICKET_CATEGORY_NAME = 'Support'
# channel to send the message
TICKET_CHANNEL = "support"
# channel to send the ticket logs
LOG_CHANNEL = "log_channel"

SUPPORT_MESSAGE = """Welcome to the support channel!\n
React with the emoji in order to create a ticket:
Crypto-> 🔑;
Network-> 🥅;
Web -> 📟;
Reverse -> 👾;
Pwn -> 🔫;
Osint -> ❓;
Hardware -> 🍌;"""
TICKET_MESSAGE = f""", a team member will soon reply to you.

Message template:
Challenge: CHALLENGE_NAME
Question: QUESTION

Click on {DELETE_EMOJI} to close the ticket!"""
###############END CONFIG###############


@client.event
async def on_ready():
    """It sends the support message to the selected channel."""

    print('Bot is ready.')

    # create support category and channel
    guild = client.guilds[0]
    category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if not category:
        category = await guild.create_category_channel(TICKET_CATEGORY_NAME)
    channel = discord.utils.get(guild.channels, name=TICKET_CHANNEL)
    if not channel:
        overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await category.create_text_channel(TICKET_CHANNEL, overwrites=overwrites)   

    # clear the history
    await channel.purge()

    message = await channel.send(SUPPORT_MESSAGE)

    # add the emojis to the message
    for emoji in EMOJIS:
        await message.add_reaction(emoji)


@client.event
async def on_reaction_add(reaction, user):
    """Depending on the selected emoji, it will create the private channel or it will delete it."""
    emoji = reaction.emoji

    # if the emoji is not in the selected ones
    if emoji not in MAP_EMOJIS_CATEGORY:
        return
    
    category = MAP_EMOJIS_CATEGORY[emoji]

    # avoid recursive messages
    if user.id == client.user.id:
        return
    
    guild = reaction.message.guild
    
    ticket_category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if not ticket_category:
        ticket_category = await guild.create_category(TICKET_CATEGORY_NAME)

    # if the reaction belongs to the EMOJIS (it's not the delete emoji)
    if str(reaction.emoji) in EMOJIS and reaction.message.content == SUPPORT_MESSAGE:

        # create the new channel with the right permissions (category+admin)
        category_permission = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True),
            # the category corresponds with a role. for a "web" ticket, a new channel is created with "admins", "web" role and person who created it.
            discord.utils.get(guild.roles, name=category): discord.PermissionOverwrite(read_messages=True)
        }

        # creating the channel and sending the initial message
        channel = await guild.create_text_channel(f'{category}-{user.display_name}', overwrites=category_permission, category=ticket_category)
        message = await channel.send(f"{user.name}"+TICKET_MESSAGE)
        await message.add_reaction(DELETE_EMOJI)
    
    # if the emoji is the delete one    
    elif str(reaction.emoji) == DELETE_EMOJI and reaction.message.channel.category and reaction.message.channel.category.name == TICKET_CATEGORY_NAME and reaction.message.author == client.user:
        channel = reaction.message.channel
        await channel.send(f'The ticket has been closed by {user.name}. Sending the ticket log to the admins...')
        
        # create log_channel inside the support category
        guild = client.guilds[0]
        category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if not category:
            category = await guild.create_category_channel(TICKET_CATEGORY_NAME)
        log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL)
        if not log_channel:
            admin_permission = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            log_channel = await guild.create_text_channel(LOG_CHANNEL, overwrites=admin_permission, category=ticket_category)
        

        # get the ticket history
        messages = []
        async for message in channel.history(limit=None):
            messages.insert(0, message)
        # removing the ticket initial message
        messages = messages[1:]
        # collect the log in a string
        log_content = f'Ticket log {channel.name}:\n\n'
        for message in messages:
            log_content += f'{message.author}: {message.content}\n'

        # write the log in a specific file and send it
        with open(f'temp_log.txt', 'w') as f:
            f.write(log_content)
        file_path = './temp_log.txt'
        file = discord.File(file_path)
        await log_channel.send(file=file)
        
        await channel.delete()

client.run(TOKEN)