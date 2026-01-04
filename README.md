# CTFeed

A Discord bot that automatically tracks CTF (Capture The Flag) events from [CTFtime.org](https://ctftime.org) and sends notifications when new competitions are announced.

## Prerequisites

Before getting started, you'll need:

- **Python 3.13** and **uv** package manager
- **Discord Bot Application** with proper permissions

### Setting Up Your Discord Bot

1. Visit the [Discord Developer Portal](https://discord.com/developers/applications) and create a new application
2. Navigate to the "Bot" section and copy your bot token (keep this secure!)
3. Configure the following bot permissions:
   - **Send Messages** - Allow the bot to post CTF announcements
   - **Manage Messages** - Enable the bot to manage its own messages
4. Generate an invite link and add the bot to your Discord server

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

### 1. Install Dependencies

```bash
uv sync
```

### Configure Your Environment

Start by copying the example configuration:
```bash
cp .env.example .env
```

Then edit the `.env` file with your specific settings. Focus on these key variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `DISCORD_BOT_TOKEN` | Your Discord bot token | `MTIzNDU2Nzg5...` |
| `CHECK_INTERVAL_MINUTES` | How often to check for new CTFs | `30` (default) |
| `ANNOUNCEMENT_CHANNEL_ID` | Channel id for announcements | `911612541829009418` |
| `CTF_CHANNEL_CATETORY_ID` | Category id for CTF event channel creations | `1454642939559940329` |
| `TIMEZONE` | time zone for displaying | `Asia/Taipei` (default) |

*Other configuration options can remain at their default values.*

### Launch the Bot
Choose your preferred method:

```bash
# With uv (recommended)
uv run python ctfeed.py

# Or with Python directly
python3 ctfeed.py
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

Once running, the bot will:

1. Automatically check CTFtime.org for new CTF events
2. Post announcements in your designated Discord channel
3. Use `data/database.db` to track announced events, avoid duplicates, record CTF event channel, and more.