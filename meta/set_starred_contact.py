#!/usr/bin/env python3
"""
Simple script to set the starred contact for testing profile switching
"""
import json
import sys

def set_starred_contact(contact_id):
    """Set the starred contact ID"""
    data = {
        "starred_contact_id": contact_id
    }
    
    with open("current_starred.json", "w") as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Set starred contact to: {contact_id}")
    
    # Show mapping
    mapping = {
        '647': 'Bob',
        '416': 'Ava', 
        '289': 'Adam'
    }
    
    if contact_id in mapping:
        print(f"👤 Profile: {mapping[contact_id]}")
    else:
        print("⚠️  Unknown contact ID")

def clear_starred_contact():
    """Clear the starred contact"""
    try:
        import os
        os.remove("current_starred.json")
        print("✅ Cleared starred contact")
    except FileNotFoundError:
        print("ℹ️  No starred contact was set")

def show_current():
    """Show current starred contact"""
    try:
        with open("current_starred.json", "r") as f:
            data = json.load(f)
            contact_id = data.get("starred_contact_id")
            
            mapping = {
                '647': 'Bob',
                '416': 'Ava', 
                '289': 'Adam'
            }
            
            if contact_id in mapping:
                print(f"⭐ Current starred contact: {mapping[contact_id]} ({contact_id})")
            else:
                print(f"⭐ Current starred contact: {contact_id}")
    except FileNotFoundError:
        print("ℹ️  No starred contact set")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python set_starred_contact.py <contact_id>  # Set starred contact")
        print("  python set_starred_contact.py clear         # Clear starred contact")
        print("  python set_starred_contact.py show          # Show current")
        print("\nAvailable contacts:")
        print("  647 - Bob")
        print("  416 - Ava")
        print("  289 - Adam")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "clear":
        clear_starred_contact()
    elif command == "show":
        show_current()
    else:
        # Assume it's a contact ID
        set_starred_contact(command) 