import discord
from discord.ext import commands
import json
import os

CONFIG_FILE = "sniper_config.json"
THEME_COLOR = discord.Color.from_str("#111111")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

class ConfigDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Jail Channel", description="Configure jail notification channel", value="jail_channel"),
            discord.SelectOption(label="Mute Role", description="Configure role assigned upon mute", value="mute_role"),
            discord.SelectOption(label="Log Channel", description="Configure moderation audit trail channel", value="log_channel"),
        ]
        super().__init__(placeholder="Select configuration module to update...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"To update your {self.values[0].replace('_', ' ').title()}, please use standard server management settings.", ephemeral=True)

class ConfigView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(ConfigDropdown())

class Configuration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_data = load_config()

    @commands.command(name="config")
    @commands.has_permissions(administrator=True)
    async def config_panel(self, ctx):
        """Displays the server configuration panel."""
        guild_id = str(ctx.guild.id)
        g_conf = self.config_data.get(guild_id, {})

        jail_ch = ctx.guild.get_channel(g_conf.get("jail_channel_id"))
        mute_r = ctx.guild.get_role(g_conf.get("mute_role_id"))
        log_ch = ctx.guild.get_channel(g_conf.get("log_channel_id"))

        embed = discord.Embed(
            title="Flex Utilities - Server Configuration",
            description="Manage core security, logging, and restriction endpoints below.",
            color=THEME_COLOR
        )
        embed.add_field(name="Jail Channel", value=jail_ch.mention if jail_ch else "Not Configured", inline=True)
        embed.add_field(name="Mute Role", value=mute_r.mention if mute_r else "Not Configured", inline=True)
        embed.add_field(name="Log Channel", value=log_ch.mention if log_ch else "Not Configured", inline=True)
        embed.set_footer(text="Flex Utilities Management Engine")

        await ctx.send(embed=embed, view=ConfigView())

async def setup(bot):
    await bot.add_cog(Configuration(bot))
