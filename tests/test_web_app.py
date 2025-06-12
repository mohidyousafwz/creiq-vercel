"""
Comprehensive tests for CREIQ Web Dashboard.
"""
import pytest
import asyncio
import json
import io
import csv
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Import the app and dependencies
from src.creiq.web_app import app, get_db, add_log, active_extractions
from src.creiq.database.database import Base
from src.creiq.database.models import RollNumber, Appeal
from src.creiq.config.settings import PASSCODE

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_db():
    """Clear database before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    # Clear active extractions
    active_extractions.clear()
    yield


@pytest.fixture
def authenticated_client():
    """Create an authenticated test client."""
    with client:
        # Login first
        response = client.post("/login", data={"passcode": PASSCODE})
        assert response.status_code == 200
        yield client


@pytest.fixture
def sample_roll_numbers(authenticated_client):
    """Create sample roll numbers in database."""
    db = TestingSessionLocal()
    try:
        # Create roll numbers
        roll1 = RollNumber(
            roll_number="38-29-300-012-10400-0000",
            property_description="429 EXMOUTH ST",
            municipality="SARNIA",
            extraction_status="completed",
            last_extracted_at=datetime.now()
        )
        roll2 = RollNumber(
            roll_number="38-29-300-012-10500-0000",
            property_description="431 EXMOUTH ST",
            municipality="SARNIA",
            extraction_status="pending"
        )
        db.add_all([roll1, roll2])
        
        # Create appeals for roll1
        appeal1 = Appeal(
            appeal_number="1194369",
            roll_number="38-29-300-012-10400-0000",
            appellant="JOHN DOE",
            status="Closed"
        )
        appeal2 = Appeal(
            appeal_number="138497",
            roll_number="38-29-300-012-10400-0000",
            appellant="JANE DOE",
            status="Open"
        )
        db.add_all([appeal1, appeal2])
        db.commit()
        
        return [roll1, roll2]
    finally:
        db.close()


class TestAuthentication:
    """Test authentication functionality."""
    
    def test_login_page(self):
        """Test login page loads."""
        response = client.get("/")
        assert response.status_code == 200
        assert "Enter your passcode" in response.text
    
    def test_login_success(self):
        """Test successful login."""
        response = client.post("/login", data={"passcode": PASSCODE})
        assert response.status_code == 200
        assert response.url.path == "/dashboard"
    
    def test_login_failure(self):
        """Test failed login."""
        response = client.post("/login", data={"passcode": "wrong"}, follow_redirects=False)
        assert response.status_code == 200
        # When login fails, we stay on the login page and show an error
        # The response includes the login template with error message
        assert "request" in response.context
    
    def test_logout(self, authenticated_client):
        """Test logout functionality."""
        response = authenticated_client.get("/logout")
        assert response.status_code == 200
        assert response.url.path == "/"
    
    def test_protected_route_without_auth(self):
        """Test accessing protected route without authentication."""
        response = client.get("/dashboard")
        # Should get 401 without auth
        assert response.status_code == 401


class TestDashboard:
    """Test dashboard functionality."""
    
    def test_dashboard_loads(self, authenticated_client, sample_roll_numbers):
        """Test dashboard page loads with data."""
        response = authenticated_client.get("/dashboard")
        assert response.status_code == 200
        assert "Dashboard" in response.text
        assert "Total Roll Numbers" in response.text
        assert "Total Appeals" in response.text
    
    def test_dashboard_stats_api(self, authenticated_client, sample_roll_numbers):
        """Test dashboard statistics API."""
        response = authenticated_client.get("/api/dashboard/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["total_roll_numbers"] == 2
        assert data["total_appeals"] == 2
        assert "success_rate" in data
        assert "status_breakdown" in data
        assert "appeal_status" in data


class TestRollNumbers:
    """Test roll numbers functionality."""
    
    def test_roll_numbers_page(self, authenticated_client):
        """Test roll numbers page loads."""
        response = authenticated_client.get("/roll-numbers")
        assert response.status_code == 200
        assert "Roll Numbers" in response.text
    
    def test_roll_numbers_search_api(self, authenticated_client, sample_roll_numbers):
        """Test roll numbers search API."""
        # Search all
        response = authenticated_client.get("/api/roll-numbers/search")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["roll_numbers"]) == 2
        
        # Search with query
        response = authenticated_client.get("/api/roll-numbers/search?q=10400")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["roll_numbers"][0]["roll_number"] == "38-29-300-012-10400-0000"
    
    def test_roll_number_detail(self, authenticated_client, sample_roll_numbers):
        """Test roll number detail page."""
        response = authenticated_client.get("/roll-numbers/38-29-300-012-10400-0000")
        assert response.status_code == 200
        assert "38-29-300-012-10400-0000" in response.text
        assert "429 EXMOUTH ST" in response.text
        assert "Appeals (2)" in response.text
    
    def test_roll_number_not_found(self, authenticated_client):
        """Test roll number not found."""
        response = authenticated_client.get("/roll-numbers/invalid-roll-number")
        assert response.status_code == 404

    def test_delete_roll_number(self, authenticated_client, sample_roll_numbers):
        """Test deleting a roll number and its appeals."""
        response = authenticated_client.delete("/api/roll_numbers/38-29-300-012-10400-0000")
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
        
        # Verify it's actually deleted
        response = authenticated_client.get("/roll-numbers/38-29-300-012-10400-0000")
        assert response.status_code == 404
    
    def test_delete_nonexistent_roll_number(self, authenticated_client):
        """Test deleting a non-existent roll number."""
        response = authenticated_client.delete("/api/roll_numbers/nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Roll number not found"


class TestAppeals:
    """Test appeals functionality."""
    
    def test_delete_appeal(self, authenticated_client, sample_roll_numbers):
        """Test deleting an individual appeal."""
        # Get the first appeal
        db = TestingSessionLocal()
        try:
            appeal = db.query(Appeal).first()
            appeal_id = appeal.id
        finally:
            db.close()
        
        response = authenticated_client.delete(f"/api/appeals/{appeal_id}")
        assert response.status_code == 200
        data = response.json()
        assert "deleted successfully" in data["message"]
        
        # Verify it's actually deleted
        db = TestingSessionLocal()
        try:
            deleted_appeal = db.query(Appeal).filter(Appeal.id == appeal_id).first()
            assert deleted_appeal is None
        finally:
            db.close()
    
    def test_delete_nonexistent_appeal(self, authenticated_client):
        """Test deleting a non-existent appeal."""
        response = authenticated_client.delete("/api/appeals/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Appeal not found"


class TestFileOperations:
    """Test file upload and export functionality."""
    
    def test_csv_upload(self, authenticated_client):
        """Test CSV file upload."""
        csv_content = "38-29-300-012-10600-0000\n38-29-300-012-10700-0000"
        csv_file = io.BytesIO(csv_content.encode())
        
        response = authenticated_client.post(
            "/api/roll-numbers/upload",
            files={"file": ("test.csv", csv_file, "text/csv")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["new"] == 2
        assert data["existing"] == 0
    
    def test_csv_upload_with_duplicates(self, authenticated_client, sample_roll_numbers):
        """Test CSV upload with duplicate roll numbers."""
        csv_content = "38-29-300-012-10400-0000\n38-29-300-012-10800-0000"
        csv_file = io.BytesIO(csv_content.encode())
        
        response = authenticated_client.post(
            "/api/roll-numbers/upload",
            files={"file": ("test.csv", csv_file, "text/csv")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["new"] == 1
        assert data["existing"] == 1
    
    def test_invalid_file_upload(self, authenticated_client):
        """Test uploading non-CSV file."""
        response = authenticated_client.post(
            "/api/roll-numbers/upload",
            files={"file": ("test.txt", b"invalid content", "text/plain")}
        )
        assert response.status_code == 400
        assert "Only CSV files are allowed" in response.json()["detail"]
    
    def test_csv_export(self, authenticated_client, sample_roll_numbers):
        """Test CSV export functionality."""
        # Export all
        response = authenticated_client.get("/api/roll-numbers/export?type=all")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        
        # Parse CSV
        content = response.content.decode()
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) == 3  # Header + 2 roll numbers
        assert rows[0][0] == "Roll Number"
        
        # Export processed only
        response = authenticated_client.get("/api/roll-numbers/export?type=processed")
        assert response.status_code == 200
        content = response.content.decode()
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) == 2  # Header + 1 completed roll number


class TestProcessing:
    """Test extraction processing functionality."""
    
    @patch('src.creiq.web_app.run_extraction_task')
    def test_process_roll_numbers(self, mock_task, authenticated_client):
        """Test starting roll number processing."""
        response = authenticated_client.post(
            "/api/roll-numbers/process",
            json={"roll_numbers": ["38-29-300-012-10400-0000"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["roll_numbers"] == ["38-29-300-012-10400-0000"]
        
        # Check that extraction tracking was initialized
        assert "38-29-300-012-10400-0000" in active_extractions
        assert active_extractions["38-29-300-012-10400-0000"]["status"] == "queued"
    
    def test_process_empty_list(self, authenticated_client):
        """Test processing with empty roll numbers list."""
        response = authenticated_client.post(
            "/api/roll-numbers/process",
            json={"roll_numbers": []}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["roll_numbers"] == []


class TestOtherPages:
    """Test other dashboard pages."""
    
    def test_logs_page(self, authenticated_client):
        """Test logs page loads."""
        response = authenticated_client.get("/logs")
        assert response.status_code == 200
        assert "Scraper Logs" in response.text
        assert "Real-time Logs" in response.text
    
    def test_settings_page(self, authenticated_client):
        """Test settings page loads."""
        response = authenticated_client.get("/settings")
        assert response.status_code == 200
        assert "Settings" in response.text
        assert "Extraction Settings" in response.text
    
    def test_guide_page(self, authenticated_client):
        """Test user guide page loads."""
        response = authenticated_client.get("/guide")
        assert response.status_code == 200
        assert "User Guide" in response.text
        assert "Getting Started" in response.text
    
    def test_health_page(self, authenticated_client):
        """Test system health page loads."""
        response = authenticated_client.get("/health-status")
        assert response.status_code == 200
        assert "System Health" in response.text
        assert "Database" in response.text


class TestErrorHandling:
    """Test error handling and resilience."""
    
    @patch('src.creiq.database.service.DatabaseService.get_roll_number')
    def test_database_error_handling(self, mock_get, authenticated_client):
        """Test handling of database errors."""
        mock_get.side_effect = Exception("Database error")
        
        # Should handle the error gracefully
        response = authenticated_client.get("/roll-numbers/test-roll-number")
        # The error is caught and results in a 500 error
        assert response.status_code == 500
    
    @patch('src.creiq.utils.roll_number_reader.read_roll_numbers_from_csv')
    async def test_upload_error_handling(self, mock_read, authenticated_client):
        """Test handling of upload errors."""
        mock_read.side_effect = Exception("Upload error")
        
        csv_file = io.BytesIO(b"test")
        response = authenticated_client.post(
            "/api/roll-numbers/upload",
            files={"file": ("test.csv", csv_file, "text/csv")}
        )
        assert response.status_code == 500
        assert "Upload error" in response.json()["detail"]


class TestLogging:
    """Test logging functionality."""
    
    @pytest.mark.asyncio
    async def test_add_log(self):
        """Test adding log entries."""
        from src.creiq.web_app import extraction_logs
        
        # Clear logs
        extraction_logs.clear()
        
        # Add log
        await add_log("INFO", "Test message", {"detail": "test"})
        
        assert len(extraction_logs) == 1
        assert extraction_logs[0]["level"] == "INFO"
        assert extraction_logs[0]["message"] == "Test message"
        assert extraction_logs[0]["details"]["detail"] == "test"
    
    @pytest.mark.asyncio
    async def test_log_limit(self):
        """Test log limit enforcement."""
        from src.creiq.web_app import extraction_logs
        
        # Clear logs
        extraction_logs.clear()
        
        # Add more than 1000 logs
        for i in range(1100):
            await add_log("INFO", f"Message {i}")
        
        assert len(extraction_logs) == 1000
        assert extraction_logs[0]["message"] == "Message 1099"  # Most recent
        assert extraction_logs[999]["message"] == "Message 100"  # Oldest kept


class TestDatabaseManagement:
    """Test database management endpoints."""
    
    def test_get_database_info(self, authenticated_client):
        """Test getting database information."""
        response = authenticated_client.get("/api/database/info")
        assert response.status_code == 200
        
        data = response.json()
        assert "size" in data
        assert "type" in data
        assert "backups" in data
        assert isinstance(data["backups"], list)
    
    def test_backup_database(self, authenticated_client):
        """Test database backup creation."""
        response = authenticated_client.post("/api/database/backup")
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert "filename" in data
        assert "size" in data
        
        # Verify backup file exists
        import os
        backup_path = os.path.join("backups", data["filename"])
        assert os.path.exists(backup_path)
        
        # Clean up
        os.remove(backup_path)
    
    def test_download_backup(self, authenticated_client):
        """Test downloading a backup file."""
        # First create a backup
        backup_response = authenticated_client.post("/api/database/backup")
        backup_data = backup_response.json()
        filename = backup_data["filename"]
        
        # Download the backup
        response = authenticated_client.get(f"/api/database/backup/{filename}")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/octet-stream"
        
        # Clean up
        import os
        os.remove(os.path.join("backups", filename))
    
    def test_download_nonexistent_backup(self, authenticated_client):
        """Test downloading a non-existent backup."""
        response = authenticated_client.get("/api/database/backup/nonexistent.db")
        assert response.status_code == 404
    
    def test_delete_backup(self, authenticated_client):
        """Test deleting a backup file."""
        # First create a backup
        backup_response = authenticated_client.post("/api/database/backup")
        backup_data = backup_response.json()
        filename = backup_data["filename"]
        
        # Delete the backup
        response = authenticated_client.delete(f"/api/database/backup/{filename}")
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify it's deleted
        import os
        assert not os.path.exists(os.path.join("backups", filename))
    
    def test_delete_nonexistent_backup(self, authenticated_client):
        """Test deleting a non-existent backup."""
        response = authenticated_client.delete("/api/database/backup/nonexistent.db")
        assert response.status_code == 404
    
    def test_delete_backup_security(self, authenticated_client):
        """Test that directory traversal is prevented in delete."""
        response = authenticated_client.delete("/api/database/backup/../../../important.db")
        assert response.status_code in [403, 404]  # Either forbidden or not found
    
    def test_purge_database_wrong_passcode(self, authenticated_client):
        """Test purging database with wrong passcode."""
        response = authenticated_client.post("/api/database/purge", data={"passcode": "wrong"})
        assert response.status_code == 403
        assert response.json()["detail"] == "Invalid passcode"
    
    def test_purge_database_correct_passcode(self, authenticated_client, test_db):
        """Test purging database with correct passcode."""
        # Add some test data
        roll_number = RollNumber(
            roll_number="12-34-567-890-12345-6789",
            extraction_status="completed"
        )
        test_db.add(roll_number)
        test_db.commit()
        
        # Purge database
        response = authenticated_client.post("/api/database/purge", data={"passcode": PASSCODE})
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        # Verify data is deleted
        assert test_db.query(RollNumber).count() == 0
    
    def test_import_database_wrong_passcode(self, authenticated_client):
        """Test importing database with wrong passcode."""
        # Create a dummy file
        import io
        file = io.BytesIO(b"dummy content")
        
        response = authenticated_client.post(
            "/api/database/import",
            data={"passcode": "wrong"},
            files={"file": ("test.db", file, "application/octet-stream")}
        )
        assert response.status_code == 403
    
    def test_import_database_wrong_file_type(self, authenticated_client):
        """Test importing non-.db file."""
        import io
        file = io.BytesIO(b"dummy content")
        
        response = authenticated_client.post(
            "/api/database/import",
            data={"passcode": PASSCODE},
            files={"file": ("test.txt", file, "text/plain")}
        )
        assert response.status_code == 400
        assert "Only .db files are allowed" in response.json()["detail"]
    
    def test_backup_retention(self, authenticated_client):
        """Test that only 3 backups are retained."""
        import os
        import shutil
        
        # Create backups directory
        os.makedirs("backups", exist_ok=True)
        
        # Create 4 backups
        for i in range(4):
            response = authenticated_client.post("/api/database/backup")
            assert response.status_code == 200
            # Add small delay to ensure different timestamps
            import time
            time.sleep(0.1)
        
        # Check that only 3 backups exist
        backup_files = list(Path("backups").glob("*.db"))
        assert len(backup_files) == 3
        
        # Clean up
        shutil.rmtree("backups", ignore_errors=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 