import discord
from discord.ext import commands

THEME_COLOR = discord.Color.from_str("#111111")

class HelpSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx, *, command_name: str = None):
        """Display help documentation for Flex Utilities commands."""
        if command_name:
            cmd = self.bot.get_command(command_name)
            if not cmd:
                await ctx.send("Command not found.", delete_after=5)
                return

            embed = discord.Embed(
                title=f"Command Help: ,,{cmd.name}",
                description=cmd.help or "No description provided.",
                color=THEME_COLOR
            )
            embed.add_field(name="Syntax", value=f"```,,{cmd.name} {cmd.signature}```", inline=False)
            embed.set_footer(text="Flex Utilities Command Reference")
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title="Flex Utilities - Command Directory",
            description="Use ,,help <command> for specific parameters and syntax guidelines.",
            color=THEME_COLOR
        )
        embed.add_field(
            name="Categories",
            value=(
                "• **General & Setup**: ,,config, ,,help\n"
                "• **Tickets**: ,,support, ,,claim, ,,close, ,,add, ,,remove, ,,transcript\n"
                "• **Moderation**: ,,ban, ,,kick, ,,mute, ,,warn, ,,softban, ,,hardban, ,,jail, ,,unjail, ,,nick, ,,lock, ,,unlock, ,,purge-p, ,,botclear-bc, ,,modlogs, ,,void\n"
                "• **Security**: ,,antinuke, ,,antiraid, ,,honeypot\n"
                "• **Auto Moderation**: ,,automod\n"
                "• **Giveaways**: ,,giveaway create, ,,giveaway end, ,,giveaway reroll, ,,giveaway edit\n"
                "• **Utilities**: ,,say, ,,blacklist"
            ),
            inline=False
        )
        embed.set_footer(text="Flex Utilities Secure Environment")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpSystem(bot))
