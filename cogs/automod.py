import discord
from discord.ext import commands
import random
import asyncio

THEME_COLOR = discord.Color.from_str("#111111")

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.entries = set()

    @discord.ui.button(label="Enter Giveaway", style=discord.ButtonStyle.success, custom_id="enter_giveaway_btn")
    async def enter_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.entries:
            await interaction.response.send_message("You are already entered into this giveaway.", ephemeral=True)
        else:
            self.entries.add(interaction.user.id)
            await interaction.response.send_message("Entry confirmed.", ephemeral=True)

class Giveaways(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="giveaway", invoke_without_command=True)
    async def giveaway(self, ctx):
        """Giveaway management command root."""
        await ctx.send("Usage: ,,giveaway create, ,,giveaway end, ,,giveaway reroll, ,,giveaway edit", delete_after=5)

    @giveaway.command(name="create")
    @commands.has_permissions(manage_guild=True)
    async def giveaway_create(self, ctx, prize: str, duration_seconds: int):
        """Create a new giveaway instance."""
        embed = discord.Embed(
            title="GIVEAWAY",
            description=f"**Prize:** {prize}\n**Hosted By:** {ctx.author.mention}\n\nClick the button below to participate.",
            color=THEME_COLOR
        )
        view = GiveawayView()
        msg = await ctx.send(embed=embed, view=view)
        
        await ctx.send(f"Giveaway initialized for **{prize}** ({duration_seconds}s duration).")
        await asyncio.sleep(duration_seconds)
        
        if view.entries:
            winner_id = random.choice(list(view.entries))
            winner = ctx.guild.get_member(winner_id)
            winner_mention = winner.mention if winner else f"<@{winner_id}>"
            await ctx.send(f"Giveaway Concluded. Congratulations {winner_mention} for winning **{prize**}.")
        else:
            await ctx.send(f"Giveaway for **{prize}** concluded with no valid entries.")

async def setup(bot):
    await bot.add_cog(Giveaways(bot))
