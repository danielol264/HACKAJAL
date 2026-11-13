from __future__ import annotations

from app.services import demo_data


class DashboardRepository:
    """Current local report source; replace internally with approved DRF calls later."""
    def load_snapshot(self) -> dict[str, object]:
        return {
            "metrics": demo_data.DASHBOARD_METRICS,
            "historical_confirmed": demo_data.HISTORICAL_CONFIRMED,
            "municipal_confirmed": demo_data.MUNICIPAL_CONFIRMED,
            "source_rows": demo_data.RECENT_ROWS,
            "alert_rows": demo_data.ALERT_ROWS,
            "follow_up_rows": demo_data.FOLLOW_UP_ROWS,
        }
