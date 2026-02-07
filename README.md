# CTFeed
A Discord bot that automatically tracks CTF (Capture The Flag) events from [CTFtime.org](https://ctftime.org) and manages event workflows inside your guild.

## Features
- Detect new, updated, and canceled CTFTime events
- Sends notifications
- Create/join event channels
- Manage events with slash commands and REST APIs

## Prerequisites

Before getting started, you'll need:

- **Python 3.13** and **uv** package manager
- **Discord Bot Application** with proper permissions
- Domain
- Docker and Docker compose (recommanded)

### Setting Up Your Discord Bot

1. Visit the [Discord Developer Portal](https://discord.com/developers/applications) and create a new application
2. Navigate to the "Bot" section and copy your **bot token** (keep this secure!)
3. Navigate to the "OAuth2" section and copy your **Client ID** and **Client Secret** (keep these secure!)
4. Configure the following scopes and bot permissions:
    - Scopes
        - applications.commands
        - bot
    - Bot Permissions
        - Manage Channels
        - View Channels
        - Manage Events
        - Create Events
        - Send Messages
        - Create Public Threads
        - Create Private Threads
        - Send Messages in Threads
        - Manage Threads
        - Embed Links
        - Read Message History
        - Add Reactions
        - Use Slash Commands
        - Bypass Slowmode
5. Generate an invite link and add the bot to your Discord server

## Domain
Follow the instructions here or the web interface may not work.

We suppose that your domain is ``example.com`` and you serve the frontend of the bot on ``bot.example.com``.

Then you have to serve backend API on ``api.bot.example.com``.

- frontend - ``bot.example.com``
- backend - ``api.bot.example.com``

## Quick Start

The fastest way to get CTFeed running is through our automated Docker deployment.

### Docker Deployment (Recommended)

Get up and running in just two commands:

```bash
git clone https://github.com/ICEDTEACTF/CTFeed && cd CTFeed
./setup_env.sh
```

The `setup_env.sh` script will:
- Check Docker requirements
- Help you create the `.env` file with Discord bot configuration
- Offer to run the bot with Docker immediately

Once setup is complete, manage your bot with:
```bash
./run.sh
```

Or run Docker commands directly:
```bash
sudo docker-compose up -d --build    # Run in background
sudo docker-compose up --build       # Run with live logs
```

## Manual Setup

Prefer to set things up manually? Here's the traditional approach:

### What You'll Need
- **uv** and **Python 3.13**
- **Docker** and **Docker Compose**

### Install Dependencies

```bash
uv sync
```

### Configure Your Environment

Start by copying the example configuration:
```bash
cp .env.example .env
```

Then edit the `.env` file with your specific settings:

| Variable | Description |
|----------|-------------|
| `DISCORD_BOT_TOKEN` | Discord bot token |
| `GUILD_ID` | Target guild ID |
| `HTTP_SECRET_KEY` | Session secret key for FastAPI |
| `HTTP_FRONTEND_URL` | Frontend base URL (used for OAuth redirect) |
| `HTTP_COOKIE_DOMAIN` | Cookie domain for session |
| `DISCORD_OAUTH2_CLIENT_ID` | Discord OAuth2 client ID |
| `DISCORD_OAUTH2_CLIENT_SECRET` | Discord OAuth2 client secret |
| `CHECK_INTERVAL_MINUTES` | CTFTime polling interval |
| `DATABASE_URL` | PostgreSQL database URL |

`DISCORD_OAUTH2_REDIRECT_URI` is derived from `HTTP_FRONTEND_URL` as `HTTP_FRONTEND_URL/auth/login`.

Discord-side config values are stored in database and set after launch:

- `ANNOUNCEMENT_CHANNEL_ID`
- `CTF_CHANNEL_CATEGORY_ID`
- `ARCHIVE_CATEGORY_ID`
- `PM_ROLE_ID`
- `MEMBER_ROLE_ID`

### Launch the Bot
Choose your preferred method:

```bash
# With uv (recommended)
./startup.sh

# Or with Python directly
uvicorn --host 0.0.0.0 --port 5000 ctfeed:app
```

## Docker Management

### Interactive Management
Use our user-friendly script for easy bot management:
```bash
./run.sh
```

The `run.sh` script provides an interactive menu for Docker deployment options:
- Docker (background) - Recommended for production
- Docker (foreground) - See live logs
- Exit

### Docker Command Reference

Docker command cheatsheet for this bot:

| Action | Command | Description |
|--------|---------|-------------|
| **Start** | `sudo docker-compose up -d --build` | Launch bot in background |
| **Monitor** | `sudo docker-compose logs -f ctfeed` | View live logs |
| **Stop** | `sudo docker-compose down` | Gracefully stop the bot |
| **Restart** | `sudo docker-compose restart ctfeed` | Quick restart without rebuild |

## How CTFeed Works

Once running, CTFeed will:

1. Start FastAPI and the Discord bot together in the app lifespan
2. Initialize database and config cache
3. Poll CTFTime for new, updated, and removed events
4. Post notifications to the announcement channel
5. Create/join event channels and manage membership
6. Create or recover Discord scheduled events
7. Auto-archive expired or canceled events
