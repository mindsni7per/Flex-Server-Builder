import discord
from discord.ext import commands
from groq import Groq
from config import GROQ_API_KEY

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
THEME_COLOR = discord.Color.from_str("#111111")

class Automod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="automod")
    @commands.has_permissions(administrator=True)
    async def automod_panel(self, ctx, *, natural_prompt: str = None):
        """Configure automod rules using natural language prompts processed via Groq."""
        if not natural_prompt:
            embed = discord.Embed(
                title="AutoMod Rule Generator",
                description="Provide a natural language rule description. \n*Example:* `,,automod Warn users who repeatedly post invites.`",
                color=THEME_COLOR
            )
            await ctx.send(embed=embed)
            return

        if not groq_client:
            await ctx.send("Groq API client is not initialized in server configuration.")
            return

        try:
            completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a professional Discord AutoMod parser. Convert the user rule into clean, structured JSON format with keys: trigger, threshold, and action."},
                    {"role": "user", "content": natural_prompt}
                ],
                model="llama-3.1-70b-versatile",
                temperature=0.2
            )
            parsed_rule = completion.choices[0].message.content.strip()
            
            embed = discord.Embed(
                title="AutoMod Rule Interpreted",
                description=f"**Original Prompt:** {natural_prompt}\n\n**Interpreted Configuration:**\n```json\n{parsed_rule}\n```",
                color=THEME_COLOR
            )
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"Failed to process rule via Groq API: {e}")

async def setup(bot):
    await bot.add_cog(Automod(bot))
