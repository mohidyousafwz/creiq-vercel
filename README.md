# CREIQ - Data Extraction Service

CREIQ (CRE Intelligence Query) is a Python-based web scraping application that extracts appeal data from the Assessment Review Board (ARB) website. It uses Playwright for browser automation and provides both API and command-line interfaces.

## 🚀 Features

- **Automated Data Extraction**: Extracts appeal information for multiple roll numbers
- **RESTful API**: Upload CSV files and process roll numbers via API endpoints
- **Property Information**: Captures property descriptions, classifications, and municipality data
- **Appeal Details**: Extracts appellant info, status, hearing details, and decisions
- **Batch Processing**: Handle multiple roll numbers efficiently
- **Background Processing**: Non-blocking API with task tracking
- **Test Mode**: Easy testing with single roll numbers

## 📋 Prerequisites

- Python 3.8 or higher
- Node.js (for Playwright)
- Chrome/Chromium browser

## 🛠️ Installation

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/creiq.git
cd creiq
```

2. **Create virtual environment**:
```bash
python -m venv myenv
# On Windows:
myenv\Scripts\activate
# On macOS/Linux:
source myenv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Install Playwright browsers**:
```bash
playwright install chromium
```

5. **Set up environment variables**:
```bash
cp env.example .env
# Edit .env and add your ARB website URL
```

## 🚦 Quick Start

### Testing Single Roll Number

```bash
python scripts/test_extraction.py
# Or with a specific roll number:
python scripts/test_extraction.py "38-29-300-012-10400-0000"
```

### Running the API Server

```bash
python main.py
# API will be available at http://localhost:8000
# Documentation at http://localhost:8000/docs
```

### Upload CSV via API

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@data/sample_upload_files/roll-number.csv"
```

## 📁 Project Structure

```
CREIQ/
├── src/
│   └── creiq/
│       ├── config/           # Configuration management
│       │   ├── __init__.py
│       │   └── settings.py   # Application settings
│       ├── models/           # Data models (future DB support)
│       │   ├── __init__.py
│       │   └── appeal.py     # Appeal data structures
│       ├── services/         # Business logic
│       │   ├── __init__.py
│       │   └── extraction_service.py
│       ├── utils/            # Utility functions
│       │   ├── __init__.py
│       │   ├── logger.py
│       │   └── roll_number_reader.py
│       ├── __init__.py
│       ├── api.py            # FastAPI application
│       └── playwright_automation.py  # Web scraping logic
├── tests/
│   └── unit/                 # Unit tests
│       ├── __init__.py
│       └── test_extraction.py
├── scripts/
│   ├── test_extraction.py    # Test single extraction
│   └── run_tests.py         # Run test suite
├── data/
│   ├── sample_upload_files/  # Sample CSV files
│   ├── results/              # Extraction results
│   └── test_extraction/      # Test outputs
├── config/                   # Configuration files
├── main.py                   # Main entry point
├── requirements.txt          # Python dependencies
├── env.example              # Environment variables template
├── docker-compose.yml       # Docker configuration
└── README.md
```

## 📊 Output Format

The extraction creates a JSON file (`all_appeal_details.json`) with the following structure:

```json
{
  "roll_number": "38-29-300-012-10400-0000",
  "extracted_timestamp": "2025-06-11T15:02:35.689946",
  "page_title": "E-Services - Appeals",
  "property_info": {
    "description": "429 EXMOUTH ST PLAN 3 PT LOT 5 PLAN 96 LOT"
  },
  "appeals": [
    {
      "appeal_number": "1194369",
      "property_info": {
        "roll_number": "38-29-300-012-10400-0000",
        "municipality": "Sarnia City",
        "classification": "Commercial sport complexes",
        "nbhd": "293",
        "description": "429 EXMOUTH STPLAN 3 PT LOT 5 PLAN 96 LOT"
      },
      "appellant_info": {
        "name1": "J J W HOLDINGS LTD",
        "name2": "C/O DONALD STASIW",
        "representative": "D B BURNARD & ASSOCIATES",
        "filing_date": "31-March-2000",
        "tax_date": "01-January-2000",
        "section": "40",
        "reason_for_appeal": "Assessment Too High"
      },
      "status_info": {
        "status": "Closed"
      },
      "decision_info": {
        "decision_number": "1357206",
        "mailing_date": "23-June-2000",
        "decisions": "APPEAL WITHDRAWN (BEFORE SCHEDULING)",
        "decision_details": "HEARING # 17287."
      }
    }
  ]
}
```

## 🧪 Testing

Run the test suite with coverage:

```bash
python scripts/run_tests.py
```

This will generate:
- Terminal coverage report
- HTML coverage report in `htmlcov/index.html`

## 🔧 Configuration

Key environment variables in `.env`:

- `URL`: ARB website URL (required)
- `BROWSER_HEADLESS`: Run browser in headless mode (default: true)
- `API_HOST`: API host address (default: 0.0.0.0)
- `API_PORT`: API port number (default: 8000)
- `LOG_LEVEL`: Logging level (default: INFO)

See `env.example` for all available options.

## 🚧 Upcoming Features

- [ ] Web Dashboard with authentication
- [ ] Database integration (SQLAlchemy)
- [ ] Scheduled extraction (cron jobs)
- [ ] Export to multiple formats (Excel, PDF)
- [ ] Email notifications
- [ ] Docker deployment
- [ ] Rate limiting and retry logic
- [ ] Advanced filtering and search

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Playwright](https://playwright.dev/) for reliable web automation
- [FastAPI](https://fastapi.tiangolo.com/) for the modern API framework
- Assessment Review Board for providing the public data
