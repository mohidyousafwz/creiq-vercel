#!/usr/bin/env python3
"""Test Supabase connection and database operations."""
import os
import sys
from pathlib import Path
from datetime import datetime

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()


def test_supabase_connection():
    """Test connection to Supabase."""
    # Get Supabase credentials
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url or not supabase_key:
        print("❌ Error: SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        print("\nPlease add the following to your .env file:")
        print("SUPABASE_URL=https://your-project.supabase.co")
        print("SUPABASE_KEY=your-anon-key-here")
        return False
    
    try:
        # Create Supabase client
        print(f"🔗 Connecting to Supabase: {supabase_url}")
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Test connection by listing tables
        print("✅ Successfully connected to Supabase!")
        
        # Try to query roll_numbers table
        print("\n📊 Testing database queries...")
        
        # Count roll numbers
        result = supabase.table('roll_numbers').select("*", count='exact').execute()
        print(f"✅ Found {result.count} roll numbers in database")
        
        # Count appeals
        result = supabase.table('appeals').select("*", count='exact').execute()
        print(f"✅ Found {result.count} appeals in database")
        
        # Test insert (optional)
        test_roll = f"TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        print(f"\n🧪 Testing insert with roll number: {test_roll}")
        
        data = {
            "roll_number": test_roll,
            "property_description": "Test Property",
            "extraction_status": "test",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        result = supabase.table('roll_numbers').insert(data).execute()
        print("✅ Successfully inserted test record")
        
        # Clean up test record
        result = supabase.table('roll_numbers').delete().eq('roll_number', test_roll).execute()
        print("🧹 Cleaned up test record")
        
        print("\n✅ All Supabase tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error connecting to Supabase: {e}")
        print("\nPossible causes:")
        print("1. Invalid SUPABASE_URL or SUPABASE_KEY")
        print("2. Network connectivity issues")
        print("3. Database tables not created in Supabase")
        print("\nTo create tables in Supabase, run this SQL in Supabase SQL Editor:")
        print(get_create_tables_sql())
        return False


def get_create_tables_sql():
    """Get SQL to create tables in Supabase."""
    return """
-- Create roll_numbers table
CREATE TABLE IF NOT EXISTS roll_numbers (
    roll_number VARCHAR(50) PRIMARY KEY,
    property_description TEXT,
    municipality VARCHAR(200),
    classification VARCHAR(100),
    nbhd VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_extracted_at TIMESTAMP,
    extraction_status VARCHAR(50) DEFAULT 'pending',
    extraction_error TEXT
);

-- Create appeals table
CREATE TABLE IF NOT EXISTS appeals (
    id SERIAL PRIMARY KEY,
    appeal_number VARCHAR(50) UNIQUE NOT NULL,
    roll_number VARCHAR(50) NOT NULL REFERENCES roll_numbers(roll_number) ON DELETE CASCADE,
    appellant VARCHAR(500),
    representative VARCHAR(500),
    section VARCHAR(100),
    tax_date VARCHAR(50),
    hearing_number VARCHAR(50),
    hearing_date VARCHAR(50),
    status VARCHAR(100),
    board_order_number VARCHAR(100),
    appellant_name1 VARCHAR(500),
    appellant_name2 VARCHAR(500),
    filing_date VARCHAR(50),
    reason_for_appeal TEXT,
    decision_number VARCHAR(100),
    decision_mailing_date VARCHAR(50),
    decisions TEXT,
    decision_details TEXT,
    property_roll_number VARCHAR(50),
    property_municipality VARCHAR(200),
    property_classification VARCHAR(100),
    property_nbhd VARCHAR(50),
    property_description TEXT,
    summary_data JSONB,
    detail_data JSONB,
    detail_screenshot_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_roll_numbers_status ON roll_numbers(extraction_status);
CREATE INDEX idx_appeals_roll_number ON appeals(roll_number);
CREATE INDEX idx_appeals_status ON appeals(status);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers
CREATE TRIGGER update_roll_numbers_updated_at BEFORE UPDATE ON roll_numbers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_appeals_updated_at BEFORE UPDATE ON appeals
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
"""


if __name__ == "__main__":
    print("🚀 Testing Supabase connection...\n")
    test_supabase_connection() 