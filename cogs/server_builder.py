import discord
from discord.ext import commands
from discord import app_commands, Interaction
import json
import asyncio
from openai import OpenAI
from config import OPENAI_API_KEY
from prompt import SYSTEM_PROMPT
from database import Database

openai_client = OpenAI(api_key=OPENAI_API_KEY)

class ServerRefineModal(discord.ui.Modal, title="Refine Server Prompt"):
    prompt_input = discord.ui.TextInput(
        label="Describe adjustments or changes",
        style=discord.TextStyle.paragraph,
        placeholder="e.g. Add 3 voice rooms for gaming and a cybersecurity category...",
        required=True,
        max_length=1500
    )

    def __init__(self, cog, original_prompt: str):
        super().__init__()
        self.cog = cog
        self.original_prompt = original_prompt

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        new_prompt = f"{self.original_prompt}. Adjustments: {self.prompt_input.value}"
        await self.cog.generate_and_preview(interaction, new_prompt)


class TemplateModal(discord.ui.Modal, title="Flex Server Architect"):
    prompt_input = discord.ui.TextInput(
        label="What should your server look like?",
        style=discord.TextStyle.paragraph,
        placeholder="Describe your dream Discord server in detail (e.g. Valorant esports hub with team channels)...",
        required=True,
        max_length=1500
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        user_prompt = self.prompt_input.value
        await self.cog.generate_and_preview(interaction, user_prompt)


class CategorySelect(discord.ui.Select):
    def __init__(self, categories):
        options = []
        for idx, cat in enumerate(categories[:25]):
            options.append(discord.SelectOption(
                label=cat.get("name", f"Category {idx+1}")[:100],
                value=str(idx),
                emoji=cat.get("emoji", "📁")
            ))
        super().__init__(placeholder="Inspect channels in a category...", min_values=1, max_values=1, options=options)
        self.categories = categories

    async def callback(self, interaction: Interaction):
        idx = int(self.values[0])
        selected_cat = self.categories[idx]
        
        channels_text = ""
        for ch in selected_cat.get("channels", []):
            emoji = ch.get("emoji", "💬")
            c_type = "🔊" if ch.get("type") == "voice" else "💬"
            topic = f" - *{ch['topic']}*" if ch.get("topic") else ""
            channels_text += f"{emoji} `{ch['name']}` ({c_type}){topic}\n"

        embed = discord.Embed(
            title=f"{selected_cat.get('emoji', '📁')} {selected_cat['name']}",
            description=channels_text or "No channels in this category.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class PreviewView(discord.ui.View):
    def __init__(self, cog, layout_data: dict, prompt: str):
        super().__init__(timeout=600)
        self.cog = cog
        self.layout_data = layout_data
        self.prompt = prompt

        categories = layout_data.get("categories", [])
        if categories:
            self.add_item(CategorySelect(categories))

    @discord.ui.button(label="Create Server", style=discord.ButtonStyle.green, emoji="🚀")
    async def create_server(self, interaction: Interaction, button: discord.ui.Button):
        # Disable view buttons
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)

        await self.cog.build_server_execution(interaction, self.layout_data)

    @discord.ui.button(label="Refine Preview", style=discord.ButtonStyle.blurple, emoji="✏️")
    async def refine_preview(self, interaction: Interaction, button: discord.ui.Button):
        modal = ServerRefineModal(self.cog, self.prompt)
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="✖️")
    async def cancel(self, interaction: Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="❌ Server creation cancelled.", embed=None, view=self)


class ServerBuilderCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="template", description="Generate a custom Discord server structure using AI.")
    @app_commands.checks.has_permissions(administrator=True)
    async def template_command(self, interaction: Interaction):
        user_id = interaction.user.id
        can_use, count, reset_sec = await Database.check_and_increment_usage(user_id)

        if not can_use:
            hours = int(reset_sec // 3600)
            minutes = int((reset_sec % 3600) // 60)
            await interaction.response.send_message(
                f"⚠️ You have reached your daily limit of 5 server builds! Reset in **{hours}h {minutes}m**.",
                ephemeral=True
            )
            return

        modal = TemplateModal(self)
        await interaction.response.send_modal(modal)

    @template_command.error
    async def template_command_error(self, interaction: Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You must have **Administrator** or **Manage Server** permissions to use `/template`.",
                ephemeral=True
            )

    async def generate_and_preview(self, interaction: Interaction, prompt: str):
        await interaction.followup.send("🤖 **Flex AI** is crafting your server layout... Please wait.", ephemeral=True)

        try:
            response = await asyncio.to_thread(
                lambda: openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f"Generate a Discord server structure tailored strictly to this theme: {prompt}"}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7
                )
            )

            raw_json = response.choices[0].message.content
            layout = json.loads(raw_json)

        except Exception as e:
            await interaction.followup.send(f"❌ Failed to generate server design from AI: `{str(e)}`", ephemeral=True)
            return

        # Build Preview Embed
        roles = layout.get("roles", [])
        categories = layout.get("categories", [])
        total_channels = sum(len(c.get("channels", [])) for c in categories)

        embed = discord.Embed(
            title=f"🏗️ Server Preview: {layout.get('server_name', 'Custom Server')}",
            description=f"**Prompt:** *\"{prompt}\"*\n\nReview the AI-generated architecture below before applying it to this server.",
            color=0x2B2D31
        )

        embed.add_field(
            name="📊 Summary Statistics",
            value=f"• **Roles:** {len(roles)}\n• **Categories:** {len(categories)}\n• **Total Channels:** {total_channels}",
            inline=False
        )

        sample_roles = ", ".join([f"`{r['name']}`" for r in roles[:6]])
        if len(roles) > 6:
            sample_roles += f" + {len(roles)-6} more"
        embed.add_field(name="🎭 Roles Overview", value=sample_roles or "None", inline=False)

        sample_cats = "\n".join([f"{c.get('emoji', '📁')} **{c['name']}** ({len(c.get('channels', []))} channels)" for c in categories[:5]])
        if len(categories) > 5:
            sample_cats += f"\n*+ {len(categories)-5} more categories*"
        embed.add_field(name="📂 Category Structure", value=sample_cats or "None", inline=False)

        embed.set_footer(text="Flex Server Architect • Use dropdown to inspect specific channels")

        view = PreviewView(self, layout, prompt)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def build_server_execution(self, interaction: Interaction, layout: dict):
        guild = interaction.guild
        status_msg = await interaction.followup.send("⏳ Starting server building process...", ephemeral=True)

        try:
            # 1. Create Roles
            await status_msg.edit(content="⏳ **Step 1/3:** Creating roles...")
            created_roles = {}
            roles_data = layout.get("roles", [])
            for role_info in reversed(roles_data):  # Bottom to top hierarchy
                name = role_info.get("name")
                hex_color = role_info.get("color", "#999999").lstrip("#")
                color = discord.Color(int(hex_color, 16)) if hex_color else discord.Color.default()
                
                perms = discord.Permissions.none()
                if "Administrator" in role_info.get("permissions", []):
                    perms = discord.Permissions(administrator=True)

                role = await guild.create_role(name=name, color=color, permissions=perms)
                created_roles[name] = role
                await asyncio.sleep(0.4)  # Prevent Discord API rate limits

            # 2. Create Categories & Channels
            await status_msg.edit(content="⏳ **Step 2/3:** Creating categories and channels...")
            categories_data = layout.get("categories", [])
            
            for cat_info in categories_data:
                cat_emoji = cat_info.get("emoji", "")
                cat_name = f"{cat_emoji} {cat_info['name']}".strip()
                category = await guild.create_category(cat_name)

                for chan_info in cat_info.get("channels", []):
                    chan_emoji = chan_info.get("emoji", "")
                    chan_name = f"{chan_emoji}-{chan_info['name']}".strip() if chan_emoji else chan_info['name']
                    topic = chan_info.get("topic", None)

                    if chan_info.get("type") == "voice":
                        await guild.create_voice_channel(chan_name, category=category)
                    else:
                        await guild.create_text_channel(chan_name, category=category, topic=topic)

                    await asyncio.sleep(0.4)

            # 3. Finalize
            total_channels = sum(len(c.get("channels", [])) for c in categories_data)
            complete_embed = discord.Embed(
                title="✅ Server Setup Complete!",
                description=f"Flex successfully created the server architecture according to your specifications.",
                color=discord.Color.green()
            )
            complete_embed.add_field(name="Roles Created", value=str(len(roles_data)), inline=True)
            complete_embed.add_field(name="Categories Created", value=str(len(categories_data)), inline=True)
            complete_embed.add_field(name="Channels Created", value=str(total_channels), inline=True)

            await status_msg.edit(content="", embed=complete_embed)

        except discord.Forbidden:
            await status_msg.edit(content="❌ **Error:** Flex lacks the necessary permissions (Manage Roles / Manage Channels) to build this server.")
        except Exception as e:
            await status_msg.edit(content=f"❌ **An unexpected error occurred during creation:** `{str(e)}`")

async def setup(bot):
    await bot.add_cog(ServerBuilderCog(bot))
