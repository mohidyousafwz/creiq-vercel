# CREIQ Technical Guide

## 📚 Table of Contents
- [System Architecture](#system-architecture)
- [Core Components](#core-components)
- [Code Structure](#code-structure)
- [Implementation Details](#implementation-details)
- [Data Flow](#data-flow)
- [Error Handling](#error-handling)
- [Performance Considerations](#performance-considerations)
- [Security](#security)
- [Extending the System](#extending-the-system)

## 🏗️ System Architecture

### Overview
CREIQ follows a modular architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer (FastAPI)                    │
│  - HTTP endpoints for file upload and control               │
│  - Request validation and response formatting               │
│  - Async task management                                    │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                      │
│  - Roll number validation and parsing                       │
│  - Task orchestration and workflow management               │
│  - Data transformation and storage                          │
└─────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────┐
│                    Automation Layer                          │
│  - Browser lifecycle management (Playwright)                 │
│  - Web page interaction and navigation                      │
│  - Data extraction from web pages                           │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction
```python
# Simplified flow
API receives request → Validates input → Creates automation task
    ↓
Task reads Excel → Extracts roll numbers → Initiates browser
    ↓
For each roll number → Navigate to site → Enter data → Extract results
    ↓
Save results → Clean up resources → Return response
```

## 🔧 Core Components

### 1. API Module (`src/creiq/api.py`)

The FastAPI application that provides RESTful endpoints:

```python
app = FastAPI(title="CREIQ API", version="1.0.0")

# Key components:
- Global state management (automation_task, automation_instance)
- Thread-safe shutdown signaling
- Async task execution
- File upload handling
```

#### Key Features:
- **Async Processing**: Uses `asyncio` for non-blocking operations
- **Thread Safety**: Uses `threading.Lock()` for concurrent access
- **Graceful Shutdown**: Implements shutdown signaling mechanism
- **Error Propagation**: Captures and returns detailed error information

### 2. Automation Module (`src/creiq/playwright_automation.py`)

Handles all browser automation tasks using Playwright:

```python
class PlaywrightAutomation:
    def __init__(self, headless: bool = False, 
                 shutdown_signal: Optional[threading.Event] = None):
        # Browser configuration
        # Shutdown signal handling
        # Resource initialization
```

#### Key Methods:

**Browser Management:**
- `start_browser()`: Initializes Playwright and launches Firefox
- `close()`: Safely closes all browser resources
- `navigate_to_site()`: Loads the ARB website

**Data Processing:**
- `enter_roll_number()`: Splits 19-digit number into 6 input fields
- `submit_search()`: Clicks search button and waits for results
- `extract_data_to_json()`: Extracts data from result pages

**Batch Operations:**
- `process_roll_numbers()`: Main workflow for processing multiple numbers
- Error recovery and logging for each roll number

### 3. Reader Module (`src/creiq/roll_number_reader.py`)

Handles Excel file processing:

```python
class RollNumberReader:
    @staticmethod
    def read_roll_numbers_from_excel(file_path: str) -> List[str]:
        # Reads first column from Excel
        # Validates roll number format
        # Returns list of valid numbers
```

## 🔍 Implementation Details

### Roll Number Processing

Roll numbers are 19-digit identifiers split across 6 input fields:

```python
# Format: XX-XX-XXX-XXX-XXXXX-XXXX
# Example: 19-08-072-215-00500-0000

segments = [
    digits[0:2],    # Field 1: 2 digits
    digits[2:4],    # Field 2: 2 digits
    digits[4:7],    # Field 3: 3 digits
    digits[7:10],   # Field 4: 3 digits
    digits[10:15],  # Field 5: 5 digits
    digits[15:19]   # Field 6: 4 digits
]
```

### Shutdown Mechanism

The system implements graceful shutdown using threading events:

```python
# In API
shutdown_signal = threading.Event()

# In automation
def _check_shutdown(self):
    if self.shutdown_signal and self.shutdown_signal.is_set():
        raise GracefulShutdownException("Shutting down gracefully")

# Called before each major operation
self._check_shutdown()
```

### Error Recovery Strategy

1. **Page-level Recovery**: If navigation fails, retry navigation
2. **Roll Number Recovery**: Skip failed roll numbers, continue with next
3. **Resource Cleanup**: Always clean up browser resources in finally blocks
4. **Error Documentation**: Save error details to `error_log.txt`

## 📊 Data Flow

### 1. Input Processing
```
Excel File → Upload Endpoint → Validation → Storage
    ↓
Extract Roll Numbers → Validate Format → Queue for Processing
```

### 2. Web Automation
```
For Each Roll Number:
    Navigate to Search Page → Enter Roll Number → Submit Search
        ↓
    Wait for Results → Check for Errors → Extract Data
        ↓
    Save JSON → Save HTML → Take Screenshot (optional)
```

### 3. Output Generation
```
Individual Results:
data/results/
├── 1908072215005000000/
│   ├── extracted_data.json
│   ├── page_content.html
│   └── error_log.txt (if errors)
└── 1908072215005000001/
    └── no_records_found.txt (if no data)
```

## ⚠️ Error Handling

### Exception Hierarchy
```python
Exception
├── GracefulShutdownException  # Clean shutdown requested
├── RuntimeError              # Browser not initialized
├── ValueError               # Invalid configuration
└── Exception               # General errors with fallback
```

### Error Handling Patterns

1. **Try-Except-Finally**:
```python
try:
    # Risky operation
    self.enter_roll_number(roll_number)
except GracefulShutdownException:
    raise  # Propagate shutdown
except Exception as e:
    logger.error(f"Error: {e}")
    # Recovery action
finally:
    # Cleanup
```

2. **Defensive Programming**:
```python
if not self.page:
    raise RuntimeError("Browser not started")
```

3. **Error Logging**:
```python
with open(error_file, 'w') as f:
    f.write(f"Error: {str(e)}\nTraceback: {traceback.format_exc()}")
```

## 🚀 Performance Considerations

### 1. Browser Optimization
- **Single Browser Instance**: Reuse browser for multiple searches
- **Network Idle Wait**: Wait for `networkidle` state
- **Timeout Configuration**: 60s for navigation, 30s for search

### 2. Resource Management
- **Lazy Initialization**: Start browser only when needed
- **Explicit Cleanup**: Close resources in reverse order
- **Memory Management**: Clear page content between searches

### 3. Concurrency
- **Thread Safety**: Lock for global state access
- **Async Operations**: Non-blocking file I/O
- **Background Tasks**: Long operations in separate threads

## 🔒 Security

### 1. Input Validation
- File type validation (only .xlsx)
- File size limits
- Roll number format validation

### 2. Environment Security
- Sensitive URLs in environment variables
- No hardcoded credentials
- Secure file permissions for .env

### 3. Browser Security
```python
launch_args = [
    '--no-sandbox',
    '--disable-web-security',
    '--ignore-certificate-errors'
]
```
**Note**: These settings reduce security for automation purposes

## 🔧 Extending the System

### Adding New Data Extractors

1. **Modify `extract_data_to_json()`**:
```python
def extract_data_to_json(self, roll_number: str) -> Dict[str, Any]:
    # Add new extraction logic
    property_address = self.page.locator('selector').text_content()
    data["property_info"]["address"] = property_address
```

2. **Add Specific Extractors**:
```python
def extract_appeal_details(self) -> List[Dict]:
    appeals = []
    rows = self.page.locator('table.appeals tr')
    for row in rows:
        appeal = {
            "case_no": row.locator('td:nth-child(1)').text_content(),
            "status": row.locator('td:nth-child(2)').text_content()
        }
        appeals.append(appeal)
    return appeals
```

### Adding New Endpoints

1. **Define in `api.py`**:
```python
@app.get("/results/{roll_number}")
async def get_results(roll_number: str):
    file_path = f"data/results/{roll_number}/extracted_data.json"
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Results not found")
```

### Custom Processors

1. **Create New Processor Class**:
```python
class CustomProcessor:
    def process(self, data: Dict) -> Dict:
        # Transform data
        return processed_data
```

2. **Integrate with Workflow**:
```python
# In process_roll_numbers
processor = CustomProcessor()
processed_data = processor.process(extracted_data)
```

## 🔍 Debugging Tips

### 1. Enable Debug Logging
```python
logger.setLevel(logging.DEBUG)
```

### 2. Browser Debugging
```python
# Run with headless=False to see browser
automation = PlaywrightAutomation(headless=False)
```

### 3. Save Debug Information
```python
# Take screenshots at each step
self.take_screenshot(f"debug_{step_name}.png")

# Save page HTML
self.save_html_content(f"debug_{step_name}.html")
```

### 4. Test Individual Components
```python
# Test single roll number
if __name__ == '__main__':
    automation = PlaywrightAutomation()
    automation.start_browser()
    automation.navigate_to_site()
    automation.enter_roll_number("1908072215005000000")
```

## 📈 Monitoring

### Key Metrics to Track
1. **Success Rate**: Successful vs failed roll numbers
2. **Processing Time**: Time per roll number
3. **Error Types**: Common failure patterns
4. **Resource Usage**: Memory and CPU utilization

### Logging Strategy
```python
logger.info(f"Processing {i+1}/{total}: {roll_number}")
logger.error(f"Failed {roll_number}: {error}")
logger.warning(f"No records for {roll_number}")
```

## 🎯 Best Practices

1. **Always Check Shutdown Signal**: Before long operations
2. **Use Context Managers**: For file operations
3. **Validate Input Early**: Fail fast principle
4. **Log Liberally**: But avoid sensitive data
5. **Handle Cleanup**: Even in error scenarios
6. **Test Edge Cases**: Empty inputs, malformed data
7. **Document Assumptions**: Browser requirements, data formats 