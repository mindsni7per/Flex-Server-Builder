# Flex - AI Discord Server Architect

Flex is a production-ready Discord bot built with `discord.py` that listens strictly to user prompt descriptions and generates thematic server setups complete with roles, categories, channels, emojis, and topics.

## Features
- **Strict Prompt Adherence**: Generates roles and channels specifically built for the user's prompt (no random boilerplate channels).
- **Interactive UI**: Slash commands, Modals, Category inspection select menus, and action buttons.
- **Daily Limits**: Built-in SQLite tracking (5 uses per user every 24 hours).
- **Rate-Limit Prevention**: Includes artificial delays during server creation to comply with Discord API limits.

## Setup Instructions

1. **Clone or copy the repository files.**
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
