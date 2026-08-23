"""Entrypoint for the web-kernel and CLI tools (imperal validate/build).

Sets up sys.path, purges stale module cache, then imports ext/chat and all
handler modules so their decorators register on the same Extension instance
-- same pattern as PagerDuty Connector's / MuleSoft Connector's main.py.
"""

import os
import sys

_EXT_DIR = os.path.dirname(os.path.abspath(__file__))
if _EXT_DIR not in sys.path:
    sys.path.insert(0, _EXT_DIR)

_LOCAL = (
    "app", "schemas", "intercom_client",
    "handlers_connection", "handlers_contacts", "handlers_companies",
    "handlers_conversations", "handlers_tickets", "handlers_content",
    "handlers_admin", "handlers_data", "handlers_tags_segments",
    "handlers_fin", "handlers_messages", "handlers_audit",
    "panels", "panels_settings",
)
for _mod in _LOCAL:
    sys.modules.pop(_mod, None)

from app import ext, chat  # noqa: E402,F401
import handlers_connection  # noqa: E402,F401
import handlers_contacts  # noqa: E402,F401
import handlers_companies  # noqa: E402,F401
import handlers_conversations  # noqa: E402,F401
import handlers_tickets  # noqa: E402,F401
import handlers_content  # noqa: E402,F401
import handlers_admin  # noqa: E402,F401
import handlers_data  # noqa: E402,F401
import handlers_tags_segments  # noqa: E402,F401
import handlers_fin  # noqa: E402,F401
import handlers_messages  # noqa: E402,F401
import handlers_audit  # noqa: E402,F401
import panels  # noqa: E402,F401
import panels_settings  # noqa: E402,F401
