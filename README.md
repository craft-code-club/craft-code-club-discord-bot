# Craft & Code Club - Discord Bot


## Steps to create a Discord Bot

* [Create an application in Discord](./docs/CreateDiscordBot.md)
* [Setup Python environment](./docs/PythonEnvironment.md)
* [Configure Environment Variables](#configure-environment-variables)



## Configure Environment Variables
1. Then we need to create a `.env` file with the following content in the root of the project:

```txt
DISCORD_API_TOKEN=<your_discord_api_key>
```



## Install the required packages

### `dotenv`

```bash
echo python-dotenv >> requirements.txt
```

### `discord.py`

```bash
echo discord.py >> requirements.txt
```

### Install packages

```bash
pip install -r requirements.txt
```



## References
- [discord.py](https://discordpy.readthedocs.io/en/stable/)
- [Discord Bot Documentation](https://discord.com/developers/docs/intro)
