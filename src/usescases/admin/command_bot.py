from .version_command import VersionCommandBot
from .info_command import InfoCommandBot
from .add_role_command import AddRoleCommandBot
from .event_session_link_command import EventSessionLinkCommandBot
from .server_status_command import ServerStatusCommandBot
from .events_command import EventsCommandBot, EventDetailsCommandBot


async def setup(bot):
    await bot.add_cog(VersionCommandBot(bot))
    await bot.add_cog(InfoCommandBot(bot))
    await bot.add_cog(AddRoleCommandBot(bot))
    await bot.add_cog(EventSessionLinkCommandBot(bot))
    await bot.add_cog(ServerStatusCommandBot(bot))
    await bot.add_cog(EventsCommandBot(bot))
    await bot.add_cog(EventDetailsCommandBot(bot))
