#!/bin/bash

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

echo -e "${CYAN}===================================${NC}"
echo -e "${WHITE}    CTFeed Environment Setup${NC}"
echo -e "${CYAN}===================================${NC}"
echo ""

# Function to check required tools
check_tools() {
    echo -e "${BLUE}Checking required tools...${NC}"
    
    if command -v docker > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Docker is installed: ${WHITE}$(docker --version)${NC}"
    else
        echo -e "${RED}✗ Docker is not installed${NC}"
    fi
    
    if command -v docker-compose > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Docker Compose is available: ${WHITE}$(docker-compose --version)${NC}"
    else
        echo -e "${RED}✗ Docker Compose is not installed${NC}"
    fi
}

check_data_directory() {
    if [ ! -w "data" ]; then
        echo -e "${YELLOW}✗ Data directory is not writable, creating...${NC}"
        mkdir -p data
        chmod 666 data/known_events.json 2>/dev/null || true
    fi
    if [ ! -f "data/known_events.json" ]; then
        echo -e "${YELLOW}✗ known_events.json not found, creating...${NC}"
        echo "[]" > data/known_events.json
        chmod 666 data/known_events.json 2>/dev/null || true
    fi
    echo -e "${GREEN}✓ Data directory is writable and ${WHITE}data/known_events.json${NC} ${GREEN}is created${NC}"
    echo ""
}

# Run system checks
check_tools
check_data_directory

if [ -f ".env" ]; then
    echo -e "${YELLOW}.env already exists! Nothing to do.${NC}"
    echo -e "${BLUE}If you want to run again please rm the .env file${NC}"
    echo ""
    
    while true; do
        echo -e -n "${YELLOW}Would you like to run the bot now? (y/n): ${NC}"
        read choice
        echo ""
        case $choice in
            [Yy]* ) 
                clear
                ./run.sh
                exit 0
                ;;
            [Nn]* ) 
                echo -e "${BLUE}Exiting setup.${NC}"
                exit 0
                ;;
            * )
                echo -e "${RED}Invalid choice. Please enter y or n.${NC}"
                ;;
        esac
    done
fi

if [ ! -f ".env.example" ]; then
    echo ".env.example file not found!"
    echo "Please make sure you're running this script from the project root directory."
    exit 1
fi

echo "Please provide the following information:"
echo "   (Press Enter after pasting each value)"
echo ""

echo "Discord Bot Token:"
echo "   Get this from https://discord.com/developers/applications"
while true; do
    read -p "   Paste your Discord Bot Token: " DISCORD_BOT_TOKEN
    if [ -n "$DISCORD_BOT_TOKEN" ]; then
        break
    else
        echo "   Error: Discord Bot Token cannot be empty. Please try again."
    fi
done

echo ""
echo "Check Interval (in minutes):"
echo "   How often should the bot check for new CTF events?"
echo "   Default is 30 minutes"
read -p "   Enter check interval in minutes (press Enter for default 30): " CHECK_INTERVAL_MINUTES
if [ -z "$CHECK_INTERVAL_MINUTES" ]; then
    CHECK_INTERVAL_MINUTES=30
fi

echo ""
echo "Announcement Channel ID:"
echo "   The Discord channel where CTF announcements will be posted"
echo "   The channel id that on your server"
while true; do
    read -p "   Paste your Discord Channel ID: " ANNOUNCEMENT_CHANNEL_ID
    if [ -n "$ANNOUNCEMENT_CHANNEL_ID" ]; then
        break
    else
        echo "   Error: Discord Channel Name cannot be empty. Please try again."
    fi
done

echo ""
echo "CTF Channel Category ID:"
echo "   The Discord category where CTF channels will be created"
echo "   The category id that on your server"
while true; do
    read -p "   Paste your Discord Category ID: " CTF_CHANNEL_CATETORY_ID
    if [ -n "$CTF_CHANNEL_CATETORY_ID" ]; then
        break
    else
        echo "   Error: Discord Channel Name cannot be empty. Please try again."
    fi
done

echo ""
echo "Time zone:"
echo "   The display time zone"
echo "   Default is Asia/Taipei"
read -p "   Enter time zone (press Enter for default Asia/Taipei): " TIMEZONE
if [ -z "$TIMEZONE" ]; then
    TIMEZONE="Asia/Taipei"
fi

echo ""
echo "Please review your configuration:"
echo "   Discord Bot Token: ${DISCORD_BOT_TOKEN:0:30}********** (hidden)"
echo "   Check Interval: $CHECK_INTERVAL_MINUTES minutes"
echo "   Announcement Channel ID: $ANNOUNCEMENT_CHANNEL_ID"
echo "   CTF Channel Category ID: $CTF_CHANNEL_CATETORY_ID"
echo "   Time Zone: $TIMEZONE"
echo ""

while true; do
    read -p "Is this configuration correct? (y/n): " -n 1 -r
    echo ""
    case $REPLY in
        [Yy]* ) 
            break
            ;;
        [Nn]* ) 
            echo "Configuration cancelled. Please run the script again."
            exit 0
            ;;
        * ) 
            echo "Please answer y (yes) or n (no)."
            ;;
    esac
done

echo ""
echo "Writing configuration to .env file..."
echo ""

cat > .env << EOF
# Discord Bot Configuration
DISCORD_BOT_TOKEN=$DISCORD_BOT_TOKEN

# CTF Tracking Configuration
CHECK_INTERVAL_MINUTES=$CHECK_INTERVAL_MINUTES
ANNOUNCEMENT_CHANNEL_ID=$ANNOUNCEMENT_CHANNEL_ID
CTF_CHANNEL_CATETORY_ID=$CTF_CHANNEL_CATETORY_ID

# Misc
TIMEZONE="$TIMEZONE"
EOF

echo -e "${GREEN}✓ Configuration complete! .env file created successfully.${NC}"
echo ""
echo -e "${WHITE}Setup is now complete!${NC}"
echo ""
echo -e "${YELLOW}To run your CTFeed bot, use the run script:${NC}"
echo -e "${CYAN}   ./run.sh${NC}"
echo ""

while true; do
    echo -e -n "${YELLOW}Would you like to run the bot now? (y/n): ${NC}"
    read choice
    echo ""
    case $choice in
        [Yy]* ) 
            ./run.sh
            exit 0
            ;;
        [Nn]* ) 
            echo -e "${BLUE}Setup complete! You can run the bot later with:${NC}"
            echo -e "${CYAN}   ./run.sh${NC}"
            echo ""
            echo -e "${YELLOW}Or run manually with:${NC}"
            echo -e "${BLUE}   uv run python ctfeed.py${NC}"
            echo -e "${BLUE}   sudo docker-compose up -d --build${NC}"
            exit 0
            ;;
        * ) 
            echo -e "${RED}Invalid choice. Please enter y or n.${NC}"
            ;;
    esac
done