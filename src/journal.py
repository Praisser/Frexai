import os
import csv
from datetime import datetime

JOURNAL_FILE = "trade_journal.csv"

def log_trade(
    strategy: str,
    entry: float,
    sl: float,
    tp: float,
    result: str,
    rr: float,
    date: str,
    chart_path: str = "",
    mode: str = "a"
):
    file_exists = os.path.isfile(JOURNAL_FILE)
    with open(JOURNAL_FILE, mode, newline='') as f:
        writer = csv.writer(f)
        if not file_exists or mode == "w":
            writer.writerow(["Strategy", "Entry", "SL", "TP", "Result", "RR", "Date", "Screenshot"])
        writer.writerow([strategy, entry, sl, tp, result, rr, date, chart_path])
