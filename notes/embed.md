# About Embed
- 在大部分情況下
    - 一般的 Embed 使用 ``discord.Color.green()``
    - 代表成功的 Embed 使用 ``discord.Color.green()``
    - 代表失敗、錯誤的 Embed 使用 ``discord.Color.red()``

- 在 Config 中
    - 如果所有設定 / 該項設定是無效設定（未設定、設定值無效），Embed 使用 ``discord.Color.red()``
    - 如果設定有效，Embed 使用 ``discord.Color.red()``