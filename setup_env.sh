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

# Run system checks
check_tools

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
    echo ""
    if [ -n "$DISCORD_BOT_TOKEN" ]; then
        break
    else
        echo "   Error: Discord Bot Token cannot be empty. Please try again."
    fi
done

echo ""
echo "Guild ID:"
echo "   Your Discord server (Guild) ID"
while true; do
    read -p "   Paste your Guild ID: " GUILD_ID
    if [ -n "$GUILD_ID" ]; then
        break
    else
        echo "   Error: Guild ID cannot be empty. Please try again."
    fi
done

echo ""
echo "HTTP Secret Key:"
echo "   A random secret key for HTTP API authentication"
while true; do
    read -p "   Paste your HTTP Secret Key: " HTTP_SECRET_KEY
    echo ""
    if [ -n "$HTTP_SECRET_KEY" ]; then
        break
    else
        echo "   Error: HTTP Secret Key cannot be empty. Please try again."
    fi
done

echo ""
echo "HTTP Frontend URL:"
echo "   Default is https://example.com"
read -p "   Enter HTTP frontend URL (press Enter for default https://example.com): " HTTP_FRONTEND_URL
if [ -z "$HTTP_FRONTEND_URL" ]; then
    HTTP_FRONTEND_URL="https://example.com"
fi

echo ""
echo "HTTP Cookie Domain:"
echo "   Default is .example.com"
read -p "   Enter HTTP cookie domain (press Enter for default .example.com): " HTTP_COOKIE_DOMAIN
if [ -z "$HTTP_COOKIE_DOMAIN" ]; then
    HTTP_COOKIE_DOMAIN=".example.com"
fi

echo ""
echo "Discord OAuth2 Client ID:"
echo "   Get this from https://discord.com/developers/applications"
while true; do
    read -p "   Paste your Discord OAuth2 Client ID: " DISCORD_OAUTH2_CLIENT_ID
    if [ -n "$DISCORD_OAUTH2_CLIENT_ID" ]; then
        break
    else
        echo "   Error: Discord OAuth2 Client ID cannot be empty. Please try again."
    fi
done

echo ""
echo "Discord OAuth2 Client Secret:"
echo "   Get this from https://discord.com/developers/applications"
while true; do
    read -p "   Paste your Discord OAuth2 Client Secret: " DISCORD_OAUTH2_CLIENT_SECRET
    echo ""
    if [ -n "$DISCORD_OAUTH2_CLIENT_SECRET" ]; then
        break
    else
        echo "   Error: Discord OAuth2 Client Secret cannot be empty. Please try again."
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
echo "Database URL:"
echo "   Default is postgresql+asyncpg://root:default_database_password@database:5432/icedtea"
read -p "   Enter database URL (press Enter for default value): " DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    DATABASE_URL="postgresql+asyncpg://root:default_database_password@database:5432/icedtea"
fi

echo ""
echo "Please review your configuration:"
echo "   Discord Bot Token: ${DISCORD_BOT_TOKEN:0:30}********** (hidden)"
echo "   Guild ID: $GUILD_ID"
echo "   HTTP Secret Key: ${HTTP_SECRET_KEY:0:10}********** (hidden)"
echo "   HTTP Frontend URL: $HTTP_FRONTEND_URL"
echo "   HTTP Cookie Domain: $HTTP_COOKIE_DOMAIN"
echo "   Discord OAuth2 Client ID: $DISCORD_OAUTH2_CLIENT_ID"
echo "   Discord OAuth2 Client Secret: ${DISCORD_OAUTH2_CLIENT_SECRET:0:10}********** (hidden)"
echo "   Check Interval: $CHECK_INTERVAL_MINUTES minutes"
echo "   Database URL: $DATABASE_URL"
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
GUILD_ID=$GUILD_ID

# HTTP API Configuration
HTTP_SECRET_KEY=$HTTP_SECRET_KEY
HTTP_FRONTEND_URL=$HTTP_FRONTEND_URL
HTTP_COOKIE_DOMAIN=$HTTP_COOKIE_DOMAIN

# Discord OAuth2 Configuration
DISCORD_OAUTH2_CLIENT_ID=$DISCORD_OAUTH2_CLIENT_ID
DISCORD_OAUTH2_CLIENT_SECRET=$DISCORD_OAUTH2_CLIENT_SECRET

# CTFTime Configuration
CHECK_INTERVAL_MINUTES=$CHECK_INTERVAL_MINUTES

# Database Configuration
DATABASE_URL="$DATABASE_URL"
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
            echo -e "${BLUE}   bash ./startup.sh${NC}"
            echo -e "${BLUE}   sudo docker-compose up -d --build${NC}"
            exit 0
            ;;
        * ) 
            echo -e "${RED}Invalid choice. Please enter y or n.${NC}"
            ;;
    esac
done
