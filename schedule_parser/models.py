"""
This module defines the data models for the waste schedule parser.
"""
import hashlib
from dataclasses import dataclass


@dataclass
class WasteEvent:
    """Represents a single waste collection event."""

    uid: str
    date: str
    location: str
    waste_type: str
    contact_name: str
    contact_phone: str
    original_address: str

    def compute_hash(self) -> str:
        """Compute SHA256 hash ignoring UID."""
        raw = f"{self.date}|{self.location}|{self.waste_type}|{self.contact_name}|{self.contact_phone}|{self.original_address}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
