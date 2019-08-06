import subprocess
import discord
from modules.base import BaseClass


class MainClass(BaseClass):
    name = "Panic"
    help_active = True
    help = {
        "description": "Dans quel état est Nikola Tesla",
        "commands": {
            "`{prefix}{command}`": "Donne l'état actuel de Nikola Tesla",
        }
    }
    color = 0x4fffb6
    command_text = "panic"

    async def command(self, message, args, kwargs):
        temperature = 0
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            temperature = int(f.read().rstrip("\n"))/1000
        with open("/proc/cpuinfo") as f:
            cpu_count=f.read().count('\n\n')
        embed = discord.Embed(title="[Panic] - Infos", color=self.color)
        with open("/proc/loadavg") as f:
            load_average = [ "**"+str(round((val/cpu_count)*100,1))+'%**' for val in map(float, f.read().split(' ')[0:3])]
        embed.add_field(
            name="Température",
            value="Nikola est à **{temperature}°C**".format(temperature=temperature))
        
        embed.add_field(
            name="Charge moyenne",
            value="Nikola est en moyenne, utilisé à :\n sur une minute : %s\n sur cinq minutes : %s\n sur quinze minutes : %s" % tuple(load_average) )
        await message.channel.send(embed=embed)
