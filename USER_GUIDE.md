# CREIQ User Guide

## 📋 Table of Contents
- [Getting Started](#getting-started)
- [Preparing Your Data](#preparing-your-data)
- [Using the Web Interface](#using-the-web-interface)
- [Using the API](#using-the-api)
- [Understanding Results](#understanding-results)
- [Troubleshooting](#troubleshooting)
- [Common Tasks](#common-tasks)
- [FAQ](#faq)

## 🚀 Getting Started

### Prerequisites
Before using CREIQ, ensure you have:
- ✅ Access to the ARB website URL
- ✅ Excel files with roll numbers
- ✅ The CREIQ system running locally or on a server

### First Time Setup

1. **Verify the system is running**:
   - Open your browser
   - Navigate to: `http://localhost:8000/docs`
   - You should see the API documentation page

2. **Test the connection**:
   ```bash
   curl http://localhost:8000/
   ```
   Expected response:
   ```json
   {
     "message": "CREIQ API is running",
     "version": "1.0.0"
   }
   ```

## 📊 Preparing Your Data

### Excel File Format

CREIQ expects Excel files (.xlsx) with roll numbers in the first column:

#### ✅ Correct Format:
| A |
|---|
| 1908072215005000000 |
| 1908072215005000001 |
| 1908072215005000002 |

#### ❌ Common Mistakes:
- Headers in the first row (skip them)
- Roll numbers in other columns
- Non-numeric characters (will be stripped)
- Wrong number of digits (must be 19)

### Roll Number Format

Roll numbers must be 19 digits, formatted as:
```
XX-XX-XXX-XXX-XXXXX-XXXX
```
Example: `19-08-072-215-00500-0000`

**Note**: Dashes are optional; the system will parse correctly either way.

## 🌐 Using the Web Interface

### Step 1: Access the API Documentation
1. Open your browser
2. Go to: `http://localhost:8000/docs`
3. You'll see the interactive API documentation

### Step 2: Upload Your Excel File
1. Click on `POST /process`
2. Click "Try it out"
3. Click "Choose File" and select your Excel file
4. Click "Execute"

### Step 3: Monitor Progress
The response will show:
```json
{
  "status": "processing",
  "message": "Processing 10 roll numbers",
  "task_id": "task_123"
}
```

### Step 4: Check Status
1. Click on `GET /status`
2. Click "Try it out"
3. Click "Execute"

Response shows current progress:
```json
{
  "automation_running": true,
  "current_task": "Processing roll number 5 of 10"
}
```

## 💻 Using the API

### With cURL

#### Upload and Process File
```bash
curl -X POST "http://localhost:8000/process" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@roll_numbers.xlsx"
```

#### Check Status
```bash
curl -X GET "http://localhost:8000/status"
```

#### Shutdown Processing
```bash
curl -X POST "http://localhost:8000/shutdown"
```

### With Python

```python
import requests

# Upload file
with open('roll_numbers.xlsx', 'rb') as f:
    files = {'file': f}
    response = requests.post('http://localhost:8000/process', files=files)
    print(response.json())

# Check status
status = requests.get('http://localhost:8000/status')
print(status.json())
```

### With PowerShell

```powershell
# Upload file
$uri = "http://localhost:8000/process"
$filePath = "C:\path\to\roll_numbers.xlsx"
$response = Invoke-RestMethod -Uri $uri -Method Post -InFile $filePath
$response | ConvertTo-Json

# Check status
Invoke-RestMethod -Uri "http://localhost:8000/status" | ConvertTo-Json
```

## 📁 Understanding Results

### Output Directory Structure
```
data/results/
├── 1908072215005000000/
│   ├── extracted_data.json    # Structured data
│   ├── page_content.html      # Raw HTML (if saved)
│   └── screenshot.png         # Visual record (if enabled)
├── 1908072215005000001/
│   └── no_records_found.txt   # Indicates no data found
└── 1908072215005000002/
    └── error_log.txt          # Contains error details
```

### JSON Data Format
```json
{
  "roll_number": "1908072215005000000",
  "extracted_timestamp": "2024-01-15T10:30:00",
  "page_title": "ARB Property Details",
  "property_info": {
    "address": "123 Main St",
    "owner": "John Doe",
    "assessed_value": "$250,000"
  },
  "appeal_info": [
    {
      "case_no": "2024-001",
      "status": "Pending",
      "filed_date": "2024-01-01"
    }
  ]
}
```

### Result Types

1. **Successful Extraction**: `extracted_data.json` contains property details
2. **No Records Found**: `no_records_found.txt` indicates no data for roll number
3. **Processing Error**: `error_log.txt` contains error details and traceback

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. "URL not found in environment variables"
**Problem**: The .env file is missing or incorrect
**Solution**: 
```bash
# Create .env file
echo "URL=https://arb-website.com" > .env
```

#### 2. "Browser not started" Error
**Problem**: Playwright couldn't launch Firefox
**Solution**:
```bash
# Install Firefox for Playwright
playwright install firefox
```

#### 3. Processing Hangs
**Problem**: The system is stuck processing
**Solution**:
```bash
# Force shutdown
curl -X POST http://localhost:8000/shutdown

# Restart the server
python -m uvicorn src.creiq.api:app --reload
```

#### 4. No Data Extracted
**Problem**: Results show empty property_info
**Solution**: 
- The website structure may have changed
- Contact support to update selectors

#### 5. Excel File Not Accepted
**Problem**: API returns "Invalid file type"
**Solution**:
- Ensure file extension is .xlsx (not .xls)
- Check file isn't corrupted
- Try saving as new Excel file

### Debug Mode

Enable detailed logging:
```bash
# Set environment variable
export LOG_LEVEL=DEBUG

# Or in .env file
LOG_LEVEL=DEBUG
```

Run with visible browser:
```bash
# In .env file
HEADLESS=false
```

## 📝 Common Tasks

### Process a Single Roll Number
Create an Excel file with one roll number and upload it.

### Batch Processing Large Files
For files with 100+ roll numbers:
1. Split into smaller batches (50 per file)
2. Process sequentially
3. Monitor for errors

### Resume Failed Processing
1. Check which roll numbers failed
2. Create new Excel with only failed numbers
3. Reprocess

### Export All Results
```python
import os
import json

results = {}
results_dir = "data/results"

for roll_dir in os.listdir(results_dir):
    json_file = os.path.join(results_dir, roll_dir, "extracted_data.json")
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            results[roll_dir] = json.load(f)

# Save combined results
with open("all_results.json", 'w') as f:
    json.dump(results, f, indent=2)
```

## ❓ FAQ

### Q: How long does processing take?
**A**: Typically 10-30 seconds per roll number, depending on website response time.

### Q: Can I process multiple files simultaneously?
**A**: No, the system processes one file at a time to avoid overwhelming the website.

### Q: What happens if the process is interrupted?
**A**: The system saves results for each roll number as it completes. You can resume with unprocessed numbers.

### Q: How do I know which roll numbers failed?
**A**: Check directories in `data/results/` for `error_log.txt` files.

### Q: Can I customize what data is extracted?
**A**: Yes, but it requires modifying the code. See the Technical Guide for details.

### Q: Is there a limit on file size?
**A**: The system can handle large files, but processing time increases linearly.

### Q: Can I schedule automatic processing?
**A**: Not built-in, but you can use cron (Linux) or Task Scheduler (Windows) to call the API.

## 🆘 Getting Help

### Log Files
Check logs for detailed error information:
- API logs: Console output where server is running
- Processing logs: In individual result directories

### Support Channels
1. Check existing documentation
2. Review error logs
3. Test with a single roll number
4. Contact technical support with:
   - Error messages
   - Log files
   - Steps to reproduce

## 🎓 Best Practices

1. **Test First**: Always test with a small batch before processing large files
2. **Monitor Progress**: Keep the status endpoint open during processing
3. **Save Results**: Backup the `data/results` directory regularly
4. **Clean Up**: Periodically archive old results to save disk space
5. **Error Recovery**: Keep track of failed roll numbers for reprocessing
6. **Regular Updates**: Keep the system updated for website changes

## 🔐 Security Notes

- Never share your .env file
- Restrict access to the API endpoint in production
- Regularly review and clean uploaded files
- Use HTTPS in production environments
- Implement authentication for public deployments 