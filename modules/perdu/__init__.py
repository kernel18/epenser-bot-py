import datetime
import time

import discord
import matplotlib.pyplot as np

import utils.emojis
from modules.base import BaseClassPython


class MainClass(BaseClassPython):
    name = "Perdu"
    help = {
        "description": "Module donnant les statistiques sur les perdants",
        "commands": {
            "`{prefix}{command}`": "Donne le classement des perdants de la semaine",
            "`{prefix}{command} all`": "Donne le classement des perdants depuis toujours",
            "`{prefix}{command} <nombre de jours>`": "Donne le classement des perdants sur la durée spécifiée",
            "`{prefix}{command} stats [@mention]`": "Donne les statistiques d'un perdant.",
            "`{prefix}{command} stats history": "Affiche un graphique avec le nombre de pertes."
        }
    }

    def __init__(self, client):
        super().__init__(client)
        self.config.init({"channel": 0, "lost_role": 0, "min_delta": datetime.timedelta(minutes=26).total_seconds()})
        self.history = {}

    async def on_message(self, message: discord.Message):
        # Fill history
        if message.author.bot:
            return
        if message.channel.id == self.config.channel:
            if message.author.id not in self.history.keys():
                # Add new user if not found
                self.history.update(
                    {message.author.id: ([(message.created_at, datetime.timedelta(seconds=0)), ])}
                )
            else:
                # Update user and precompute timedelta
                delta = message.created_at - self.history[message.author.id][-1][0]
                if delta.total_seconds() >= self.config.min_delta:
                    self.history[message.author.id].append((message.created_at, delta))
        await self.parse_command(message)

    async def fill_history(self):
        self.history = {}
        async for message in self.client.get_channel(self.config.channel).history(limit=None):
            if message.author.id not in self.history.keys():
                # Add new user if not found
                self.history.update({message.author.id: ([(message.created_at, datetime.timedelta(seconds=0)), ])})
            else:
                # Update user and precompute timedelta
                delta = self.history[message.author.id][-1][0] - message.created_at
                if delta.total_seconds() >= self.config.min_delta:
                    self.history[message.author.id].append((message.created_at, delta))

    def get_top(self, top=10, since=datetime.datetime(year=1, month=1, day=1), with_user=None, only_users=None):
        """Return [(userid, [(date, delta), (date,delta), ...]), ... ]"""
        # Extract only messages after until
        if only_users is not None:
            # Extract data for only_users
            messages = []
            for user in only_users:
                try:
                    if self.history[user][-1][0] > since:
                        messages.append((user, [message for message in self.history[user] if message[0] > since]))
                except KeyError:
                    pass
            messages.sort(key=lambda x: len(x[1]), reverse=True)
            return messages
        if with_user is None:
            with_user = []
        # Extract TOP top users, and with_users data
        messages = []
        for user in self.history.keys():
            if self.history[user][-1][0] > since:
                messages.append((user, [message for message in self.history[user] if message[0] > since]))
        messages.sort(key=lambda x: len(x[1]), reverse=True)
        # Extract top-ten
        saved_messages = messages[:min(top, len(messages))]
        # Add with_user
        saved_messages.extend([message for message in messages if message[0] in with_user])
        return saved_messages

    async def com_fill(self, message: discord.Message, args, kwargs):
        if await self.auth(message.author):
            async with message.channel.typing():
                await self.fill_history()
            await message.channel.send("Fait.")

    async def com_all(self, message: discord.Message, args, kwargs):
        # Get all stats
        top = self.get_top()
        embed_description = "\n".join(
            f"{utils.emojis.write_with_number(i)} : <@{top[i][0]}> a **perdu {len(top[i][1])} fois** depuis la"
            f" création du salon à en moyenne **{sum(list(zip(*top[i][1]))[1], datetime.timedelta(0)) / len(top[i][1])} heures d'intervalle.**"
            for i in range(len(top))
        )[:2000]
        await message.channel.send(embed=discord.Embed(title="G-Perdu - Tableau des scores",
                                                       description=embed_description,
                                                       color=self.color))

    async def com_stats(self, message: discord.Message, args, kwargs):
        if "sum" in args:
            if message.mentions:
                top = self.get_top(only_users=[mention.id for mention in message.mentions] + [message.author.id])
            else:
                # TOP 5 + auteur
                top = self.get_top(top=5, with_user=[message.author.id])
            dates = []
            new_top = {}
            for t in top:
                for date, _ in t[1]:
                    dates.append(date)
            dates.sort()
            dates.append(datetime.datetime.today() + datetime.timedelta(days=1))
            for t in top:
                user = t[0]
                new_top.update({user: ([dates[0]], [0])})
                i = 0
                for date, _ in t[1]:
                    while date < dates[i]:
                        new_top[user][0].append(dates[i])
                        new_top[user][1].append(new_top[user][1][-1])
                        i += 1
                    new_top[user][0].append(date)
                    new_top[user][1].append(new_top[user][1][-1] + 1)

            to_plot = [t[1][1:] for t in new_top.values()]
            np.stackplot(dates, *to_plot)
            np.xlabel("Temps", fontsize=30)
            np.ylabel("Score", fontsize=30)
            np.title("Évolution du nombre de perdu au cours du temps.", fontsize=40)
            file_name = f"/tmp/{time.time()}.png"
            np.savefig(file_name, bbox_inches='tight')
            await message.channel.send(file=discord.File(file_name))

        if "history" in args:
            # Si mention, alors uniquement les mentions
            if message.mentions:
                top = self.get_top(only_users=[mention.id for mention in message.mentions] + [message.author.id])
            else:
                # TOP 5 + auteur
                top = self.get_top(top=5, with_user=[message.author.id])
            new_top = {}
            for t in top:
                c = 0
                counts = []
                dates = []
                for date, _ in t[1][::-1]:
                    c += 1
                    counts.append(c)
                    dates.append(date)
                new_top.update({t[0]: (dates, counts)})
            np.figure(num=None, figsize=(25, 15), dpi=120, facecolor='w', edgecolor='k')
            for user, (dates, counts) in new_top.items():
                np.plot_date(dates, counts, linestyle='-')
            np.xlabel("Temps", fontsize=30)
            np.ylabel("Score", fontsize=30)
            np.title("Évolution du nombre de perdu au cours du temps.", fontsize=40)
            file_name = f"/tmp/{time.time()}.png"
            np.savefig(file_name, bbox_inches='tight')
            await message.channel.send(file=discord.File(file_name))

    async def command(self, message, args, kwargs):
        if message.mentions:
            await self.com_stats(message, args, kwargs)
        since = datetime.datetime.now() - datetime.timedelta(days=7)
        if args[0]:
            try:
                since = datetime.datetime.now() - datetime.timedelta(days=float(args[0]))
            except ValueError:
                pass
        top = self.get_top(10, since)
        embed_description = "\n".join(
            f"{utils.emojis.write_with_number(i)} : <@{top[i][0]}> a **perdu {len(top[i][1])} fois** depuis la"
            f" création du salon à en moyenne **{sum(list(zip(*top[i][1]))[1], datetime.timedelta(0)) / len(top[i][1])} heures d'intervalle.**"
            for i in range(len(top))
        )[:2000]
        await message.channel.send(embed=discord.Embed(title="G-Perdu - Tableau des scores",
                                                       description=embed_description,
                                                       color=self.config.color))