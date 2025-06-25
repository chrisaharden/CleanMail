import json
import os
from datetime import datetime
from typing import Dict, Optional

class EmailTracker:
    """Enhanced email tracking system with JSON-based persistence"""
    
    def __init__(self, tracking_file: str = "email_tracking.json"):
        self.tracking_file = tracking_file
        self.data = self._load_tracking_data()
    
    def _load_tracking_data(self) -> Dict:
        """Load tracking data from JSON file"""
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load tracking file {self.tracking_file}: {e}")
                print("Starting with empty tracking data.")
        
        return {}
    
    def _save_tracking_data(self):
        """Save tracking data to JSON file"""
        try:
            # Create backup of existing file
            if os.path.exists(self.tracking_file):
                backup_file = f"{self.tracking_file}.backup"
                with open(self.tracking_file, 'r') as src, open(backup_file, 'w') as dst:
                    dst.write(src.read())
            
            # Save new data
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            
            print(f"Tracking data saved to {self.tracking_file}")
        except IOError as e:
            print(f"Error saving tracking file: {e}")
    
    def get_last_processed_email(self, email_address: str) -> Optional[str]:
        """Get the last processed email ID for an account"""
        account_data = self.data.get(email_address, {})
        return account_data.get('last_processed_email_id')
    
    def update_last_processed_email(self, email_address: str, email_id: str, processed_count: int = 0):
        """Update the last processed email ID for an account"""
        if email_address not in self.data:
            self.data[email_address] = {
                'first_run_date': datetime.now().isoformat(),
                'total_processed': 0,
                'run_count': 0
            }
        
        account_data = self.data[email_address]
        account_data['last_processed_email_id'] = email_id
        account_data['last_processed_date'] = datetime.now().isoformat()
        account_data['total_processed'] = account_data.get('total_processed', 0) + processed_count
        account_data['run_count'] = account_data.get('run_count', 0) + 1
        account_data['last_run_processed_count'] = processed_count
        
        self._save_tracking_data()
        
        print(f"Updated tracking for {email_address}:")
        print(f"  - Last processed email: {email_id}")
        print(f"  - This run processed: {processed_count} emails")
        print(f"  - Total processed: {account_data['total_processed']} emails")
        print(f"  - Total runs: {account_data['run_count']}")
    
    def get_account_stats(self, email_address: str) -> Dict:
        """Get statistics for an account"""
        return self.data.get(email_address, {})
    
    def list_all_accounts(self) -> Dict:
        """Get all tracked accounts and their stats"""
        return self.data.copy()
    
    def reset_account(self, email_address: str):
        """Reset tracking for a specific account"""
        if email_address in self.data:
            del self.data[email_address]
            self._save_tracking_data()
            print(f"Reset tracking data for {email_address}")
        else:
            print(f"No tracking data found for {email_address}")
    
    def export_stats(self, output_file: str = "email_tracking_stats.json"):
        """Export detailed statistics"""
        stats = {
            'export_date': datetime.now().isoformat(),
            'total_accounts': len(self.data),
            'accounts': {}
        }
        
        for email, data in self.data.items():
            stats['accounts'][email] = {
                'total_processed': data.get('total_processed', 0),
                'run_count': data.get('run_count', 0),
                'first_run_date': data.get('first_run_date'),
                'last_processed_date': data.get('last_processed_date'),
                'last_run_processed_count': data.get('last_run_processed_count', 0),
                'has_last_processed_email': 'last_processed_email_id' in data
            }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        
        print(f"Statistics exported to {output_file}")
        return stats

# Utility functions for backward compatibility
def load_last_processed_email(email_address: str) -> Optional[str]:
    """Load last processed email using the enhanced tracker"""
    tracker = EmailTracker()
    return tracker.get_last_processed_email(email_address)

def save_last_processed_email_marker(email_address: str, email_id: str, processed_count: int = 0):
    """Save last processed email using the enhanced tracker"""
    tracker = EmailTracker()
    tracker.update_last_processed_email(email_address, email_id, processed_count)

if __name__ == "__main__":
    # Demo/test functionality
    tracker = EmailTracker()
    
    print("Email Tracking System Demo")
    print("=" * 40)
    
    # Show current accounts
    accounts = tracker.list_all_accounts()
    if accounts:
        print(f"Currently tracking {len(accounts)} accounts:")
        for email, data in accounts.items():
            print(f"  - {email}: {data.get('total_processed', 0)} emails processed")
    else:
        print("No accounts currently tracked.")
    
    print("\nTo use this system:")
    print("1. Replace the old tracking functions in main.py")
    print("2. Use EmailTracker class for enhanced features")
    print("3. Run tracker.export_stats() to get detailed reports")
