
from typing import Optional, Type

from .base import BaseAdapter
from .grafana import GrafanaAdapter
from .prometheus_webhook import PrometheusWebhookAdapter
from .custom_webhook import CustomWebhookAdapter
from .cloud_adapter import CloudAdapter

# A mapping of source names to adapter classes
ADAPTER_MAP = {
    "grafana": GrafanaAdapter,
    "prometheus": PrometheusWebhookAdapter,
    "custom_webhook": CustomWebhookAdapter,
    "cloud": CloudAdapter,
}

def get_adapter(source: str, token: Optional[str] = None) -> Optional[BaseAdapter]:
    """
    Factory function to get an adapter instance based on the source name.

    :param source: The name of the source system.
    :param token: An optional token for adapters that require it.
    :return: An instance of the appropriate adapter, or None if not found.
    """
    adapter_class: Type[BaseAdapter] = ADAPTER_MAP.get(source.lower())
    if adapter_class:
        # Pass the token to the adapter's constructor if it's provided
        return adapter_class(token=token)
    return None
