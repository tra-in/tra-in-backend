from pydantic import BaseModel
from typing import Optional, List


class RecommendRequest(BaseModel):
    from_name: str
    to_name: str
    deadline: str
    now: Optional[str] = None
    limit: int = 200
    topk: int = 10
    min_transfer_min: int = 15
    max_transfers: int = 2  # 1 or 2
