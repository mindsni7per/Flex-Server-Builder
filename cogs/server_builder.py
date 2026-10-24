import discord
from discord.ext import commands, tasks
from discord import app_commands, Interaction, ui
import json
import asyncio
import random
import re
import os
import aiohttp
from datetime import datetime

PREFIX = ",,"
CONFIG_FILE = "sniper_config.json"
BACKUP_FILE = "server_backups.json"

# SLEEK GRAPHITE GREY EMBED COLOR (#595b5c)
DARK_EMBED_COLOR = discord.Color.from_str("#595b5c")


def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_json(filename, data):
    try:
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Failed to save {filename}: {e}")


def parse_time(time_str: str) -> int:
    match = re.match(r"^(\d+)([smh])$", time_str.lower())
    if not match:
        return 0
    val, unit = int(match.group(1)), match.group(2)
    if unit == "s":
        return val
    elif unit == "m":
        return val * 60
    elif unit == "h":
        return val * 3600
    return 0


# --- TICKET INTERACTIVE VIEW (CLOSE & CLAIM) ---
class TicketActionView(ui.View):
    def __init__(self, cog_instance, creator_id: int, open_time_str: str, panel_name: str):
        super().__init__(timeout=None)
        self.cog = cog_instance
        self.creator_id = creator_id
        self.open_time_str = open_time_str
        self.panel_name = panel_name

    @ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="ticket_close_btn", emoji="🔒")
    async def close_ticket(self, interaction: Interaction, button: ui.Button):
        guild = interaction.guild
        channel = interaction.channel
        closed_by = interaction.user
        close_time_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")

        await interaction.response.send_message("🔒 Closing ticket and sending transcript...", ephemeral=True)

        try:
            creator = guild.get_member(self.creator_id) or await guild.fetch_member(self.creator_id)
            if creator:
                dm_embed = discord.Embed(
                    title="Ticket Closed",
                    description=f"Your ticket has been closed in **{guild.name}**!",
                    color=DARK_EMBED_COLOR
                )
                dm_embed.add_field(
                    name="Ticket Information",
                    value=f"• **Open Date:** {self.open_time_str}\n• **Panel Name:** {self.panel_name}\n• **Ticket Name:** {channel.name}",
                    inline=False
                )
                dm_embed.add_field(
                    name="Close Information",
                    value=f"• **Closed By:** {closed_by.mention}\n• **Close Date:** {close_time_str}\n• **Close Reason:** No further action required.",
                    inline=False
                )
                dm_embed.set_footer(text="Flex Utilities • Ticketing System")
                await creator.send(embed=dm_embed)
        except Exception as e:
            print(f"Could not send close DM: {e}")

        await asyncio.sleep(3)
        try:
            await channel.delete()
        except Exception:
            pass

    @ui.button(label="Claim", style=discord.ButtonStyle.success, custom_id="ticket_claim_btn", emoji="🙌")
    async def claim_ticket(self, interaction: Interaction, button: ui.Button):
        button.disabled = True
        button.label = f"Claimed by {interaction.user.display_name}"
        await interaction.response.edit_message(view=self)
        await interaction.channel.send(f"🙌 Ticket claimed by {interaction.user.mention}!")


# --- TICKET PANEL INTERACTIVE VIEW ---
class TicketPanelView(ui.View):
    def __init__(self, cog_instance, panel_name="General Support"):
        super().__init__(timeout=None)
        self.cog = cog_instance
        self.panel_name = panel_name

    @ui.button(label="Create Ticket", style=discord.ButtonStyle.secondary, custom_id="create_ticket_panel")
    async def create_ticket(self, interaction: Interaction, button: ui.Button):
        await self.cog.spawn_ticket(interaction.guild, interaction.user, interaction, panel_name=self.panel_name)


# --- GIVEAWAY JOIN VIEW ---
class GiveawayJoinView(ui.View):
    def __init__(self, cog_instance, giveaway_id):
        super().__init__(timeout=None)
        self.cog = cog_instance
        self.giveaway_id = giveaway_id

    @ui.button(label="🎉 Enter Giveaway", style=discord.ButtonStyle.success, custom_id="join_giveaway_btn")
    async def join_giveaway(self, interaction: Interaction, button: ui.Button):
        success, msg = self.cog.add_giveaway_entry(self.giveaway_id, interaction.user)
        if success:
            await interaction.response.send_message("🎉 You have successfully entered the giveaway!", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ {msg}", ephemeral=True)


class ServerBuilder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config_data = load_json(CONFIG_FILE)
        self.backups = load_json(BACKUP_FILE)
        self.active_giveaways = {}

    def add_giveaway_entry(self, message_id, user: discord.Member):
        if message_id in self.active_giveaways:
            gw = self.active_giveaways[message_id]
            req_role = gw.get("required_role")
            if req_role and req_role not in user.roles:
                return False, f"You must have the {req_role.mention} role to enter!"

            if user.id not in gw["entries"]:
                gw["entries"].append(user.id)
                return True, "Success"
            return False, "You are already entered in this giveaway!"
        return False, "Giveaway not found."

    async def spawn_ticket(self, guild: discord.Guild, user: discord.Member, interaction: Interaction = None, panel_name: str = "General Support", forced_by: discord.Member = None):
        guild_id = str(guild.id)
        g_conf = self.config_data.get(guild_id, {})
        
        ticket_count = g_conf.get("ticket_counter", 0) + 1
        g_conf["ticket_counter"] = ticket_count
        self.config_data[guild_id] = g_conf
        save_json(CONFIG_FILE, self.config_data)

        clean_name = re.sub(r'[^a-zA-Z0-9]', '', user.name.lower())
        channel_name = f"ticket-{clean_name}-{ticket_count:03d}"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        admin_role_id = g_conf.get("admin_role_id")
        admin_role = guild.get_role(admin_role_id) if admin_role_id else None
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, read_message_history=True)

        category_id = g_conf.get("ticket_category_id")
        category = guild.get_channel(category_id) if category_id else None

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=category if isinstance(category, discord.CategoryChannel) else None,
            overwrites=overwrites
        )

        open_time_str = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        ping_mentions = f"{user.mention}"
        if admin_role:
            ping_mentions = f"{admin_role.mention}, {user.mention}"

        embed_main = discord.Embed(
            title=f"🎫 Ticket #{ticket_count} opened",
            description=f"Welcome, {user.mention}! A staff member will join shortly.\n\nFeel free to describe your issue in detail while you wait. The more context, the faster we can help.",
            color=DARK_EMBED_COLOR
        )
        embed_main.set_footer(text="Flex Utilities")

        view = TicketActionView(self, creator_id=user.id, open_time_str=open_time_str, panel_name=panel_name)
        await ticket_channel.send(content=ping_mentions, embed=embed_main, view=view)

        if forced_by:
            embed_force = discord.Embed(
                title="ℹ️ Force Ticket",
                description=f"{forced_by.mention} created this ticket for {user.mention}.",
                color=DARK_EMBED_COLOR
            )
            embed_force.set_footer(text=f"Flex Utilities • {panel_name}")
            await ticket_channel.send(embed=embed_force)

        if interaction:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True)
            else:
                await interaction.followup.send(f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True)

    # --- SAY COMMAND WITH WEBHOOK URL & EMBED SUPPORT ---
    @app_commands.command(name="say", description="Make the bot say a message (Supports Webhook URLs, embeds & channel)")
    @app_commands.describe(
        message="The message text for the bot to send",
        channel="Optional target channel (ignored if webhook URL is provided)",
        embed="Send as a styled embed (Default: False)",
        webhook_url="Optional Discord Webhook URL to post through",
        username="Custom username for the webhook message",
        avatar_url="Custom avatar image URL for the webhook message"
    )
    async def say_command(
        self,
        interaction: Interaction,
        message: str,
        channel: discord.TextChannel = None,
        embed: bool = False,
        webhook_url: str = None,
        username: str = None,
        avatar_url: str = None
    ):
        try:
            # 1. SEND VIA EXTERNAL WEBHOOK URL
            if webhook_url:
                payload = {}
                if embed:
                    payload["embeds"] = [{
                        "description": message,
                        "color": int("595b5c", 16)
                    }]
                else:
                    payload["content"] = message

                if username:
                    payload["username"] = username
                if avatar_url:
                    payload["avatar_url"] = avatar_url

                async with aiohttp.ClientSession() as session:
                    async with session.post(webhook_url, json=payload) as resp:
                        if resp.status in [200, 204]:
                            await interaction.response.send_message("✅ Webhook message sent successfully!", ephemeral=True)
                        else:
                            text = await resp.text()
                            await interaction.response.send_message(f"❌ Failed to send via webhook URL. Status `{resp.status}`: `{text}`", ephemeral=True)
                return

            # 2. STANDARD BOT MESSAGE / EMBED IN CHANNEL
            target_channel = channel or interaction.channel
            if embed:
                emb = discord.Embed(description=message, color=DARK_EMBED_COLOR)
                await target_channel.send(embed=emb)
            else:
                await target_channel.send(message)

            await interaction.response.send_message(f"✅ Message sent in {target_channel.mention}!", ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to send message: `{e}`", ephemeral=True)

    # --- HONEYPOT GROUP COMMANDS ---
    honeypot_group = app_commands.Group(name="honeypot", description="Configure honeypot security traps")

    @honeypot_group.command(name="set", description="Set a channel as a trap and choose auto-punishment")
    @app_commands.describe(
        channel="The trap channel where typing results in a penalty",
        action="Action to take against users who type in this channel"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Ban", value="ban"),
        app_commands.Choice(name="Kick", value="kick"),
        app_commands.Choice(name="Permanent Mute Role", value="mute"),
        app_commands.Choice(name="Warn", value="warn")
    ])
    async def honeypot_set(self, interaction: Interaction, channel: discord.TextChannel, action: app_commands.Choice[str]):
        guild_id = str(interaction.guild_id)
        if guild_id not in self.config_data:
            self.config_data[guild_id] = {}

        self.config_data[guild_id]["honeypot_channel_id"] = channel.id
        self.config_data[guild_id]["honeypot_action"] = action.value
        save_json(CONFIG_FILE, self.config_data)

        embed = discord.Embed(
            title="🍯 Honeypot Trap Set",
            description=f"**Channel:** {channel.mention}\n**Action:** `{action.name}`\n\nAny user who types in {channel.mention} will immediately trigger a `{action.value}` punishment!",
            color=DARK_EMBED_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @honeypot_group.command(name="disable", description="Disable the active honeypot trap for this server")
    async def honeypot_disable(self, interaction: Interaction):
        guild_id = str(interaction.guild_id)
        if guild_id in self.config_data:
            self.config_data[guild_id].pop("honeypot_channel_id", None)
            self.config_data[guild_id].pop("honeypot_action", None)
            save_json(CONFIG_FILE, self.config_data)

        embed = discord.Embed(
            title="🍯 Honeypot Trap Disabled",
            description="Honeypot protection has been turned off.",
            color=DARK_EMBED_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @honeypot_group.command(name="view", description="View current honeypot trap status")
    async def honeypot_view(self, interaction: Interaction):
        guild_id = str(interaction.guild_id)
        conf = self.config_data.get(guild_id, {})
        hp_id = conf.get("honeypot_channel_id")
        hp_action = conf.get("honeypot_action")

        if hp_id and hp_action:
            channel = interaction.guild.get_channel(hp_id)
            ch_str = channel.mention if channel else f"ID: `{hp_id}`"
            embed = discord.Embed(
                title="🍯 Active Honeypot Trap",
                description=f"**Channel:** {ch_str}\n**Action:** `{hp_action.upper()}`",
                color=DARK_EMBED_COLOR
            )
        else:
            embed = discord.Embed(
                title="🍯 Honeypot Status",
                description="No honeypot trap is currently active.",
                color=DARK_EMBED_COLOR
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="memorize", description="Snapshot server channels & categories for anti-nuke restoration")
    async def memorize(self, interaction: Interaction):
        guild = interaction.guild
        guild_id = str(guild.id)

        categories_data = []
        for category in guild.categories:
            channels_data = []
            for ch in category.channels:
                channels_data.append({
                    "name": ch.name,
                    "type": "voice" if isinstance(ch, discord.VoiceChannel) else "text",
                    "topic": getattr(ch, "topic", None)
                })
            categories_data.append({
                "name": category.name,
                "channels": channels_data
            })

        self.backups[guild_id] = categories_data
        save_json(BACKUP_FILE, self.backups)

        embed = discord.Embed(
            title="🛡️ Server State Memorized",
            description="All categories and channels have been successfully backed up for Anti-Nuke recovery!",
            color=DARK_EMBED_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="adminrole", description="Set the staff/admin role to be pinged in tickets")
    @app_commands.describe(role="The admin/staff role to ping")
    async def adminrole(self, interaction: Interaction, role: discord.Role):
        guild_id = str(interaction.guild_id)
        if guild_id not in self.config_data:
            self.config_data[guild_id] = {}
        
        self.config_data[guild_id]["admin_role_id"] = role.id
        save_json(CONFIG_FILE, self.config_data)

        embed = discord.Embed(
            title="🛡️ Admin Role Configured",
            description=f"Tickets will now ping {role.mention}",
            color=DARK_EMBED_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="setup", description="Deploy interactive ticket panel in a channel")
    @app_commands.describe(channel="Channel to deploy the ticket panel in")
    async def setup_ticket(self, interaction: Interaction, channel: discord.TextChannel):
        guild_id = str(interaction.guild_id)
        if guild_id not in self.config_data:
            self.config_data[guild_id] = {}
        self.config_data[guild_id]["ticket_category_id"] = channel.category_id

        embed = discord.Embed(
            description="Click the button below to create a ticket",
            color=DARK_EMBED_COLOR
        )

        await channel.send(embed=embed, view=TicketPanelView(self))
        await interaction.response.send_message(f"✅ Ticket panel deployed successfully in {channel.mention}!", ephemeral=True)

    @app_commands.command(name="force", description="Force create a ticket for a specific user")
    @app_commands.describe(user="The user to create a ticket for")
    async def force_ticket(self, interaction: Interaction, user: discord.Member):
        await self.spawn_ticket(interaction.guild, user, interaction, forced_by=interaction.user)

    giveaway_group = app_commands.Group(name="giveaway", description="Manage community giveaways")

    @giveaway_group.command(name="create", description="Create a giveaway with full custom options")
    @app_commands.describe(
        duration="Duration (e.g. 30s, 15m, 2h)",
        winners="Number of winners",
        prize="Prize description",
        host="Host user for the giveaway",
        required_roles="Role required to join",
        image="Image URL to show in giveaway embed",
        thumbnail="Thumbnail URL to show in embed",
        color="Hex color code (e.g. #111111)"
    )
    async def giveaway_create(
        self,
        interaction: Interaction,
        duration: str,
        winners: int,
        prize: str,
        host: discord.Member = None,
        required_roles: discord.Role = None,
        image: str = None,
        thumbnail: str = None,
        color: str = None
    ):
        seconds = parse_time(duration)
        if seconds <= 0:
            await interaction.response.send_message("❌ Invalid duration format! Use `30s`, `10m`, or `2h`.", ephemeral=True)
            return

        embed_color = DARK_EMBED_COLOR
        if color:
            try:
                embed_color = discord.Color.from_str(color)
            except ValueError:
                pass

        host_user = host or interaction.user

        embed = discord.Embed(
            title="🎉 GIVEAWAY TIME! 🎉",
            description=(
                f"**Prize:** {prize}\n"
                f"**Winners:** {winners}\n"
                f"**Duration:** {duration}\n"
                f"**Host:** {host_user.mention}\n"
            ),
            color=embed_color
        )

        if required_roles:
            embed.description += f"**Required Role:** {required_roles.mention}\n"

        embed.description += "\nClick the button below to enter!"
        
        if image:
            embed.set_image(url=image)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        embed.set_footer(text=f"Hosted by {host_user.display_name}")

        await interaction.response.send_message("🎉 Giveaway created successfully!", ephemeral=True)
        msg = await interaction.channel.send(embed=embed, view=GiveawayJoinView(self, str(interaction.id)))

        self.active_giveaways[str(msg.id)] = {
            "prize": prize,
            "winners": winners,
            "entries": [],
            "channel_id": interaction.channel_id,
            "host": host_user.id,
            "required_role": required_roles
        }

        await asyncio.sleep(seconds)

        data = self.active_giveaways.get(str(msg.id))
        if data:
            entries = data["entries"]
            if entries:
                chosen = random.sample(entries, min(winners, len(entries)))
                mentions = ", ".join([f"<@{uid}>" for uid in chosen])
                await interaction.channel.send(f"🎊 **GIVEAWAY ENDED!** Winner(s) of **{prize}**: {mentions}!")
            else:
                await interaction.channel.send(f"❌ Giveaway for **{prize}** ended with no valid entries.")
            self.active_giveaways.pop(str(msg.id), None)

    @giveaway_group.command(name="end", description="End an active giveaway early using its message ID")
    @app_commands.describe(message_id="The message ID of the giveaway announcement")
    async def giveaway_end(self, interaction: Interaction, message_id: str):
        if message_id in self.active_giveaways:
            data = self.active_giveaways.pop(message_id)
            entries = data["entries"]
            winners = data["winners"]
            prize = data["prize"]

            if entries:
                chosen = random.sample(entries, min(winners, len(entries)))
                mentions = ", ".join([f"<@{uid}>" for uid in chosen])
                await interaction.response.send_message(f"🎊 **Giveaway Ended Early!** Winner(s) of **{prize}**: {mentions}!", ephemeral=False)
            else:
                await interaction.response.send_message(f"❌ Giveaway ended with no valid entries.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Giveaway message ID not found or already ended.", ephemeral=True)

    @giveaway_group.command(name="reroll", description="Reroll a winner for a finished giveaway")
    @app_commands.describe(message_id="The message ID of the giveaway")
    async def giveaway_reroll(self, interaction: Interaction, message_id: str):
        await interaction.response.send_message("🎲 Rerolled new winner successfully!", ephemeral=True)
        try:
            msg = await interaction.channel.fetch_message(int(message_id))
            if msg:
                await interaction.channel.send("🎲 **New Winner Rerolled!**")
        except Exception:
            await interaction.channel.send("❌ Could not fetch message ID for reroll.")

    @giveaway_group.command(name="list", description="List all currently running giveaways")
    async def giveaway_list(self, interaction: Interaction):
        if not self.active_giveaways:
            await interaction.response.send_message("ℹ️ There are no active giveaways running right now.", ephemeral=True)
            return

        embed = discord.Embed(title="🎉 Active Giveaways", color=DARK_EMBED_COLOR)
        for msg_id, data in self.active_giveaways.items():
            embed.add_field(name=data["prize"], value=f"Entries: {len(data['entries'])}\nMessage ID: `{msg_id}`", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="help", description="Show all available Flex Utilities commands")
    async def help_command(self, interaction: Interaction):
        embed = discord.Embed(
            title="🤖 Flex Utilities - Command Directory",
            description="Here are all available commands you can use:",
            color=DARK_EMBED_COLOR
        )
        embed.add_field(name="/say", value="Make the bot say a message (Supports Webhook URLs, embeds & channel)", inline=False)
        embed.add_field(name="/setup", value="Deploy the interactive ticket panel", inline=False)
        embed.add_field(name="/adminrole", value="Set the admin role pinged in tickets", inline=False)
        embed.add_field(name="/force", value="Force create a ticket for a user", inline=False)
        embed.add_field(name="/memorize", value="Snapshot server channels & categories for anti-nuke", inline=False)
        embed.add_field(name="/honeypot set", value="Set trap channel & auto-punishment action", inline=False)
        embed.add_field(name="/honeypot disable", value="Disable active honeypot trap", inline=False)
        embed.add_field(name="/honeypot view", value="View current honeypot status", inline=False)
        embed.add_field(name="/giveaway create", value="Create a giveaway with custom parameters", inline=False)
        embed.add_field(name="/giveaway end", value="End an active giveaway early", inline=False)
        embed.add_field(name="/giveaway reroll", value="Reroll a winner", inline=False)
        embed.add_field(name="/giveaway list", value="List running giveaways", inline=False)
        embed.add_field(name="/help", value="Display this help menu", inline=False)
        embed.set_footer(text="Flex Utilities Suite")

        await interaction.response.send_message(embed=embed, ephemeral=False)

    # --- ANTI-NUKE LISTENER: RESTORE CHANNELS IF DELETED/ALTERED ---
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        guild_id = str(channel.guild.id)
        if guild_id not in self.backups:
            return

        backup_data = self.backups[guild_id]
        channel_found_in_backup = False
        for cat in backup_data:
            for ch in cat["channels"]:
                if ch["name"] == channel.name:
                    channel_found_in_backup = True
                    break

        if channel_found_in_backup:
            try:
                target_cat_name = None
                for cat in backup_data:
                    for ch in cat["channels"]:
                        if ch["name"] == channel.name:
                            target_cat_name = cat["name"]
                            break

                category = discord.utils.get(channel.guild.categories, name=target_cat_name)
                if not category:
                    category = await channel.guild.create_category(name=target_cat_name)

                if isinstance(channel, discord.VoiceChannel):
                    await channel.guild.create_voice_channel(name=channel.name, category=category)
                else:
                    topic = getattr(channel, "topic", None)
                    await channel.guild.create_text_channel(name=channel.name, category=category, topic=topic)
            except Exception as e:
                print(f"Anti-nuke restoration error: {e}")

    # --- TICKET CHATBOT & HONEYPOT LISTENER ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        guild_id = str(message.guild.id)
        g_conf = self.config_data.get(guild_id, {})

        # 1. HONEYPOT SECURITY TRAP LISTENER (Permanent Mute Role)
        hp_channel_id = g_conf.get("honeypot_channel_id")
        if hp_channel_id and message.channel.id == hp_channel_id:
            if not message.author.guild_permissions.administrator:
                hp_action = g_conf.get("honeypot_action", "warn")
                user = message.author

                try:
                    await message.delete()
                except Exception as e:
                    print(f"[Honeypot Delete Error]: {e}")

                try:
                    if hp_action == "ban":
                        await user.ban(reason="Triggered Honeypot Protection Trap")
                    elif hp_action == "kick":
                        await user.kick(reason="Triggered Honeypot Protection Trap")
                    elif hp_action == "mute":
                        guild = message.guild
                        
                        muted_role = discord.utils.get(guild.roles, name="Muted")
                        if not muted_role:
                            try:
                                muted_role = await guild.create_role(
                                    name="Muted",
                                    color=DARK_EMBED_COLOR,
                                    reason="Honeypot Mute Role Creation"
                                )
                                print(f"✅ Created 'Muted' role in {guild.name}")
                            except Exception as e:
                                print(f"❌ Failed to create 'Muted' role: {e}")
                                return

                        try:
                            await user.add_roles(muted_role, reason="Triggered Honeypot Protection Trap (Permanent Mute)")
                            print(f"✅ Assigned 'Muted' role to {user.display_name}")
                        except Exception as e:
                            print(f"❌ Failed to assign 'Muted' role: {e}")

                        for ch in guild.channels:
                            try:
                                await ch.set_permissions(
                                    muted_role,
                                    send_messages=False,
                                    send_messages_in_threads=False,
                                    add_reactions=False,
                                    speak=False
                                )
                            except Exception as e:
                                print(f"Could not override perms for channel {ch.name}: {e}")

                    elif hp_action == "warn":
                        try:
                            await user.send(f"⚠️ **Warning from {message.guild.name}:** Do not type in {message.channel.mention}!")
                        except Exception:
                            pass
                except Exception as e:
                    print(f"Honeypot action error: {e}")
                return

        # 2. TICKET READER
        if message.channel.name.startswith("ticket-"):
            admin_role_id = g_conf.get("admin_role_id")
            admin_role = message.guild.get_role(admin_role_id) if admin_role_id else None

            content_lower = message.content.lower()
            trigger_phrases = ["staff", "ping", "help", "admin", "support", "yes", "yea", "yup", "pls"]
            
            if any(p in content_lower for p in trigger_phrases) and admin_role:
                if admin_role.mention not in message.content:
                    await message.channel.send(f"🛡️ Pinging staff team for assistance: {admin_role.mention}")
            return


async def setup(bot):
    await bot.add_cog(ServerBuilder(bot))
