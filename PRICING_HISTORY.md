# Intercom Connector — Pricing History

Canonical policy: `/Users/vladivanco/Documents/Imperal OS/PRICING_POLICY.md`
(fixed scale `{0, 8, 16, 20, 40, 60}`, `pricing_model` explicit, `revenue_split_dev`
always passed explicitly to `update_pricing`).

---

## 2026-08-23 — Initial pricing, `per_action`, applied before `submit_for_review`

Applied per §1/§2 of `PRICING_POLICY.md`: pricing set only after a clean
`imperal validate .` (0 errors) and a successful `deploy_app` (20/21, only
the advisory "no file > 300 lines" warning — same class carried by
MuleSoft/Stripe/PagerDuty), and strictly before `submit_for_review`.

`revenue_split_dev=95` passed explicitly on the `update_pricing` call (the
value `create_app` itself returned for this account, partner tier) — per
the documented n8n/MuleSoft bug where omitting this parameter silently
fails to persist the price even though the call reports success. The
first `update_pricing` attempt in this session *did* hit that exact
failure mode (returned an explicit mismatch error listing every tool as
"not stored" and model as "free" instead of "per_action") — retried
immediately with the same explicit `revenue_split_dev=95` and it stored
correctly this time (full app JSON with `pricing_model: per_action`
echoed back, manifest's mirrored `pricing` block present). Re-ran
`deploy_app` afterward to sync that mirror into the live `imperal.json`.

**Free (connection lifecycle, standard across all connectors):**
- `connect_intercom`, `disconnect_intercom`, `list_connections` — 0

**8 tokens — simple list/get reads (no aggregation, one Intercom API call):**
`list_contacts`, `get_contact`, `list_contact_companies`, `list_companies`,
`get_company`, `list_company_contacts`, `list_conversations`,
`get_conversation`, `list_tickets`, `get_ticket`, `list_ticket_types`,
`list_ticket_states`, `list_articles`, `get_article`,
`list_help_center_collections`, `list_news_items`, `list_admins`,
`get_admin`, `list_teams`, `get_team`, `list_data_attributes`,
`get_data_export`, `list_away_status_reasons`, `list_tags`,
`list_segments`, `get_segment`, `list_subscription_types`,
`list_external_pages`, `list_content_import_sources`.

**16 tokens — standard writes (create/update/delete/attach/detach, one
Intercom API call each, real side effects in the customer's workspace):**
`create_contact`, `update_contact`, `delete_contact`,
`attach_tag_to_contact`, `detach_tag_from_contact`,
`attach_contact_to_company`, `detach_contact_from_company`,
`create_or_update_company`, `delete_company`, `search_conversations`
(heavier query semantics than a plain list, priced as a write-tier read),
`reply_conversation`, `manage_conversation`, `add_conversation_note`,
`create_ticket`, `update_ticket`, `reply_ticket`, `create_ticket_type`,
`create_article`, `update_article`, `delete_article`,
`create_help_center_collection`, `create_news_item`, `update_news_item`,
`delete_news_item`, `set_admin_away`, `create_data_attribute`,
`create_data_event`, `create_tag`, `delete_tag`,
`attach_contact_subscription`, `detach_contact_subscription`,
`create_external_page`, `update_external_page`, `delete_external_page`,
`create_message`.

**20 tokens — heavier/premium-surface operations (async job enqueue or
Intercom's own AI-agent surface, more expensive to Intercom and to us):**
`create_data_export`, `create_reporting_export`, `start_fin_conversation`,
`reply_to_fin`.

**40 tokens — aggregated value-add reports (many underlying Intercom API
calls fanned out into one synthesized answer):**
`audit_workspace_health`, `find_stale_conversations` — same tier as
PagerDuty Connector's `audit_account` / AppFolio Connector's
`audit_portfolio_health` precedent for this exact report shape.

No Google Cloud/Workspace markup applies (§5 of the policy) — Intercom is
not a Google-backed API.
