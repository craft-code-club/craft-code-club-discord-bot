"""Small key/value state table, backed by the same storage account.

The gateway bot kept its state in the process (a `tasks.loop` only ticks while
the process lives, and `on_member_join` fired in real time). Timer-triggered
functions have no memory between runs, so the few pieces of state they need -
currently just the new-member watermark - live in a `BotState` table alongside
the existing `CommunityEvents` table.
"""

import logging
import os
from functools import lru_cache
from typing import Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TableServiceClient

logger = logging.getLogger(__name__)

TABLE_NAME = 'BotState'
PARTITION_KEY = 'state'

# Well-known keys.
LAST_SYNC_KEY = 'last_community_events_sync'
LAST_NOTIFY_KEY = 'last_notify_run'


class StateDao:
    def __init__(self):
        connection_string = os.environ.get('AZURE_STORAGE_CONNECTION_STRING')
        if not connection_string:
            raise RuntimeError('AZURE_STORAGE_CONNECTION_STRING is not set')

        connection = TableServiceClient.from_connection_string(connection_string)
        connection.create_table_if_not_exists(TABLE_NAME)
        self.table = connection.get_table_client(TABLE_NAME)

    def get(self, key: str) -> Optional[str]:
        try:
            entity = self.table.get_entity(partition_key=PARTITION_KEY, row_key=key)
        except ResourceNotFoundError:
            return None
        value = entity.get('value')
        return str(value) if value is not None else None

    def set(self, key: str, value: str) -> None:
        self.table.upsert_entity(entity={
            'PartitionKey': PARTITION_KEY,
            'RowKey': key,
            'value': value,
        })


@lru_cache(maxsize=1)
def get_state_dao() -> StateDao:
    """Build the DAO on first use.

    Never at import time: a function worker imports every module while indexing
    triggers, and a storage outage at that moment would fail the whole app
    rather than the one invocation that actually needs the table.
    """
    return StateDao()
