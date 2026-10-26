import discord
from discord.ext import commands
import asyncio
import os

THEME_COLOR = discord.Color.from_str("#111111")

class TicketActionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim Ticket", style=discord.ButtonStyle.success, custom_id="ticket_claim_btn")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        button.disabled = True
        button.label = f"Claimed by {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"Ticket successfully claimed by {interaction.user.mention}.")

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="ticket_close_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Initializing ticket closure sequence...", ephemeral=True)
        await asyncio.sleep(2)
        try:
            await interaction.channel.delete(reason="Ticket closed by user action.")
        except Exception:
            pass

class TicketSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.secondary, custom_id="open_ticket_panel")
    async def open_ticket(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        channel = await guild.create_text_channel(name=f"ticket-{user.name}", overwrites=overwrites)
        embed = discord.Embed(
            title="Support Ticket Created",
            description=f"Welcome {user.mention}. Support staff will assist you shortly.",
            color=THEME_COLOR
        )
        await channel.send(content=user.mention, embed=embed, view=TicketActionView())
        await interaction.response.send_message(f"Ticket generated successfully: {channel.mention}", ephemeral=True)

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="support")
    @commands.has_permissions(administrator=True)
    async def support_panel(self, ctx):
        """Sends the persistent support panel."""
        embed = discord.Embed(
            title="Support Center",
            description="Click the button below to open a ticket",
            color=THEME_COLOR
        )
        await ctx.send(embed=embed, view=TicketSetupView())

    @commands.command(name="claim")
    @commands.has_permissions(manage_channels=True)
    async def claim_ticket_cmd(self, ctx):
        """Claim the current support ticket."""
        if not ctx.channel.name.startswith("ticket-"):
            await ctx.send("This command can only be used inside active ticket channels.", delete_after=5)
            return
        await ctx.send(f"Ticket claimed by {ctx.author.mention}.")

    @commands.command(name="close")
    async def close_ticket_cmd(self, ctx):
        """Close the current support ticket channel."""
        if not ctx.channel.name.startswith("ticket-"):
            await ctx.send("This command can only be used inside active ticket channels.", delete_after=5)
            return
        await ctx.send("Archiving channel and closing ticket...")
        await asyncio.sleep(2)
        await ctx.channel.delete(reason=f"Closed by {ctx.author}")

    @commands.command(name="add")
    @commands.has_permissions(manage_channels=True)
    async def ticket_add(self, ctx, member: discord.Member):
        """Add a specified member to the current ticket."""
        if not ctx.channel.name.startswith("ticket-"):
            return
        await ctx.channel.set_permissions(member, read_messages=True, send_messages=True)
        await ctx.send(f"Added {member.mention} to the ticket.")

    @commands.command(name="remove")
    @commands.has_permissions(manage_channels=True)
    async def ticket_remove(self, ctx, member: discord.Member):
        """Remove a specified member's ticket access."""
        if not ctx.channel.name.startswith("ticket-"):
            return
        await ctx.channel.set_permissions(member, overwrite=None)
        await ctx.send(f"Removed {member.mention} from the ticket.")

    @commands.command(name="transcript")
    @commands.has_permissions(manage_channels=True)
    async def ticket_transcript(self, ctx):
        """Generates a text transcript of the active ticket session."""
        if not ctx.channel.name.startswith("ticket-"):
            return
        messages = [f"[{m.created_at}] {m.author}: {m.content}" async for m in ctx.channel.history(limit=200, oldest_first=True)]
        filename = f"{ctx.channel.name}-transcript.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(messages))
        await ctx.send("Transcript Generated:", file=discord.File(filename))
        os.remove(filename)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
