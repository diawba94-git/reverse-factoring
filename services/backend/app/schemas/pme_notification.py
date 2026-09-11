from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class NotificationPmeOut(BaseModel):
    type: Literal["validation", "financement", "litige", "acheteur", "kyc", "invitation"]
    titre: str
    description: str
    date: datetime
    lu: bool
