"""Matplotlib charts integrated into the HACKAJAL PySide6 interface."""
from __future__ import annotations

import math
from typing import Any

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

MONTH_NAMES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


class EmptyTrendChart(FigureCanvas):
    """An intentionally data-free chart until validated API data is available."""

    def __init__(self, message: str = "Sin datos epidemiológicos validados", submessage: str = "La evolución se mostrará al conectar la API institucional.") -> None:
        figure = Figure(figsize=(5, 2.7), tight_layout=True)
        super().__init__(figure)
        axis = figure.add_subplot(111)
        axis.set_facecolor("#FFFFFF")
        figure.patch.set_facecolor("#FFFFFF")
        axis.text(0.5, 0.56, message, ha="center", va="center", color="#17313B", fontsize=11, weight="bold")
        axis.text(0.5, 0.40, submessage, ha="center", va="center", color="#687A82", fontsize=9)
        axis.set_xticks([])
        axis.set_yticks([])
        for spine in axis.spines.values():
            spine.set_visible(False)


class HistoricalTrendChart(FigureCanvas):
    """Historical confirmed cases plus a forecast area placeholder."""

    def __init__(self, points: list[tuple[int, int]]) -> None:
        figure = Figure(figsize=(5, 2.7), tight_layout=True)
        super().__init__(figure)
        axis = figure.add_subplot(111)
        figure.patch.set_facecolor("#FFFFFF")
        axis.set_facecolor("#FFFFFF")
        if points:
            years, values = zip(*points)
            axis.plot(years, values, color="#123B4A", linewidth=2.4, marker="o", markersize=5, label="Confirmados históricos")
            axis.axvspan(2026.1, 2026.85, color="#EEF2F4", zorder=0)
            axis.text(2026.47, max(values) * 0.70, "Predicción\npendiente", ha="center", va="center", color="#687A82", fontsize=8)
            axis.set_xticks(years)
            axis.set_xticklabels([str(year) for year in years], fontsize=8)
            axis.tick_params(axis="y", labelsize=8, colors="#687A82")
            axis.grid(axis="y", color="#E7ECEE", linewidth=0.8)
            axis.spines[["top", "right", "left"]].set_visible(False)
            axis.spines["bottom"].set_color("#DDE6E9")
            axis.legend(frameon=False, loc="upper left", fontsize=8)


class MunicipalDistributionChart(FigureCanvas):
    def __init__(self, points: list[tuple[str, int]]) -> None:
        figure = Figure(figsize=(5, 2.1), tight_layout=True)
        super().__init__(figure)
        axis = figure.add_subplot(111)
        figure.patch.set_facecolor("#FFFFFF")
        axis.set_facecolor("#FFFFFF")
        if points:
            names, values = zip(*points)
            labels = [name.replace("Cuautitlán de García Barragán", "Cuautitlán G. B.") for name in names]
            bars = axis.barh(labels[::-1], values[::-1], color="#1B4E81")
            axis.bar_label(bars, labels=[f"{value:,}" for value in values[::-1]], padding=3, fontsize=8, color="#17313B")
            axis.set_xlim(0, max(values) * 1.18)
            axis.set_xticks([])
            axis.tick_params(axis="y", labelsize=8, colors="#405860", length=0)
            for spine in axis.spines.values():
                spine.set_visible(False)


class EpidemiologicalTrendChart(FigureCanvas):
    """Monthly registered cases chart complying with API_ESCRITORIO.md.
    
    IMPORTANT: Unrecorded months are NOT represented as zero.
    Gaps indicate missing periods, and recorded months show markers and case counts.
    """

    def __init__(self, casos_por_mes: list[dict[str, Any]] | None, anio: int) -> None:
        figure = Figure(figsize=(6, 3.2), tight_layout=True)
        super().__init__(figure)
        figure.patch.set_facecolor("#FFFFFF")
        axis = figure.add_subplot(111)
        axis.set_facecolor("#FFFFFF")

        # Map available months (1..12)
        cases_by_month: dict[int, int] = {}
        if casos_por_mes:
            for item in casos_por_mes:
                m = item.get("mes")
                c = item.get("casos")
                if m is not None and c is not None:
                    cases_by_month[int(m)] = int(c)

        if not cases_by_month:
            axis.text(0.5, 0.55, f"Sin casos registrados para el año {anio}", ha="center", va="center", color="#123B4A", fontsize=11, weight="bold")
            axis.text(0.5, 0.42, "No se encontraron expedientes con fecha en este periodo.", ha="center", va="center", color="#647C8C", fontsize=9)
            axis.set_xticks([])
            axis.set_yticks([])
            for spine in axis.spines.values():
                spine.set_visible(False)
            return

        months = list(range(1, 13))
        # Build series with float('nan') for missing months (prevents plotting as zero)
        y_values = [cases_by_month.get(m, float("nan")) for m in months]

        # Filter points where data exists for markers and text annotations
        valid_months = [m for m in months if not math.isnan(y_values[m - 1])]
        valid_values = [y_values[m - 1] for m in valid_months]

        # Plot line connecting measured consecutive points (nan breaks the line naturally)
        axis.plot(months, y_values, color="#123B4A", linewidth=2.5, linestyle="-", label=f"Casos {anio}", zorder=3)
        # Plot distinctive turquoise markers on measured points
        axis.scatter(valid_months, valid_values, color="#028090", edgecolor="#FFFFFF", s=55, linewidth=1.5, zorder=4)

        # Annotate points with values
        max_val = max(valid_values) if valid_values else 10
        for m, val in zip(valid_months, valid_values):
            axis.annotate(
                f"{int(val):,}",
                (m, val),
                textcoords="offset points",
                xytext=(0, 7),
                ha="center",
                fontsize=8,
                fontweight="600",
                color="#123B4A",
            )

        # Highlight months without data with subtle tick styling or note
        missing_months = [m for m in months if m not in cases_by_month]
        if missing_months:
            # Subtle note at top
            axis.set_title(
                f"Evolución mensual {anio} ({len(valid_months)} de 12 meses registrados · Meses sin dato omitidos)",
                fontsize=9,
                color="#647C8C",
                loc="left",
                pad=10,
            )
        else:
            axis.set_title(f"Evolución mensual {anio} (Todos los meses registrados)", fontsize=9, color="#647C8C", loc="left", pad=10)

        axis.set_xticks(months)
        axis.set_xticklabels(MONTH_NAMES, fontsize=8.5, color="#183447")
        axis.set_ylim(0, max_val * 1.25 if max_val > 0 else 10)
        axis.tick_params(axis="y", labelsize=8, colors="#647C8C")
        axis.grid(axis="y", color="#EAF0F5", linestyle="--", linewidth=0.8, zorder=1)
        axis.spines[["top", "right", "left"]].set_visible(False)
        axis.spines["bottom"].set_color("#CBD5E1")


class ClimateEvolutionChart(FigureCanvas):
    """Monthly climate evolution (Temperature, Humidity, Precipitation).
    
    Uses dual-axis:
    - Left Y: Temperatura (°C) and Humedad (%)
    - Right Y: Precipitación (mm)
    """

    def __init__(self, clima_por_mes: list[dict[str, Any]] | None, anio: int) -> None:
        figure = Figure(figsize=(6, 3.2), tight_layout=True)
        super().__init__(figure)
        figure.patch.set_facecolor("#FFFFFF")
        ax1 = figure.add_subplot(111)
        ax1.set_facecolor("#FFFFFF")

        climate_by_month: dict[int, dict[str, Any]] = {}
        if clima_por_mes:
            for item in clima_por_mes:
                m = item.get("mes")
                if m is not None:
                    climate_by_month[int(m)] = item

        months = list(range(1, 13))
        temps = [climate_by_month.get(m, {}).get("temperatura") for m in months]
        hums = [climate_by_month.get(m, {}).get("humedad") for m in months]
        precs = [climate_by_month.get(m, {}).get("precipitacion") for m in months]

        # Convert None to NaN so Matplotlib doesn't draw zero for missing data
        t_clean = [float("nan") if v is None else float(v) for v in temps]
        h_clean = [float("nan") if v is None else float(v) for v in hums]
        p_clean = [0.0 if v is None else float(v) for v in precs]

        has_data = any(not math.isnan(x) for x in t_clean) or any(not math.isnan(x) for x in h_clean) or any(v is not None for v in precs)

        if not has_data:
            ax1.text(0.5, 0.55, f"Sin mediciones meteorológicas para el año {anio}", ha="center", va="center", color="#123B4A", fontsize=11, weight="bold")
            ax1.text(0.5, 0.42, "No hay datos de temperatura, humedad o lluvia en este corte.", ha="center", va="center", color="#647C8C", fontsize=9)
            ax1.set_xticks([])
            ax1.set_yticks([])
            for spine in ax1.spines.values():
                spine.set_visible(False)
            return

        # Right axis for precipitation bars
        ax2 = ax1.twinx()
        ax2.set_facecolor("none")

        # Bars for precipitation
        valid_p_months = [m for m, v in enumerate(precs, start=1) if v is not None]
        valid_p_values = [float(precs[m - 1]) for m in valid_p_months]
        if valid_p_values:
            ax2.bar(valid_p_months, valid_p_values, width=0.45, color="#A7D7C5", alpha=0.55, label="Precipitación (mm)", zorder=2)
            max_p = max(valid_p_values)
            ax2.set_ylim(0, max_p * 1.5 if max_p > 0 else 50)
            ax2.tick_params(axis="y", labelsize=8, colors="#3B7A57")
            ax2.set_ylabel("Lluvia (mm)", fontsize=8, color="#3B7A57")
        else:
            ax2.set_yticks([])

        # Lines for Temperature and Humidity on ax1
        t_valid_m = [m for m, v in enumerate(t_clean, start=1) if not math.isnan(v)]
        t_valid_y = [t_clean[m - 1] for m in t_valid_m]
        if t_valid_m:
            ax1.plot(t_valid_m, t_valid_y, color="#C47A27", linewidth=2.0, marker="s", markersize=4, label="Temp. (°C)", zorder=4)

        h_valid_m = [m for m, v in enumerate(h_clean, start=1) if not math.isnan(v)]
        h_valid_y = [h_clean[m - 1] for m in h_valid_m]
        if h_valid_m:
            ax1.plot(h_valid_m, h_valid_y, color="#028090", linewidth=2.0, marker="o", markersize=4, linestyle="--", label="Humedad (%)", zorder=4)

        ax1.set_xticks(months)
        ax1.set_xticklabels(MONTH_NAMES, fontsize=8.5, color="#183447")
        ax1.set_ylim(0, 105)
        ax1.set_ylabel("Temp (°C) / Hum (%)", fontsize=8, color="#647C8C")
        ax1.tick_params(axis="y", labelsize=8, colors="#647C8C")
        ax1.grid(axis="y", color="#EAF0F5", linestyle=":", linewidth=0.8, zorder=1)

        ax1.spines[["top", "left"]].set_visible(False)
        ax1.spines["bottom"].set_color("#CBD5E1")
        ax2.spines[["top", "left", "bottom"]].set_visible(False)
        ax2.spines["right"].set_color("#CBD5E1")

        # Unified legend
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        if lines1 or lines2:
            ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", frameon=True, facecolor="#FFFFFF", edgecolor="#CBD5E1", fontsize=7.5)
