# CREIQ - ARB Website Automation System

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/Playwright-1.40+-green.svg" alt="Playwright">
  <img src="https://img.shields.io/badge/FastAPI-0.104+-red.svg" alt="FastAPI">
  <img src="https://img.shields.io/badge/Coverage-80%25-brightgreen.svg" alt="Coverage">
</div>

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

CREIQ is an automated web scraping system designed to interact with the Assessment Review Board (ARB) website. It automates the process of searching for property information using roll numbers, extracting relevant data, and saving it in structured formats.

The system is built with reliability and scalability in mind, featuring:
- **Robust error handling** with automatic recovery
- **Graceful shutdown** capabilities for long-running operations
- **Comprehensive logging** for debugging and monitoring
- **RESTful API** for easy integration
- **Extensive test coverage** (80%+)

## ✨ Features

### Core Functionality
- 🌐 **Automated Web Navigation**: Uses Playwright to control Firefox browser
- 📝 **Batch Processing**: Process multiple roll numbers from Excel files
- 🔍 **Data Extraction**: Extract property and appeal information
- 💾 **Multiple Output Formats**: Save as JSON and HTML
- 📸 **Screenshot Capture**: Document the state of pages

### Technical Features
- 🚀 **Async API**: Built with FastAPI for high performance
- 🛡️ **Error Recovery**: Automatic retry and error logging
- 🔄 **Graceful Shutdown**: Clean termination of long-running tasks
- 📊 **Progress Tracking**: Real-time status updates
- 🧪 **Comprehensive Testing**: 30+ tests with mocking

### Security & Reliability
- 🔐 **Environment-based Configuration**: Sensitive data in `.env` files
- 🚦 **Thread-safe Operations**: Proper synchronization for concurrent access
- 📝 **Detailed Logging**: Comprehensive logs for debugging
- ⚡ **Resource Management**: Automatic cleanup of browser resources

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Excel Files   │────▶│   FastAPI App   │────▶│   Playwright    │
│  (Roll Numbers) │     │   (REST API)    │     │  (Web Browser)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │                         │
                               ▼                         ▼
                        ┌─────────────────┐     ┌─────────────────┐
                        │  JSON Output    │     │   ARB Website   │
                        │   (Results)     │◀────│  (Data Source)  │
                        └─────────────────┘     └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Firefox browser (for Playwright)
- Windows/Linux/macOS

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/creiq.git
cd creiq
```

2. **Create virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
playwright install firefox
```

4. **Configure environment**
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# URL=https://your-arb-website.com
```

### Running the Application

1. **Start the API server**
```bash
python -m uvicorn src.creiq.api:app --reload
```

2. **Access the API documentation**
```
http://localhost:8000/docs
```

3. **Upload and process Excel file**
```bash
curl -X POST "http://localhost:8000/process" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_roll_numbers.xlsx"
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Required
URL=https://arb-website.com

# Optional
HEADLESS=false              # Run browser in headless mode
LOG_LEVEL=INFO             # Logging level
RESULTS_DIR=data/results   # Output directory
```

### Excel File Format

The system expects Excel files with roll numbers in the first column:

| A (Roll Number)      |
|---------------------|
| 1908072215005000000 |
| 1908072215005000001 |
| 1908072215005000002 |

## 📚 API Documentation

### Endpoints

#### `GET /`
Health check endpoint.

**Response:**
```json
{
  "message": "CREIQ API is running",
  "version": "1.0.0"
}
```

#### `POST /process`
Process an Excel file containing roll numbers.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body: Excel file (.xlsx)

**Response:**
```json
{
  "status": "completed",
  "message": "Processing completed successfully",
  "details": {
    "total_roll_numbers": 10,
    "processed": 10,
    "successful": 8,
    "failed": 2
  }
}
```

#### `POST /shutdown`
Gracefully shutdown any running automation tasks.

**Response:**
```json
{
  "status": "shutdown initiated",
  "message": "Automation tasks are shutting down"
}
```

#### `GET /status`
Get current processing status.

**Response:**
```json
{
  "automation_running": true,
  "current_task": "Processing roll number 5 of 10"
}
```

## 🧪 Testing

### Run All Tests
```bash
python run_tests.py
```

### Run with Coverage
```bash
pytest tests/ --cov=src/creiq --cov-report=html
```

### View Coverage Report
```bash
# Windows
start htmlcov/index.html

# Linux/macOS
open htmlcov/index.html
```

### Test Categories
- **Unit Tests**: Test individual components
- **Integration Tests**: Test complete workflows
- **Edge Cases**: Test error conditions

## 📁 Project Structure

```
CREIQ/
├── src/
│   └── creiq/
│       ├── __init__.py           # Package initialization
│       ├── api.py                # FastAPI application
│       ├── playwright_automation.py  # Browser automation
│       └── roll_number_reader.py # Excel file processing
├── tests/
│   ├── test_playwright_automation.py  # Test suite
│   ├── requirements-test.txt     # Test dependencies
│   └── TEST_SUMMARY.md          # Test documentation
├── data/
│   ├── uploads/                 # Uploaded Excel files
│   └── results/                 # Processing results
├── requirements.txt             # Project dependencies
├── .env.example                # Environment template
├── pytest.ini                  # Pytest configuration
└── README.md                   # This file
```

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Write tests for new features
- Follow PEP 8 style guide
- Update documentation
- Ensure all tests pass

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Playwright](https://playwright.dev/) for reliable browser automation
- Powered by [FastAPI](https://fastapi.tiangolo.com/) for modern API development
- Tested with [Pytest](https://pytest.org/) for comprehensive test coverage

---

<div align="center">
  <p>Built with ❤️ by the CREIQ Team</p>
</div>
