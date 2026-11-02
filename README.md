# FreeLLMAPI Visualizer

A modern Tkinter GUI tool for exporting and analyzing error logs from FreeLLMAPI's SQLite database.

## Features
- Export recent errors to `.txt` with auto-Notepad opening
- Filter by error type: rate limits (429), timeouts (504), forbidden (403), unavailable (503), not found (404), other
- Advanced filters: date range, time range, platform, model
- Dark theme with modern styling
- Cross-platform (Windows/macOS/Linux)

## Screenshots

![GUI Screenshot](https://via.placeholder.com/800x600.png?text=FreeLLMAPI+Visualizer+Dark+Theme)

## Installation

```bash
# Clone the repo
git clone https://github.com/your-username/freeapi-visualizer.git

# Install dependencies
pip install -r requirements.txt

# Run the GUI
python export_errors_gui.py
```

## Usage

1. Run the program
2. Select error types to filter
3. Click "Export Report" to generate `recent_errors.txt`
4. File auto-opens in Notepad

## Advanced Filters

Click "Advanced Filters..." to set:
- Date range (from/to)
- Time range (from/to)
- Platform filter
- Model filter

## Contributing

Feel free to open issues or submit pull requests.

## License

MIT License

---

*Built with Python/Tkinter • Dark theme by Claude Code*