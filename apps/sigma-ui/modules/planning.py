import uuid
from typing import Any

from sigmac3_sdk.geo import GPSposition


def gen_blankmission() -> dict[str, Any]:
    """Create an empty mission scaffold for the planner UI."""
    return {
        "mission_uid": str(uuid.uuid4()),
        "mission_type": None,
        "home_pos": None,
        "land_pos": None,
        "points": {
            "route_in": [],
            "survey": [],
            "route_out": [],
        },
        "n_points": {"route_in": 0, "survey": 0, "route_out": 0},
        "route_in": [],
        "survey": [],
        "route_out": [],
    }


def plan_mission(mission: dict[str, Any]) -> dict[str, Any]:
    """Mark the mission as planned; keep data in sync."""
    required = ("mission_uid", "points", "route_in", "survey", "route_out")
    for key in required:
        if key not in mission:
            raise RuntimeError(f"Mission is missing required field {key}")

    mission["route_in"] = mission["points"]["route_in"]
    mission["survey"] = mission["points"]["survey"]
    mission["route_out"] = mission["points"]["route_out"]
    mission["planned"] = True
    return mission


def render_opplan(mission: dict[str, Any]) -> str:
    """Render a minimal HTML OPPLAN summary for the planner result view."""
    uid = mission.get("mission_uid", "")
    route_in = mission.get("route_in") or []
    survey = mission.get("survey") or []
    route_out = mission.get("route_out") or []
    home = mission.get("home_pos")
    land = mission.get("land_pos")

    def _fmt_pos(pos: GPSposition | None) -> str:
        if not pos:
            return "N/A"
        return f"{pos.lat:.6f}, {pos.lon:.6f}"

    def _fmt_points(points: list[dict[str, Any]]) -> str:
        return "".join(
            f"<li>{p.get('point_type','')} {p.get('num','')}: "
            f"{_fmt_pos(p.get('pos'))}</li>"
            for p in points
        )

    return f"""
<html>
<head><title>Mission {uid}</title></head>
<body>
  <h1>Mission {uid}</h1>
  <p><strong>Home:</strong> {_fmt_pos(home)}<br/>
     <strong>Land:</strong> {_fmt_pos(land)}</p>
  <h2>Ingress</h2>
  <ul>{_fmt_points(route_in)}</ul>
  <h2>Survey</h2>
  <ul>{_fmt_points(survey)}</ul>
  <h2>Egress</h2>
  <ul>{_fmt_points(route_out)}</ul>
</body>
</html>
""".strip()
