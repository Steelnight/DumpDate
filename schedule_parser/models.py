from dataclasses import dataclass
import hashlib

@dataclass
class WasteEvent:
    uid: str
    date: str
    location: str
    waste_type: str
    contact_name: str
    contact_phone: str

    def compute_hash(self) -> str:
        """Compute SHA256 hash ignoring UID."""
        raw = f"{self.date}|{self.location}|{self.waste_type}|{self.contact_name}|{self.contact_phone}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
