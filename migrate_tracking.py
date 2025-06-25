#!/usr/bin/env python3
"""
Migration script to transition from old single-file tracking to new JSON-based system
"""

import os
import json
from datetime import datetime
from email_tracking import EmailTracker

def migrate_old_tracking():
    """Migrate from old last_processed_email.txt to new JSON system"""
    
    print("CleanMail Tracking Migration Tool")
    print("=" * 50)
    
    # Check for old tracking file
    old_file = "last_processed_email.txt"
    if os.path.exists(old_file):
        print(f"Found old tracking file: {old_file}")
        
        try:
            with open(old_file, 'r') as f:
                old_email_id = f.read().strip()
            
            if old_email_id:
                print(f"Old last processed email ID: {old_email_id}")
                
                # Ask user which account this belongs to
                print("\nThis email ID needs to be assigned to an account.")
                print("Based on your config files, the main account appears to be: accounts@chrisharden.com")
                
                account = input("Enter the email account this ID belongs to (or press Enter for accounts@chrisharden.com): ").strip()
                if not account:
                    account = "accounts@chrisharden.com"
                
                # Create new tracker and migrate
                tracker = EmailTracker()
                tracker.update_last_processed_email(account, old_email_id, 0)
                
                print(f"\nMigrated old tracking data to new system for account: {account}")
                
                # Backup old file
                backup_file = f"{old_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(old_file, backup_file)
                print(f"Old tracking file backed up as: {backup_file}")
                
            else:
                print("Old tracking file is empty - no migration needed")
                
        except Exception as e:
            print(f"Error reading old tracking file: {e}")
    else:
        print("No old tracking file found - starting fresh")
    
    # Check for account-specific tracking files
    print("\nChecking for account-specific tracking files...")
    
    account_files = []
    for file in os.listdir('.'):
        if file.startswith('last_processed_email_') and file.endswith('.txt'):
            account_files.append(file)
    
    if account_files:
        print(f"Found {len(account_files)} account-specific tracking files:")
        tracker = EmailTracker()
        
        for file in account_files:
            print(f"  Processing: {file}")
            
            # Extract account from filename
            # Format: last_processed_email_accounts_at_chrisharden_com.txt
            account_part = file.replace('last_processed_email_', '').replace('.txt', '')
            account = account_part.replace('_at_', '@').replace('_', '.')
            
            try:
                with open(file, 'r') as f:
                    email_id = f.read().strip()
                
                if email_id:
                    tracker.update_last_processed_email(account, email_id, 0)
                    print(f"    Migrated {account}: {email_id}")
                    
                    # Backup file
                    backup_file = f"{file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    os.rename(file, backup_file)
                    print(f"    Backed up as: {backup_file}")
                else:
                    print(f"    File is empty - skipping")
                    
            except Exception as e:
                print(f"    Error processing {file}: {e}")
    else:
        print("No account-specific tracking files found")
    
    print("\nMigration complete!")
    
    # Show final status
    tracker = EmailTracker()
    accounts = tracker.list_all_accounts()
    
    if accounts:
        print(f"\nNow tracking {len(accounts)} accounts:")
        for email, data in accounts.items():
            last_id = data.get('last_processed_email_id', 'None')
            print(f"  - {email}: {last_id}")
    else:
        print("\nNo accounts are currently being tracked.")
    
    print(f"\nTracking data is now stored in: email_tracking.json")
    print("You can now use main_fixed.py which supports the new tracking system.")

def show_current_status():
    """Show current tracking status"""
    print("Current Tracking Status")
    print("=" * 30)
    
    tracker = EmailTracker()
    accounts = tracker.list_all_accounts()
    
    if not accounts:
        print("No accounts are currently being tracked.")
        return
    
    for email, data in accounts.items():
        print(f"\nAccount: {email}")
        print(f"  Last processed email: {data.get('last_processed_email_id', 'None')}")
        print(f"  Last processed date: {data.get('last_processed_date', 'Never')}")
        print(f"  Total emails processed: {data.get('total_processed', 0)}")
        print(f"  Total runs: {data.get('run_count', 0)}")
        print(f"  First run date: {data.get('first_run_date', 'Unknown')}")

def reset_account_tracking():
    """Reset tracking for a specific account"""
    tracker = EmailTracker()
    accounts = tracker.list_all_accounts()
    
    if not accounts:
        print("No accounts are currently being tracked.")
        return
    
    print("Currently tracked accounts:")
    for i, email in enumerate(accounts.keys(), 1):
        print(f"  {i}. {email}")
    
    try:
        choice = input("\nEnter account email to reset (or number): ").strip()
        
        if choice.isdigit():
            choice_num = int(choice) - 1
            if 0 <= choice_num < len(accounts):
                email = list(accounts.keys())[choice_num]
            else:
                print("Invalid number")
                return
        else:
            email = choice
        
        if email in accounts:
            confirm = input(f"Are you sure you want to reset tracking for {email}? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                tracker.reset_account(email)
            else:
                print("Reset cancelled")
        else:
            print(f"Account {email} not found")
            
    except ValueError:
        print("Invalid input")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "migrate":
            migrate_old_tracking()
        elif command == "status":
            show_current_status()
        elif command == "reset":
            reset_account_tracking()
        elif command == "export":
            tracker = EmailTracker()
            stats = tracker.export_stats()
            print("Statistics exported successfully")
        else:
            print("Unknown command. Available commands:")
            print("  migrate - Migrate from old tracking system")
            print("  status  - Show current tracking status")
            print("  reset   - Reset tracking for an account")
            print("  export  - Export tracking statistics")
    else:
        print("CleanMail Tracking Migration Tool")
        print("Available commands:")
        print("  python migrate_tracking.py migrate - Migrate from old system")
        print("  python migrate_tracking.py status  - Show current status")
        print("  python migrate_tracking.py reset   - Reset account tracking")
        print("  python migrate_tracking.py export  - Export statistics")
        print()
        
        # Default action - show status and offer migration
        show_current_status()
        
        if input("\nWould you like to run migration now? (y/n): ").strip().lower() in ['y', 'yes']:
            migrate_old_tracking()
