"""ROI projection engine — multi-year deterministic growth.

Builds the 5-year projection (Screens 4/5/8) from the configured onboarding ramp
(default apps: 25, 100, 200, 400, 600 across years 1-5) and the core calculator.
Cumulative savings are accumulated year over year.
"""

from __future__ import annotations

from app.roi.assumptions import Assumptions
from app.roi.calculations import calculate_projected, projected_inputs_for_apps
from app.roi.models import Projection, ProjectionPoint, format_inr


def build_projection(a: Assumptions, *, apps_schedule: list[int] | None = None,
                     years: list[int] | None = None) -> Projection:
    """Build a multi-year projection. Never raises."""
    try:
        apps_list = [int(x) for x in (apps_schedule or a.projection_apps)]
        year_list = list(years or a.projection_years)
        # Pad/truncate year labels to match app schedule length.
        if len(year_list) < len(apps_list):
            year_list = list(range(1, len(apps_list) + 1))
        else:
            year_list = year_list[:len(apps_list)]

        points: list[ProjectionPoint] = []
        cumulative = 0.0
        total_hours = 0.0
        peak_fte = 0.0
        for year, apps in zip(year_list, apps_list):
            res = calculate_projected(apps, a)
            inp = projected_inputs_for_apps(apps, a)
            cumulative += res.cost_savings
            total_hours += res.hours_saved
            peak_fte = max(peak_fte, res.fte_equivalent)
            obs_reduced = inp.observations_closed + inp.observations_prevented
            points.append(ProjectionPoint(
                year=int(year), applications=apps,
                hours_saved=res.hours_saved, cost_savings=res.cost_savings,
                fte_equivalent=res.fte_equivalent,
                observations_reduced=round(obs_reduced, 1), roi_pct=res.roi_pct,
                cumulative_cost_savings=round(cumulative, 0),
                cost_savings_display=res.cost_savings_display,
                cumulative_display=format_inr(cumulative, symbol=a.symbol,
                                              lakh=a.lakh, crore=a.crore),
            ))

        return Projection(
            enabled=True, points=points,
            total_cost_savings=round(cumulative, 0),
            total_hours_saved=round(total_hours, 1), peak_fte=round(peak_fte, 2),
            total_display=format_inr(cumulative, symbol=a.symbol, lakh=a.lakh,
                                     crore=a.crore),
        )
    except Exception as exc:  # noqa: BLE001 - fail safe
        return Projection(enabled=False,
                          note=f"projection error (ignored): {type(exc).__name__}")
