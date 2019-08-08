"""Base class for module, never use directly !!!"""
import asyncio
import os
import sys
import pickle
import traceback

import discord
import lupa

from modules.base.Base import BaseClass
from storage import FSStorage
import storage.path as path


class BaseClassLua(BaseClass):
    """Base class for all modules, Override it to make submodules"""
    name = ""
    help = {
        "description": "",
        "commands": {

        }
    }
    help_active = False
    color = 0x000000
    command_text = None
    super_users = []
    authorized_roles = []

    def __init__(self, client, path):
        """Initialize module class

        Initialize module class, always call it to set self.client when you override it.

        :param client: client instance
        :type client: NikolaTesla"""
        super().__init__(client)
        # Get lua globals
        self.lua = lupa.LuaRuntime(unpack_returned_tuples=True)
        print(os.path.abspath(path))
        self.luaMethods = self.lua.require(path)

    def call(self, method, *args, **kwargs):
        # Try to run lua method then python one
        if self.luaMethods[method] is not None:
            async def coro(*args, **kwargs):
                self.luaMethods[method](self, asyncio.ensure_future, discord, *args, *kwargs)
            asyncio.ensure_future(self.client._run_event(coro, method, *args, **kwargs), loop=self.client.loop)
        try:
            coro = getattr(self, method)
        except AttributeError:
            pass
        else:
            asyncio.ensure_future(self.client._run_event(coro, method, *args, **kwargs), loop=self.client.loop)

    def dispatch(self, event, *args, **kwargs):
        method = "on_"+event
        if self.luaMethods[method] is not None:
            async def coro(*args, **kwargs):
                self.luaMethods[method](self, asyncio.ensure_future, discord, *args, **kwargs)
            asyncio.ensure_future(self.client._run_event(coro, method, *args, **kwargs), loop=self.client.loop)
        else: # If lua method not found, pass
            super().dispatch(event, *args, **kwargs)

    async def parse_command(self, message):
        """Parse a command_text from received message and execute function
        %git update
        com_update(m..)
        Parse message like `{prefix}{command_text} subcommand` and call class method `com_{subcommand}`.

        :param message: message to parse
        :type message: discord.Message"""
        if message.content.startswith(self.client.config["prefix"] + (self.command_text if self.command_text else "")):

            content = message.content.lstrip(
                self.client.config["prefix"] + (self.command_text if self.command_text else ""))
            sub_command, args, kwargs = self._parse_command_content(content)
            sub_command = "com_" + sub_command
            if await self.auth(message.user):
                if self.luaMethods[sub_command] is not None:
                    self.luaMethods[sub_command](self, asyncio.ensure_future, discord, message, args, kwargs)
                else:
                    if self.luaMethods["command"] is not None:
                        self.luaMethods["command"](self, asyncio.ensure_future, discord, message, [sub_command[4:]] + args, kwargs)
            else:
                await self.unautorized(message, [sub_command[4:]] + args, kwargs)

