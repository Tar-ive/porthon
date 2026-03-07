"""Worker implementations for always-on runtime."""

from deepagent.workers.calendar_worker import CalendarWorker
from deepagent.workers.facebook_worker import FacebookWorker
from deepagent.workers.figma_worker import FigmaWorker
from deepagent.workers.kg_worker import KgWorker
from deepagent.workers.notion_leads_worker import NotionLeadsWorker
from deepagent.workers.notion_opportunity_worker import NotionOpportunityWorker


def build_workers() -> dict:
    workers = [
        KgWorker(),
        CalendarWorker(),
        NotionLeadsWorker(),
        NotionOpportunityWorker(),
        FacebookWorker(),
        FigmaWorker(),
    ]
    return {w.worker_id: w for w in workers}
