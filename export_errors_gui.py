"""GUI for exporting FreeLLMAPI errors with filter selection."""
import re
import sqlite3
import subprocess
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk, messagebox

DB_PATH = Path(r"C:\Users\aminm\AppData\Roaming\FreeLLMAPI\freeapi.db")
OUTPUT_PATH = Path(__file__).parent / "recent_errors.txt"

FILTER_LABELS = [
    ("rate_limit",    r"429|too many request|rate.limit|quota.exceeded|limit.exceeded"),
    ("timeout",       r"timeout|timed.out|deadline.exceeded|gateway.timeout|504"),
    ("forbidden",     r"403|forbidden|unauthorized|permission.denied|invalid.*authoriz"),
    ("unavailable",   r"503|service.unavailable|unavailable|overloaded|temporarily.unavail"),
    ("not_found",     r"404|model.not.found|no endpoint|unsupported.model|unknown.model"),
]

# Modern Dark Palette
DARK_BG = "#1a1b26"
CARD_BG = "#24283b"
CARD_BORDER = "#414868"
TEXT_PRIMARY = "#c0caf5"
TEXT_MUTED = "#7a88cf"
ACCENT_BLUE = "#7aa2f7"
ACCENT_BLUE_HOVER = "#3d59a1"
ACCENT_PURPLE = "#bb9af7"
ENTRY_BG = "#16161e"


def _classify(error: str, status: str) -> str:
    text = f"{error or ''} {status or ''}".lower()
    for label, pattern in FILTER_LABELS:
        if re.search(pattern, text):
            return label
    return "other"


def _connect():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _fmt_date(v):
    """Return YYYY-MM-DD string or empty."""
    if not v:
        return ""
    y, m, d = v
    return f"{y:04d}-{m:02d}-{d:02d}"


def _center_window(win, width, height, parent=None):
    win.update_idletasks()
    if parent:
        px = parent.winfo_x()
        py = parent.winfo_y()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        x = max(0, px + (pw - width) // 2)
        y = max(0, py + (ph - height) // 2)
    else:
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = max(0, (sw - width) // 2)
        y = max(0, (sh - height) // 2)
    win.geometry(f"{width}x{height}+{x}+{y}")


def _apply_theme(root):
    root.configure(bg=DARK_BG)
    root.option_add("*Font", ("Segoe UI", 10))
    root.option_add("*Background", DARK_BG)
    root.option_add("*Foreground", TEXT_PRIMARY)

    # Style popup listbox for Comboboxes
    root.option_add("*TCombobox*Listbox.background", ENTRY_BG)
    root.option_add("*TCombobox*Listbox.foreground", TEXT_PRIMARY)
    root.option_add("*TCombobox*Listbox.selectBackground", ACCENT_BLUE_HOVER)
    root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
    root.option_add("*TCombobox*Listbox.borderWidth", 1)
    root.option_add("*TCombobox*Listbox.relief", "solid")

    style = ttk.Style()
    style.theme_use("clam")

    # Global Base Frame
    style.configure(".", background=DARK_BG, foreground=TEXT_PRIMARY, font=("Segoe UI", 10))
    style.configure("TFrame", background=DARK_BG)
    style.configure("Card.TFrame", background=CARD_BG)

    # LabelFrame Cards
    style.configure("TLabelframe", background=CARD_BG, bordercolor=CARD_BORDER, borderwidth=1, relief="solid")
    style.configure("TLabelframe.Label", background=CARD_BG, foreground=ACCENT_BLUE, font=("Segoe UI", 10, "bold"))

    # Labels
    style.configure("TLabel", background=DARK_BG, foreground=TEXT_PRIMARY, font=("Segoe UI", 10))
    style.configure("Card.TLabel", background=CARD_BG, foreground=TEXT_PRIMARY, font=("Segoe UI", 10))
    style.configure("Muted.TLabel", background=CARD_BG, foreground=TEXT_MUTED, font=("Segoe UI", 9))
    style.configure("Status.TLabel", background=DARK_BG, foreground=TEXT_MUTED, font=("Segoe UI", 9))

    # Checkbuttons
    style.configure("TCheckbutton", background=CARD_BG, foreground=TEXT_PRIMARY, font=("Segoe UI", 10), focuscolor="")
    style.map("TCheckbutton",
              background=[("active", CARD_BG)],
              foreground=[("active", ACCENT_BLUE)])

    # Buttons
    style.configure("Accent.TButton", background=ACCENT_BLUE, foreground="#ffffff", font=("Segoe UI", 10, "bold"), borderwidth=0, padding=(14, 7))
    style.map("Accent.TButton",
              background=[("active", ACCENT_BLUE_HOVER), ("disabled", "#333a56")],
              foreground=[("disabled", "#565f89")])

    style.configure("Secondary.TButton", background="#2f354f", foreground=TEXT_PRIMARY, font=("Segoe UI", 10), borderwidth=0, padding=(12, 7))
    style.map("Secondary.TButton",
              background=[("active", CARD_BORDER)])

    # Entry & Combobox
    style.configure("TEntry", fieldbackground=ENTRY_BG, foreground=TEXT_PRIMARY, bordercolor=CARD_BORDER, lightcolor=CARD_BORDER, darkcolor=CARD_BORDER, insertcolor=TEXT_PRIMARY, padding=5)
    style.configure("TCombobox", fieldbackground=ENTRY_BG, background=CARD_BG, foreground=TEXT_PRIMARY, bordercolor=CARD_BORDER, arrowcolor=TEXT_PRIMARY, padding=5)
    style.map("TCombobox",
              fieldbackground=[("readonly", ENTRY_BG)],
              foreground=[("readonly", TEXT_PRIMARY)],
              selectbackground=[("readonly", ENTRY_BG)],
              selectforeground=[("readonly", TEXT_PRIMARY)])


class FilterDialog(tk.Toplevel):
    """Modal for advanced filters (date, time, platform, model)."""

    def __init__(self, parent, platforms, models):
        super().__init__(parent)
        self.title("Advanced Filters")
        # Make window resizable for better platform/model viewing
        self.resizable(True, True)
        self.configure(bg=DARK_BG)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.result = None

        self.platforms = platforms
        self.models = models
        now = datetime.now()
        self.today = (now.year, now.month, now.day)

        # initialise date/time StringVars before building UI
        for suffix in ("_from", "_to"):
            setattr(self, f"var_date{suffix}_y", tk.StringVar(value=self.today[0]))
            setattr(self, f"var_date{suffix}_m", tk.StringVar(value=self.today[1]))
            setattr(self, f"var_date{suffix}_d", tk.StringVar(value=self.today[2]))
        self.var_date_from_y = getattr(self, "var_date_from_y")
        self.var_date_from_m = getattr(self, "var_date_from_m")
        self.var_date_from_d = getattr(self, "var_date_from_d")
        self.var_date_to_y = getattr(self, "var_date_to_y")
        self.var_date_to_m = getattr(self, "var_date_to_m")
        self.var_date_to_d = getattr(self, "var_date_to_d")
        self.var_time_from_h = tk.StringVar(value="00")
        self.var_time_from_m = tk.StringVar(value="00")
        self.var_time_to_h = tk.StringVar(value="23")
        self.var_time_to_m = tk.StringVar(value="59")

        self._build_ui()
        _center_window(self, 440, 460, parent=parent)
        self.transient(parent)
        self.grab_set()
        self.focus_set()
        self.wait_window()

    def _build_ui(self):
        pad = dict(padx=8, pady=5)
        body = ttk.Frame(self, padding=20)
        body.pack(fill="both", expand=True)

        # Header
        lbl_head = tk.Label(
            body, text="🔍 Advanced Filters", font=("Segoe UI", 13, "bold"),
            bg=DARK_BG, fg=ACCENT_PURPLE, anchor="w"
        )
        lbl_head.pack(fill="x", pady=(0, 12))

        # ── Date range ───────────────────────────────────────────────────
        frm_date = ttk.LabelFrame(body, text="📅 Date Range", padding=12)
        frm_date.pack(fill="x", pady=(0, 10))

        row = 0
        for label, var in [("From:", "date_from"), ("To:", "date_to")]:
            ttk.Label(frm_date, text=label, style="Card.TLabel", width=6).grid(row=row, column=0, sticky="e", **pad)
            ttk.Combobox(frm_date, textvariable=getattr(self, f"var_{var}_y"), width=5,
                         values=list(range(2020, 2031)), state="readonly").grid(row=row, column=1, sticky="w", **pad)
            ttk.Label(frm_date, text="/", style="Card.TLabel").grid(row=row, column=2, padx=2)
            ttk.Combobox(frm_date, textvariable=getattr(self, f"var_{var}_m"), width=5,
                         values=list(range(1, 13)), state="readonly").grid(row=row, column=3, sticky="w", **pad)
            ttk.Label(frm_date, text="/", style="Card.TLabel").grid(row=row, column=4, padx=2)
            ttk.Combobox(frm_date, textvariable=getattr(self, f"var_{var}_d"), width=5,
                         values=list(range(1, 32)), state="readonly").grid(row=row, column=5, sticky="w", **pad)
            row += 1

        # ── Time range ──────────────────────────────────────────────────
        frm_time = ttk.LabelFrame(body, text="⏰ Time Range", padding=12)
        frm_time.pack(fill="x", pady=(0, 10))

        row = 0
        for label, suf in [("From:", "time_from"), ("To:", "time_to")]:
            ttk.Label(frm_time, text=label, style="Card.TLabel", width=6).grid(row=row, column=0, sticky="e", **pad)
            h = ttk.Entry(frm_time, textvariable=getattr(self, f"var_{suf}_h"), width=4, font=("Segoe UI", 10))
            h.grid(row=row, column=1, sticky="w", **pad)
            ttk.Label(frm_time, text=":", style="Card.TLabel").grid(row=row, column=2, padx=2)
            m = ttk.Entry(frm_time, textvariable=getattr(self, f"var_{suf}_m"), width=4, font=("Segoe UI", 10))
            m.grid(row=row, column=3, sticky="w", **pad)
            row += 1

        # ── Platform ──────────────────────────────────────────────────────
        frm_platform = ttk.LabelFrame(body, text="🌐 Platform", padding=12)
        frm_platform.pack(fill="x", pady=(0, 10))
        self.var_platform = tk.StringVar()
        cb = ttk.Combobox(frm_platform, textvariable=self.var_platform,
                     values=self.platforms, state="readonly", width=36, font=("Segoe UI", 10))
        cb.pack(fill="x", pady=2)
        # Ensure listbox has height to show all options
        cb.option_add('*TCombobox*Listbox.height', 8)
        cb.option_add('*TCombobox*Listbox.width', 36)
        # Set initial selection to first platform if available
        if self.platforms:
            cb.current(0)
        ttk.Label(frm_platform, text="(leave blank for all platforms)", style="Muted.TLabel").pack(anchor="w")

        # ── Model ─────────────────────────────────────────────────────────
        frm_model = ttk.LabelFrame(body, text="🤖 Model", padding=12)
        frm_model.pack(fill="x", pady=(0, 12))
        self.var_model = tk.StringVar()
        ttk.Combobox(frm_model, textvariable=self.var_model,
                     values=self.models, state="readonly", width=36, font=("Segoe UI", 10)).pack(fill="x", pady=2)
        ttk.Label(frm_model, text="(leave blank for all models)", style="Muted.TLabel").pack(anchor="w")

        # ── Buttons ───────────────────────────────────────────────────────
        btn_frame = ttk.Frame(body)
        btn_frame.pack(fill="x", pady=(8, 0))
        ttk.Button(btn_frame, text="Apply Filters", style="Accent.TButton", command=self._apply).pack(side="right", padx=(8, 0))
        ttk.Button(btn_frame, text="Cancel", style="Secondary.TButton", command=self._cancel).pack(side="right")

    def _apply(self):
        def _date(val_y, val_m, val_d):
            y, m, d = val_y.get(), val_m.get(), val_d.get()
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"

        def _time(val_h, val_m):
            return f"{int(val_h.get()):02d}:{int(val_m.get()):02d}"

        self.result = {
            "date_from": _date(self.var_date_from_y, self.var_date_from_m, self.var_date_from_d),
            "date_to": _date(self.var_date_to_y, self.var_date_to_m, self.var_date_to_d),
            "time_from": _time(self.var_time_from_h, self.var_time_from_m),
            "time_to": _time(self.var_time_to_h, self.var_time_to_m),
            "platform": self.var_platform.get().strip(),
            "model": self.var_model.get().strip(),
        }
        self.destroy()

    def _cancel(self):
        self.result = {}
        self.destroy()


class ExportApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FreeLLMAPI Error Exporter")
        self.resizable(True, True)

        _apply_theme(self)

        self.main_frame = ttk.Frame(self, padding=24)
        self.main_frame.pack(fill="both", expand=True)
        self.advanced = {}
        self._build_ui()
        self._load_options()
        _center_window(self, 480, 480)

    def _build_ui(self):
        # Header Banner
        hdr_frame = tk.Frame(self.main_frame, bg=DARK_BG)
        hdr_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        lbl_title = tk.Label(
            hdr_frame, text="⚡ FreeLLMAPI Error Exporter",
            font=("Segoe UI", 15, "bold"), bg=DARK_BG, fg=ACCENT_PURPLE, anchor="w"
        )
        lbl_title.pack(anchor="w")

        lbl_sub = tk.Label(
            hdr_frame, text="Export diagnostic error logs to text report",
            font=("Segoe UI", 9), bg=DARK_BG, fg=TEXT_MUTED, anchor="w"
        )
        lbl_sub.pack(anchor="w", pady=(2, 0))

        # Divider
        sep = tk.Frame(self.main_frame, height=1, bg=CARD_BORDER)
        sep.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        # Limit entry card
        frm_limit = ttk.LabelFrame(self.main_frame, text="⚙️ Export Limit", padding=12)
        frm_limit.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 14))

        ttk.Label(frm_limit, text="Max errors to fetch:", style="Card.TLabel").grid(row=0, column=0, sticky="e", padx=(0, 12))
        self.var_limit = tk.StringVar(value="100")
        ttk.Entry(frm_limit, textvariable=self.var_limit, width=12, font=("Segoe UI", 10)).grid(row=0, column=1, sticky="w")

        # Filter checkboxes card
        frm_filters = ttk.LabelFrame(self.main_frame, text="📊 Filter by Error Type", padding=12)
        frm_filters.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        self.check_vars = {}
        for i, (key, desc) in enumerate([
            ("rate_limit",    "429 / Rate Limit"),
            ("timeout",       "504 / Timeout"),
            ("forbidden",     "403 / Forbidden"),
            ("unavailable",   "503 / Unavailable"),
            ("not_found",     "404 / Not Found"),
            ("other",         "Other Errors"),
        ]):
            var = tk.BooleanVar(value=True)
            self.check_vars[key] = var
            ttk.Checkbutton(frm_filters, text=desc, variable=var).grid(
                row=i // 2, column=i % 2, sticky="w", padx=(0, 24), pady=5,
            )

        # Buttons frame
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 16))

        self.btn_export = ttk.Button(
            btn_frame, text="📥 Export Report", style="Accent.TButton", command=self._export
        )
        self.btn_export.pack(side="left", padx=(0, 10))

        self.btn_advanced = ttk.Button(
            btn_frame, text="⚙️ Advanced Filters...", style="Secondary.TButton", command=self._open_advanced
        )
        self.btn_advanced.pack(side="left")

        # Status Bar Card
        status_card = tk.Frame(self.main_frame, bg=CARD_BG, highlightbackground=CARD_BORDER, highlightthickness=1)
        status_card.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 0))

        self.var_status = tk.StringVar(value="🟢 Ready")
        lbl_status = tk.Label(
            status_card, textvariable=self.var_status, bg=CARD_BG, fg=TEXT_MUTED,
            font=("Segoe UI", 9), anchor="w", padx=10, pady=8
        )
        lbl_status.pack(fill="x")

        self.main_frame.columnconfigure(0, weight=1)

    def _load_options(self):
        try:
            with _connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT DISTINCT platform FROM requests ORDER BY platform")
                self.platforms = [r["platform"] for r in cur.fetchall()]
                cur.execute("SELECT DISTINCT model_id FROM requests ORDER BY model_id")
                self.models = [r["model_id"] for r in cur.fetchall()]
        except Exception:
            self.platforms = []
            self.models = []

    def _open_advanced(self):
        dlg = FilterDialog(self, self.platforms, self.models)
        if dlg.result is not None and dlg.result != {}:
            self.advanced.update(dlg.result)
            self.btn_advanced.config(text="⚙️ Advanced Filters (Active)")
            self.var_status.set("⚙️ Advanced filters applied — click Export Report")

    def _get_selected_filters(self) -> list[str]:
        return [k for k, v in self.check_vars.items() if v.get()]

    def _fetch(self, errors_limit: int, filters: list[str]) -> list[dict]:
        cond_parts = ["status != 'success'"]
        params: list = []

        adv = self.advanced
        if adv.get("date_from"):
            cond_parts.append("date(created_at, 'localtime') >= ?")
            params.append(adv["date_from"])
        if adv.get("date_to"):
            cond_parts.append("date(created_at, 'localtime') <= ?")
            params.append(adv["date_to"])
        if adv.get("time_from"):
            cond_parts.append("time(created_at, 'localtime') >= ?")
            params.append(adv["time_from"])
        if adv.get("time_to"):
            cond_parts.append("time(created_at, 'localtime') <= ?")
            params.append(adv["time_to"])
        if adv.get("platform"):
            cond_parts.append("platform = ?")
            params.append(adv["platform"])
        if adv.get("model"):
            cond_parts.append("model_id = ?")
            params.append(adv["model"])

        where = " AND ".join(cond_parts)
        sql = f"""
            SELECT platform, model_id, status, error, input_tokens, output_tokens,
                   latency_ms, created_at, client_agent, caller
            FROM requests
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT ?
        """
        params.append(errors_limit)

        with _connect() as conn:
            cur = conn.cursor()
            cur.execute(sql, params)
            all_rows = [dict(r) for r in cur.fetchall()]

        classified = [(row, _classify(row["error"], row["status"])) for row in all_rows]
        filtered = [row for row, label in classified if label in filters]
        return filtered

    def _format(self, rows: list[dict], filters: list[str]) -> str:
        if not rows:
            return "No errors found matching the selected filters.\n"

        lines = [
            f"FreeLLMAPI Error Report — generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Filters: {', '.join(filters)}",
            f"Total errors exported: {len(rows)}",
            "",
        ]
        for i, row in enumerate(rows, 1):
            label = _classify(row["error"], row["status"])
            lines.append(f"--- Error #{i} [{label}] ---")
            lines.append(f"Time:           {row['created_at']}")
            lines.append(f"Platform:       {row['platform']}")
            lines.append(f"Model:          {row['model_id']}")
            lines.append(f"Status:         {row['status']}")
            lines.append(f"Error:          {row['error'] or '(none)'}")
            lines.append(f"Input tokens:   {row['input_tokens']}")
            lines.append(f"Output tokens:  {row['output_tokens']}")
            lines.append(f"Latency:        {row['latency_ms']} ms")
            lines.append(f"Client:         {row['client_agent'] or 'unknown'}")
            lines.append(f"Caller:         {row['caller'] or 'none'}")
            lines.append("")

        return "\n".join(lines)

    def _export(self):
        try:
            limit = int(self.var_limit.get())
            if limit <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid input", "Limit must be a positive integer.")
            return

        filters = self._get_selected_filters()
        if not filters:
            messagebox.showwarning("No filters", "Please select at least one error type.")
            return

        self.var_status.set("⏳ Fetching data…")
        self.btn_export.config(state="disabled")
        self.update_idletasks()

        try:
            rows = self._fetch(errors_limit=limit, filters=filters)
            content = self._format(rows, filters)
            OUTPUT_PATH.write_text(content, encoding="utf-8")
            subprocess.Popen(["notepad.exe", str(OUTPUT_PATH)])
            self.var_status.set(f"✅ Wrote {len(rows)} errors → {OUTPUT_PATH.name}")
        except FileNotFoundError:
            messagebox.showerror("Database not found", f"Could not find:\n{DB_PATH}")
            self.var_status.set("⚠️ Error: database not found")
        except Exception as exc:
            messagebox.showerror("Export failed", str(exc))
            self.var_status.set("⚠️ Export error")
        finally:
            self.btn_export.config(state="normal")


if __name__ == "__main__":
    app = ExportApp()
    app.mainloop()
