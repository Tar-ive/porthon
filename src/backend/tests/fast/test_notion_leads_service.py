from __future__ import annotations

import pytest

from integrations.notion_leads_service import NotionLeadsService


@pytest.mark.fast
def test_row_to_lead_supports_status_and_property_id_keys():
    service = NotionLeadsService(token="test_token")
    row = {
        "id": "page_123",
        "properties": {
            "title_prop_id": {
                "id": "title_prop_id",
                "name": "Name",
                "type": "title",
                "title": [{"plain_text": "Theo Referral Lead"}],
            },
            "status_prop_id": {
                "id": "status_prop_id",
                "name": "Status",
                "type": "status",
                "status": {"name": "Contacted"},
            },
            "lead_type_id": {
                "id": "lead_type_id",
                "name": "Lead type",
                "type": "select",
                "select": {"name": "Referral"},
            },
            "priority_id": {
                "id": "priority_id",
                "name": "Priority",
                "type": "select",
                "select": {"name": "High"},
            },
            "deal_size_id": {
                "id": "deal_size_id",
                "name": "Deal size",
                "type": "formula",
                "formula": {"type": "number", "number": 3200},
            },
            "source_id": {
                "id": "source_id",
                "name": "Source",
                "type": "rich_text",
                "rich_text": [{"plain_text": "Referral"}],
            },
            "lead_key_id": {
                "id": "lead_key_id",
                "name": "Lead Key",
                "type": "rich_text",
                "rich_text": [{"plain_text": "theo referral lead::referral"}],
            },
        },
    }

    lead = service.row_to_lead(row)

    assert lead["name"] == "Theo Referral Lead"
    assert lead["status"] == "Contacted"
    assert lead["lead_type"] == "Referral"
    assert lead["priority"] == "High"
    assert lead["deal_size"] == 3200
    assert lead["source"] == "Referral"
    assert lead["lead_key"] == "theo referral lead::referral"
    assert lead["page_id"] == "page_123"


@pytest.mark.fast
def test_row_to_lead_falls_back_when_source_or_key_missing():
    service = NotionLeadsService(token="test_token")
    row = {
        "id": "page_456",
        "properties": {
            "Name": {"title": [{"plain_text": "Untyped Lead"}]},
            "Status": {"status": {"name": "Lead"}},
        },
    }

    lead = service.row_to_lead(row)
    assert lead["name"] == "Untyped Lead"
    assert lead["status"] == "Lead"
    assert lead["source"] == "Unknown"
    assert lead["lead_key"] == "untyped lead::unknown"


@pytest.mark.fast
def test_lead_to_properties_supports_status_type():
    service = NotionLeadsService(token="test_token")
    lead = {
        "name": "Status Type Lead",
        "status": "Proposal sent",
        "lead_type": "Inbound",
        "priority": "Medium",
        "deal_size": 1000,
        "last_contact": None,
        "next_action": "",
        "next_follow_up_date": None,
        "email_handle": "",
        "source": "Inbound",
        "notes": "",
        "lead_key": "status type lead::inbound",
    }

    props_status = service._lead_to_properties(lead, status_kind="status")
    assert props_status["Status"] == {"status": {"name": "Proposal sent"}}

    props_select = service._lead_to_properties(lead, status_kind="select")
    assert props_select["Status"] == {"select": {"name": "Proposal sent"}}
