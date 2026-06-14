from datetime import datetime, timezone
import json
import logging

from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage

from models.planned_action import PlannedAction
from utils.config import Settings

logger = logging.getLogger("wattops.utils.service_bus")


def parse_iso_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def publish_scheduled_actions(
    actions: list[PlannedAction], service_bus_namespace: str, queue_name: str
) -> None:
    credential = DefaultAzureCredential()

    with ServiceBusClient(
        fully_qualified_namespace=service_bus_namespace,
        credential=credential,
    ) as client:
        with client.get_queue_sender(queue_name=queue_name) as sender:
            for action in actions:
                msg = ServiceBusMessage(json.dumps(action.to_message()))

                scheduled_for = parse_iso_utc(action.window.start)
                msg.scheduled_enqueue_time_utc = scheduled_for

                sender.send_messages(msg)
