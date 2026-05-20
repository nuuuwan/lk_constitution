from dataclasses import dataclass


@dataclass
class LegislativeListItem:
    number: int
    subject: str
    description: str
