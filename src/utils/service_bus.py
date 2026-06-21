import json
import logging

from datetime import datetime
from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage

from models.planned_action import PlannedAction

logger = logging.getLogger("wattops.utils.service_bus")


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

                msg.scheduled_enqueue_time_utc = datetime.fromisoformat(
                    action.scheduled_at
                )

                sender.send_messages(msg)
