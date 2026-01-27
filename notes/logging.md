# About logging
- Critical
    - fail to initialize database
    - fail to initialize config in database
    - fail to get or update config from settings (cache) -> src.database.model.Config, src.database.model.config_info and src.config.Settings are out of sync 
    - Guild not found
    - (discord bot) fail to load extension