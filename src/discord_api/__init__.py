"""Minimal Discord API surface for a gateway-less (serverless) bot.

`discord.py` is a gateway-first library: it can only dispatch commands from
MESSAGE_CREATE and only build `discord.Interaction` objects from a live
websocket session, so it has no supported entry point for an HTTP
Interactions Endpoint. Azure Functions cannot hold that websocket open, so
this package replaces it with the two pieces we actually need:

  * `rest`         - the handful of REST routes the bot calls (aiohttp).
  * `interactions` - Ed25519 request verification and response builders.
"""
