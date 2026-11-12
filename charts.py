"""График истории цены тура (для кнопки «📈 История цены»)."""
import io
from datetime import datetime


def _fmt_day(day: str) -> str:
    return datetime.strptime(day, "%Y-%m-%d").strftime("%d.%m")


def _title(info: dict) -> str:
    hotel = info["hotel"].split("(")[0].strip()
    if len(hotel) > 52:
        hotel = hotel[:51] + "…"
    dep = _fmt_day(info["dep"]) if info.get("dep") else "?"
    return f"{hotel}\nвылет {dep}, {info['nights']} ноч."


def price_caption(series: list, info: dict) -> str:
    prices = [p for _, p in series]
    first, last = prices[0], prices[-1]
    lo = min(series, key=lambda x: x[1])
    hi = max(series, key=lambda x: x[1])
    diff = last - first
    pct = diff / first * 100 if first else 0
    arrow = "📉" if diff < 0 else ("📈" if diff > 0 else "➖")
    hotel = info["hotel"].split("(")[0].strip()
    meal = f", {info['meal']}" if info.get("meal") else ""
    return (
        f"📈 <b>{hotel}</b>\n"
        f"Вылет {_fmt_day(info['dep'])}, {info['nights']} ноч.{meal}\n\n"
        f"Сейчас: <b>{last:.0f} €</b>\n"
        f"Минимум: {lo[1]:.0f} € ({_fmt_day(lo[0])}) · максимум: {hi[1]:.0f} € ({_fmt_day(hi[0])})\n"
        f"{arrow} С {_fmt_day(series[0][0])}: {diff:+.0f} € ({pct:+.0f}%)"
    )


def make_price_chart(series: list, info: dict) -> bytes:
    """PNG-график: цена по дням. series = [(YYYY-MM-DD, цена), ...]."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    days = [datetime.strptime(d, "%Y-%m-%d") for d, _ in series]
    prices = [p for _, p in series]
    lo_i = prices.index(min(prices))
    hi_i = prices.index(max(prices))

    fig, ax = plt.subplots(figsize=(8, 4.4), dpi=130)
    ax.plot(days, prices, color="#1a73e8", linewidth=2, marker="o", markersize=4, zorder=3)
    ax.fill_between(days, prices, min(prices) - (max(prices) - min(prices) or 10) * 0.25,
                    color="#1a73e8", alpha=0.08, zorder=1)
    ax.scatter([days[lo_i]], [prices[lo_i]], color="#1e8e3e", s=60, zorder=4)
    ax.annotate(f"мин {prices[lo_i]:.0f} €", (days[lo_i], prices[lo_i]), textcoords="offset points",
                xytext=(0, -16), ha="center", color="#1e8e3e", fontsize=9)
    if hi_i != lo_i:
        ax.scatter([days[hi_i]], [prices[hi_i]], color="#d93025", s=60, zorder=4)
        ax.annotate(f"макс {prices[hi_i]:.0f} €", (days[hi_i], prices[hi_i]), textcoords="offset points",
                    xytext=(0, 10), ha="center", color="#d93025", fontsize=9)
    ax.annotate(f"{prices[-1]:.0f} €", (days[-1], prices[-1]), textcoords="offset points",
                xytext=(8, 0), ha="left", va="center", fontsize=10, fontweight="bold")

    ax.set_title(_title(info), fontsize=11, loc="left")
    ax.set_ylabel("€ за 1 человека")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d.%m"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=8))
    ax.grid(True, alpha=0.25)
    ax.margins(x=0.06, y=0.18)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
