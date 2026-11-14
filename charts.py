"""График истории цены тура (для кнопки «📈 История цены»)."""
import io
from datetime import datetime, timedelta


def _fmt_day(day: str) -> str:
    return datetime.strptime(day, "%Y-%m-%d").strftime("%d.%m")


def _title(info: dict) -> str:
    hotel = info["hotel"].split("(")[0].strip()
    if len(hotel) > 52:
        hotel = hotel[:51] + "…"
    dep = _fmt_day(info["dep"]) if info.get("dep") else "?"
    return f"{hotel}\nвылет {dep}, {info['nights']} ноч."


BG = "#121212"        # фон
GRID = "#2b2b2b"
TEXT = "#c9c9c9"
GREEN = "#62a817"     # минимальная цена
GREY = "#7d7d7d"      # средняя цена


def _style(fig, ax, mode: str = "day"):
    """Тёмная тема: чёрный фон, тонкая сетка, светлые подписи."""
    import matplotlib.dates as mdates
    from matplotlib.ticker import FuncFormatter
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#4a4a4a")
    ax.tick_params(colors=TEXT, labelsize=9)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f} €".replace(",", " ")))
    fmt = "%Y.%m" if mode == "month" else "%d.%m"
    ax.xaxis.set_major_formatter(mdates.DateFormatter(fmt))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=9))
    for lab in ax.get_xticklabels():
        lab.set_rotation(45)
        lab.set_ha("right")


def _legend(ax):
    leg = ax.legend(loc="upper right", fontsize=9, frameon=False, labelcolor=TEXT, handlelength=1.2)
    return leg


def _save(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=fig.get_facecolor())
    import matplotlib.pyplot as plt
    plt.close(fig)
    return buf.getvalue()


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
    """PNG-график: цена тура по дням. series = [(YYYY-MM-DD, цена), ...]."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    days = [datetime.strptime(d, "%Y-%m-%d") for d, _ in series]
    prices = [p for _, p in series]
    lo_i, hi_i = prices.index(min(prices)), prices.index(max(prices))

    fig, ax = plt.subplots(figsize=(9, 4.4), dpi=140)
    ax.plot(days, prices, color=GREEN, linewidth=2.2, marker="o", markersize=7, label="цена тура", zorder=3)
    ax.annotate(f"мин {prices[lo_i]:.0f} €", (days[lo_i], prices[lo_i]), textcoords="offset points",
                xytext=(0, -18), ha="center", color=GREEN, fontsize=9)
    if hi_i != lo_i:
        ax.annotate(f"макс {prices[hi_i]:.0f} €", (days[hi_i], prices[hi_i]), textcoords="offset points",
                    xytext=(0, 12), ha="center", color="#e06666", fontsize=9)
    ax.annotate(f"{prices[-1]:.0f} €", (days[-1], prices[-1]), textcoords="offset points",
                xytext=(10, 0), ha="left", va="center", fontsize=10, fontweight="bold", color="#ffffff")
    ax.set_title(_title(info), fontsize=10, loc="left", color=TEXT)
    ax.margins(x=0.08, y=0.22)
    _style(fig, ax, "day")
    _legend(ax)
    fig.tight_layout()
    return _save(fig)


# ───────────────────── общий график цен ─────────────────────

MODES = {"day": "по дням", "week": "по неделям", "month": "по месяцам"}


def _period_key(day: str, mode: str) -> str:
    dt = datetime.strptime(day, "%Y-%m-%d")
    if mode == "week":
        return (dt - timedelta(days=dt.weekday())).strftime("%Y-%m-%d")   # понедельник недели
    if mode == "month":
        return dt.strftime("%Y-%m-01")
    return day


def aggregate(daily: list, mode: str, fields: tuple, how: str = "mean") -> list:
    """Склеивает дневные значения в недели/месяцы (среднее или минимум). Для «по дням» берёт последние 30 дней."""
    if not daily:
        return []
    if mode == "day":
        last = datetime.strptime(daily[-1]["day"], "%Y-%m-%d")
        daily = [d for d in daily if datetime.strptime(d["day"], "%Y-%m-%d") >= last - timedelta(days=30)]
    elif mode == "week":
        last = datetime.strptime(daily[-1]["day"], "%Y-%m-%d")
        daily = [d for d in daily if datetime.strptime(d["day"], "%Y-%m-%d") >= last - timedelta(days=182)]
    groups = {}
    for d in daily:
        groups.setdefault(_period_key(d["day"], mode), []).append(d)
    out = []
    for key in sorted(groups):
        g = groups[key]
        row = {"day": key}
        for f in fields:
            vals = [x[f] for x in g]
            h = how.get(f, "mean") if isinstance(how, dict) else how
            row[f] = min(vals) if h == "min" else sum(vals) / len(vals)
        out.append(row)
    return out


def overall_caption(daily: list, old: list, mode: str) -> str:
    head = "📈 <b>Цены на туры</b> (при двух в номере)\n"
    if not daily:
        return head + "Пока данных нет."
    now = daily[-1]
    text = (head + f"Сейчас ({_fmt_day(now['day'])}): минимальная <b>{now['min']:.0f} €</b> · "
                   f"средняя <b>{now['avg']:.0f} €</b>")
    how = {"min": "min", "avg": "mean"}
    agg = aggregate(daily, mode, ("min", "avg"), how=how)
    if len(agg) >= 2:
        for key, label in (("min", "Минимальная"), ("avg", "Средняя")):
            diff = agg[-1][key] - agg[0][key]
            pct = diff / agg[0][key] * 100 if agg[0][key] else 0
            arrow = "📉" if diff < 0 else ("📈" if diff > 0 else "➖")
            text += f"\n{arrow} {label} с {_fmt_day(agg[0]['day'])}: {diff:+.0f} € ({pct:+.0f}%)"
    else:
        text += "\n\nИстория копится с 12.11, линии по дням появятся завтра."
    return text


def make_overall_chart(daily: list, old: list, mode: str = "day") -> bytes:
    """Тёмный график: средняя (серая) и минимальная (зелёная) цена по дням / неделям / месяцам."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    agg = aggregate(daily, mode, ("min", "avg"), how={"min": "min", "avg": "mean"})
    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=140)
    if agg:
        xs = [datetime.strptime(m["day"], "%Y-%m-%d") for m in agg]
        ax.plot(xs, [m["avg"] for m in agg], color=GREY, linewidth=2.2, marker="o", markersize=7,
                label="средняя цена", zorder=2)
        ax.plot(xs, [m["min"] for m in agg], color=GREEN, linewidth=2.2, marker="o", markersize=7,
                label="минимальная цена", zorder=3)
        ax.annotate(f"{agg[-1]['avg']:.0f} €", (xs[-1], agg[-1]["avg"]), textcoords="offset points",
                    xytext=(10, 0), ha="left", va="center", fontsize=9, color="#dddddd")
        ax.annotate(f"{agg[-1]['min']:.0f} €", (xs[-1], agg[-1]["min"]), textcoords="offset points",
                    xytext=(10, 0), ha="left", va="center", fontsize=9, color=GREEN)
    ax.margins(x=0.1, y=0.18)
    _style(fig, ax, mode)
    _legend(ax)
    fig.tight_layout()
    return _save(fig)
