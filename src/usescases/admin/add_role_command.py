"""/add-role - grant a role to one member, or to everyone in the guild.

Two changes from the prefix-command version:
  * the role is a typed ROLE option, so it arrives as an id and no longer has
    to be matched by name;
  * `@all` became an explicit `everyone` boolean option, because a USER option
    cannot express "all of them".

The bulk path still runs one PUT per member against a single rate-limit
bucket, so the member cap from the original command is kept. Anything above it
belongs in a job, not in an interaction: the interaction token expires 15
minutes after the command is invoked.
"""

import logging
import os

from discord_api import interactions
from discord_api.rest import DiscordApiError, DiscordRest

from .permissions import require_admin

logger = logging.getLogger(__name__)

PROGRESS_EVERY = 250


async def handle(rest: DiscordRest, interaction: dict) -> None:
    guild_id = await require_admin(rest, interaction, 'add-role')
    if not guild_id:
        return

    options = interactions.options(interaction)
    role_id = options.get('role')
    target_user_id = options.get('user')
    everyone = bool(options.get('everyone', False))
    user_name = interactions.user_name(interaction)

    logger.debug('[COMMAND][ADD-ROLE] User "%s" requested role "%s" for user "%s" (everyone=%s)',
                 user_name, role_id, target_user_id, everyone)

    if not role_id:
        await rest.edit_original_response(interaction['token'], content='❌ Indica o role a adicionar.')
        return

    if everyone and target_user_id:
        await rest.edit_original_response(
            interaction['token'],
            content='❌ Escolhe `user` **ou** `everyone`, não ambos.')
        return

    if not everyone and not target_user_id:
        await rest.edit_original_response(
            interaction['token'],
            content='❌ Indica um `user`, ou ativa `everyone` para aplicar a todos os membros.')
        return

    roles = await rest.get_guild_roles(guild_id)
    role = next((r for r in roles if str(r['id']) == str(role_id)), None)
    if role is None:
        logger.warning('[COMMAND][ADD-ROLE] Role "%s" not found in guild "%s"', role_id, guild_id)
        await rest.edit_original_response(interaction['token'],
                                          content=f'❌ Role não encontrado: `{role_id}`.')
        return

    if not everyone:
        await _add_to_single_member(rest, interaction, guild_id, role, str(target_user_id), user_name)
        return

    await _add_to_everyone(rest, interaction, guild_id, role, user_name)


async def _add_to_single_member(rest: DiscordRest, interaction: dict, guild_id: str, role: dict,
                                user_id: str, requested_by: str) -> None:
    try:
        await rest.add_role(guild_id, user_id, role['id'])
    except DiscordApiError as error:
        logger.warning('[COMMAND][ADD-ROLE] Failed to add role "%s" to "%s": %s',
                       role['name'], user_id, error)
        await rest.edit_original_response(
            interaction['token'],
            content=f'❌ Não foi possível adicionar o role "{role["name"]}" a <@{user_id}> '
                    f'(HTTP {error.status}).')
        return

    logger.info('[COMMAND][ADD-ROLE] Added role "%s" to "%s" (by "%s")',
                role['name'], user_id, requested_by)
    await rest.edit_original_response(
        interaction['token'],
        content=f'✅ Role "{role["name"]}" adicionado a <@{user_id}>.')


async def _add_to_everyone(rest: DiscordRest, interaction: dict, guild_id: str, role: dict,
                           requested_by: str) -> None:
    max_members = int(os.environ.get('ADD_ROLE_ALL_MAX_MEMBERS', '3000'))

    members = [member async for member in rest.iter_members(guild_id)]
    if len(members) > max_members:
        logger.warning('[COMMAND][ADD-ROLE] everyone request in guild "%s" aborted: %s members '
                       'exceeds cap of %s', guild_id, len(members), max_members)
        await rest.edit_original_response(
            interaction['token'],
            content=f'⚠️ Operação cancelada para todos os membros '
                    f'({len(members)} utilizador(es), limite {max_members}).')
        return

    await rest.edit_original_response(
        interaction['token'],
        content=f'⏳ A adicionar o role "{role["name"]}" a {len(members)} utilizador(es)...')

    added = 0
    skipped = 0
    failed = 0
    for index, member in enumerate(members, start=1):
        user = member.get('user', {})
        if user.get('bot'):
            skipped += 1
            continue
        if str(role['id']) in [str(r) for r in member.get('roles', [])]:
            skipped += 1
            continue
        try:
            await rest.add_role(guild_id, user['id'], role['id'])
            added += 1
        except DiscordApiError as error:
            failed += 1
            logger.warning('[COMMAND][ADD-ROLE] Failed to add role "%s" to "%s": %s',
                           role['name'], user.get('id'), error)

        if index % PROGRESS_EVERY == 0:
            await rest.create_followup(
                interaction['token'],
                content=f'⏳ {index}/{len(members)} processados...')

    logger.info('[COMMAND][ADD-ROLE] Role "%s" bulk-applied by "%s": %s added, %s skipped, %s failed',
                role['name'], requested_by, added, skipped, failed)
    await rest.create_followup(
        interaction['token'],
        content=f'✅ Role "{role["name"]}": {added} adicionados, {skipped} ignorados, {failed} falhas.')
