"""Customer models."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class CustomerContext(BaseModel):
    """360-degree customer snapshot."""

    customer_id: str
    external_id: str
    name: str
    email: str
    company: Optional[str]
    tier: str
    lifetime_value: float

    total_orders: int
    recent_orders: List[dict]
    open_tickets: int
    avg_sentiment: float
    last_interaction: Optional[datetime]

    is_high_value: bool
    churn_risk: str
