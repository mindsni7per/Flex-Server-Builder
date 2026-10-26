import discord
from discord.ext import commands

THEME_COLOR = discord.Color.from_str("#111111")

class Utilities(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.blacklisted_users = set()

    @commands.command(name="say")
    @commands.has_permissions(manage_messages=True)
    async def say_utility(self, ctx, *, message: str):
        """Send a message authored by Flex Utilities."""
        await ctx.message.delete()
        embed = discord.Embed(description=message, color=THEME_COLOR)
        embed.set_footer(text=f"Broadcasted via Flex Utilities • Requested by {ctx.author}")
        await ctx.send(embed=embed)

    @commands.group(name="blacklist", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def blacklist(self, ctx, member: discord.Member = None, *, reason: str = None):
        """Blacklist a user from bot utilities and tickets."""
        if member:
            self.blacklisted_users.add(member.id)
            await ctx.send(f"Blacklisted {member.mention} from Flex Utilities commands. Reason: {reason or 'None'}")
        else:
            await ctx.send("Usage: ,,blacklist @user [reason] or ,,blacklist remove @user")

    @blacklist.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def blacklist_remove(self, ctx, member: discord.Member):
        """Remove user from blacklist."""
        if member.id in self.blacklisted_users:
            self.blacklisted_users.remove(member.id)
            await ctx.send(f"Removed {member.mention} from the blacklist.")
        else:
            await ctx.send("User is not currently blacklisted.")

async def setup(bot):
    await bot.add_cog(Utilities(bot))
