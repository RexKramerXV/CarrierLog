#!/usr/bin/env python
"""Plugin to put your Carrier crew to work"""
import platform
import os
import sys
import tkinter as tk
import requests
import json


import myNotebook as nb

from typing import Optional, Tuple, Dict

from config import config

from EDMCLogging import get_main_logger
logger = get_main_logger()


TARGET_URL='http://localhost:5020'

class PluginConfig:
    """Holds globals for status and handling."""

    def __init__(self):
        self.shutting_down = False      # Plugin is shutting down.

        #
        # REST API related settings
        #

        self.session: requests.Session = requests.Session()

        #
        # Discord related properties
        #

        self.discord_guild: str = ''         # Discord Guild name
        self.discord_channel_name: str = ''  # Discord Channel name
        self.discord_webhookurl: str = ''    # Discord Webhook URL
        self.discord_bot_token: str = ''     # Discord bot token
        self.discord_prefix: str = '/'       # Discord bot prefix
        self.discord_description: str = 'Carrier Commander Discord Bot'  # name of bot

        #
        # config related properties
        #

        self.guild_textvar = tk.StringVar()
        self.channel_textvar = tk.StringVar()
        self.webhookurl_textvar = tk.StringVar()
        self.bot_token_textvar = tk.StringVar()
        self.discord_prefix_textvar = tk.StringVar()

        # the message about Carrier Status in EDMC
        self.carrier_status_msg = Optional[tk.Label]

        #
        # Discord process related properties
        #

        self.queue: Queue = Queue()
        self.loop: asyncio.AbstractEventLoop = None
        self.discord_thread: Thread = None

        logger.debug("PluginConfig initialized.")


plugin = PluginConfig()


class FileHandler():
    def __init__(self) -> None:
        logger.debug(f'Initializing class "FileHandler"')

        # path to E:D journals and status files (and where we store our systems)
        if platform.system() == 'Windows':
            from os import getenv
            self.path = getenv(
                'USERPROFILE') + "/Saved Games/Frontier Developments/Elite Dangerous/"
        else:
            self.path = "./"

        logger.debug(f'Set path to logs and our file storage to {self.path=}')

        # files to store text strings in for further (including potential external) use

        # current system name
        self.system_name_file = 'system_name.txt'

        # plotted system name (empty if no jump plotted)
        self.plotted_name_file = 'plotted_system.txt'

        # trigger string when from Comms when entering a new system comms channel
        self.entered_system_msg = '$COMMS_entered:#name='

        # Name of E:D status file
        self.status_file = 'Status.json'

        self.current_system_file = self.path + self.system_name_file
        self.plotted_system_file = self.path + self.plotted_name_file
        self.files = [self.current_system_file, self.plotted_system_file]

        logger.debug(f'Class "FileHandler" initialized')


fh = FileHandler()


class CommunityGoal():
    def __init__(self) -> None:
        # storage for the Community Goal dict
        self.CommunityGoal: dict = {}

        # Target for Community Goal ('Contributions' on Inara)
        # this can be either hard-coded, or
        # TODO: be put into the plugin configuration screen or
        # IDEA: be auto-fetched from the Inara website
        self.COMMUNITY_GOAL_LIMIT = 0


cg = CommunityGoal()


def plugin_start3(plugin_dir: str) -> str:
    """
    Plugin startup method.

    :param plugin_dir:
    :return: 'Pretty' name of this plugin.
    """

    plugin_name = os.path.basename(os.path.dirname(__file__))
    logger.info(f'CarrierCommander folder is {plugin_dir}')
    logger.info(f'CarrierCommander plugin name is {plugin_name}')

    # read the presets from config (if available)
    plugin.discord_guild = config.get_str(
        'carriercommander_discord_guild', default='')
    logger.debug(
        f'Loaded value: {plugin.discord_guild=} ({type(plugin.discord_guild)})')

    plugin.discord_channel = config.get_str(
        'carriercommander_discord_channel', default='')
    logger.debug(
        f'Loaded value: {plugin.discord_channel=} ({type(plugin.discord_channel)})')

    plugin.discord_webhookurl = config.get_str(
        'carriercommander_discord_webhookurl', default='')
    logger.debug(
        f'Loaded value: {plugin.discord_webhookurl=} ({type(plugin.discord_webhookurl)})')

    plugin.discord_bot_token = config.get_str(
        'carriercommander_discord_bot_token', default='')
    logger.debug(
        f'Loaded value: {plugin.discord_bot_token=} ({type(plugin.discord_bot_token)})')

    # set the text variables correspondingly

    plugin.guild_textvar.set(value=plugin.discord_guild)
    plugin.channel_textvar.set(value=plugin.discord_channel)
    plugin.bot_token_textvar.set(value=plugin.discord_bot_token)
    plugin.webhookurl_textvar.set(value=plugin.discord_webhookurl)

    return plugin_name


def plugin_stop() -> None:
    """
    Plugin stop method.

    :return:
    """
    logger.info(f'Stopping plugin')
    plugin.shutting_down = True
    set_status("No link to Carrier.", "grey")
    logger.debug('CarrierCommander plugin - stopped successfully.')
    return 0


def plugin_app(parent: tk.Frame) -> Tuple[tk.Label, tk.Label, tk.Label, tk.Label, tk.Label, tk.Label]:
    """
    Create a pair of TK widgets for the EDMarketConnector main window
    """
    # get current gridsize
    row = parent.grid_size()[1]
    #row += 2
    tk.Frame(parent, highlightthickness=1).grid(
        columnspan=2, sticky=tk.EW)  # separator

    # By default widgets inherit the current theme's colors
    label_carrier = tk.Label(parent, text="Carrier:")
    label_carrier.grid(row=row+2, column=0, sticky=tk.W)

    plugin.carrier_status_msg = tk.Label(parent, text="Initialising...",
                                         foreground="green")  # Override theme's foreground color
    plugin.carrier_status_msg.grid(row=row+2, column=1, sticky=tk.W)

    label_targetsystem = tk.Label(parent, text="Target Sys:")
    label_targetsystem.grid(row=row+3, column=0, sticky=tk.W)

    status_targetsystem = tk.Label(parent, text="-")
    status_targetsystem.grid(row=row+3, column=1, sticky=tk.W)

    label_depotlevel = tk.Label(parent, text="Depot:")
    label_depotlevel.grid(row=row+4, column=0, sticky=tk.W)

    status_depotlevel = tk.Label(parent, text="-")
    status_depotlevel.grid(row=row+4, column=1, sticky=tk.W)

    return plugin.carrier_status_msg

# later on your event functions can update the contents of these widgets


def plugin_prefs(parent: nb.Notebook, cmdr: str, is_beta: bool) -> Optional[tk.Frame]:
    """
    Return a TK Frame for adding to the EDMarketConnector settings dialog.
    """

    PADX = 10
    PADY = 5

    conf_frame = nb.Frame(parent)
    conf_frame.columnconfigure(index=1, weight=1)

    cur_row = 1

    nb.Label(conf_frame, text=_(
        "Provide Discord's guild, channel and WebHook URL for communication, plus a bot token from Discord's developer portal."
    )).grid(sticky=tk.EW, row=cur_row, column=0, columnspan=4)

    cur_row += 2

    # Label for Discord Guild
    nb.Label(conf_frame, text=_('Discord Guild')).grid(
        sticky=tk.W, row=cur_row, column=0, padx=PADX, pady=PADY)
    nb.Entry(conf_frame, textvariable=plugin.guild_textvar).grid(
        sticky=tk.EW, row=cur_row, column=1, padx=PADX, pady=PADY)

    cur_row += 2

    # Label for Discord Channel
    nb.Label(conf_frame, text=_('Discord Channel')).grid(
        sticky=tk.W, row=cur_row, column=0, padx=PADX, pady=PADY)
    nb.Entry(conf_frame, textvariable=plugin.channel_textvar).grid(
        sticky=tk.EW, row=cur_row, column=1, padx=PADX, pady=PADY)

    cur_row += 2

    # Label for Discord Channel
    nb.Label(conf_frame, text=_('Discord Webhook URL')).grid(
        sticky=tk.W, row=cur_row, column=0, padx=PADX, pady=PADY)
    nb.Entry(conf_frame, textvariable=plugin.webhookurl_textvar).grid(
        sticky=tk.EW, row=cur_row, column=1, padx=PADX, pady=PADY)

    cur_row += 2

    # Label for Discord Bot Token
    nb.Label(conf_frame, text=_('Discord Bot Token')).grid(
        sticky=tk.W, row=cur_row, column=0, padx=PADX, pady=PADY)
    nb.Entry(conf_frame, textvariable=plugin.bot_token_textvar).grid(
        sticky=tk.EW, row=cur_row, column=1, padx=PADX, pady=PADY)

    return conf_frame


def prefs_changed(cmdr: str, is_beta: bool) -> None:
    """
    Save settings.
    """

    plugin.discord_guild = plugin.guild_textvar.get()
    plugin.discord_channel = plugin.channel_textvar.get()
    plugin.discord_bot_token = plugin.bot_token_textvar.get()
    plugin.discord_webhookurl = plugin.webhookurl_textvar.get()

    # Store new value in config
    config.set('carriercommander_discord_guild', plugin.discord_guild)
    logger.trace(
        f'Stored value: {plugin.discord_guild=} ({type(plugin.discord_guild)})')

    config.set('carriercommander_discord_channel', plugin.discord_channel)
    logger.trace(
        f'Stored value: {plugin.discord_channel=} ({type(plugin.discord_channel)})')

    config.set('carriercommander_discord_webhookurl',
               plugin.discord_webhookurl)
    logger.trace(
        f'Stored value: {plugin.discord_webhookurl=} ({type(plugin.discord_webhookurl)})')

    config.set('carriercommander_discord_bot_token', plugin.discord_bot_token)
    logger.trace(
        f'Stored value: {plugin.discord_bot_token=} ({type(plugin.discord_bot_token)})')


def journal_entry(cmdrname: str, is_beta: bool, system: str, station: str, entry: dict, state: dict) -> None:
    """
    Handle the given journal entry.

    :param cmdrname: Current commander name
    :param is_beta: Is the game currently in beta
    :param system: Current system, if known
    :param station: Current station, if any
    :param entry: The journal event - this is what we are mainly looking for
    :param state: More info about the commander, their ship, and their cargo
    :return: None
    """

    # print it out to trace log
    logger.debug('cmdr = ' + str(cmdrname) + ', system = ' + str(system) +
                 ', station = ' + str(station) + ', event = ' + str(entry))

    #
    # POST only certain requests to webserver
    #
    r = plugin.session.post(TARGET_URL, json=json.dumps(entry), timeout=5)
    r.raise_for_status()

    reply = r.json()
    msg_num = reply['msgnum']
    msg = reply['msg']

    logger.debug(f'{msgnum=}')
    logger.debug(f'{msg=}')


def set_status(r: str, color: str) -> None:
    plugin.carrier_status_msg['text'] = str(r)
    plugin.carrier_status_msg['foreground'] = color


if __name__ == "__main__":
    logger.info("This module " + os.path.basename(__file__) +
                " is not intended to be run stand-alone.")
    sys.exit(0)
