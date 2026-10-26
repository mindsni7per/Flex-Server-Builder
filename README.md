# Flex Utilities

A modular, high-performance Discord community management, ticketing, and administration bot built with Python and discord.py. Flex Utilities provides persistent moderation case logging, automated ticket processing via Groq AI, server layout anti-nuke snapshots, anti-raid mechanisms, and interactive configuration panels.

## Features

- **Dynamic Prefix Engine**: Per-guild custom prefix configuration with a default of `,,`.
- **Persistent Moderation Case System**: Automatic case assignment for bans, kicks, mutes, warnings, jails, and voiding with full audit history tracking.
- **Support Ticket Suite**: Interactive support panels, dynamic permission overwrites, claim/close workflows, and text transcript generation.
- **Groq AI Ticket Assistant**: Integrated natural-language processing using `llama-3.1-70b-versatile` for immediate, formal, and structured automated ticket responses.
- **AutoMod Rule Parser**: Translates natural-language moderation prompts into structured JSON trigger sets via Groq.
- **Security Systems**: Anti-Nuke state snapshots, Anti-Raid rate-limiting logic, and configurable Honeypot trap channels.
- **Community Utilities**: Managed giveaway workflows, broadcast messaging (`,,say`), and server-specific command blacklists.

## Installation

1. Clone the repository to your local environment or hosting server:
   ```bash
   git clone [https://github.com/your-repo/flex-utilities.git](https://github.com/your-repo/flex-utilities.git)
   cd flex-utilities
