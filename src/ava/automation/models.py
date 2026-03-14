from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum


class AutomationStrategy(StrEnum):
    UI_AUTOMATION = "ui_automation"
    INPUT_SIMULATION = "input_simulation"
    DOM_AUTOMATION = "dom_automation"
    VISUAL_FALLBACK = "visual_fallback"


@dataclass(slots=True)
class BrowserPlan:
    uses_live_session: bool
    uses_isolated_session: bool
    browser_name: str
    strategy: AutomationStrategy
    reason: str

    def as_dict(self) -> dict[str, str | bool]:
        return asdict(self)

    def describe(self) -> str:
        if self.uses_isolated_session:
            return f"Isolated {self.browser_name.title()} test session use karenge."
        if self.uses_live_session:
            return f"Live {self.browser_name.title()} session mil gaya. Usko control karenge."
        return (
            "Live browser session nahi mila. "
            f"{self.browser_name.title()} profile open karna padega."
        )
