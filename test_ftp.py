#!/usr/bin/env python3
"""Test FTP connection and functionality"""

import ftplib
import io
import os
from app.core.config import settings

def test_ftp_connection():
    """Test basic FTP connection"""
    print("Testing FTP Connection...")
    print(f"Host: {settings.ftp_host}")
    print(f"Port: {settings.ftp_port}")
    print(f"User: {settings.ftp_user}")
    print(f"Base Path: {settings.ftp_base_path}")
    print(f"Files Path: {settings.ftp_files_path}")
    print(f"CSV Path: {settings.ftp_csv_path}")
    print("-" * 50)
    
    ftp = ftplib.FTP()
    
    try:
        # Test connection
        print("1. Testing connection...")
        ftp.connect(settings.ftp_host, settings.ftp_port)
        print("   ✓ Connection successful")
        
        # Test login
        print("2. Testing login...")
        ftp.login(settings.ftp_user, settings.ftp_password)
        print("   ✓ Login successful")
        
        # Get welcome message
        print(f"3. Server welcome: {ftp.getwelcome()}")
        
        # Test directory listing
        print("4. Testing directory listing...")
        files = ftp.nlst()
        print(f"   ✓ Root directory contains {len(files)} items")
        for f in files[:5]:  # Show first 5 items
            print(f"     - {f}")
        if len(files) > 5:
            print(f"     ... and {len(files) - 5} more")
        
        # Test changing to base directory
        print("5. Testing base directory access...")
        try:
            ftp.cwd(settings.ftp_base_path)
            print(f"   ✓ Successfully changed to {settings.ftp_base_path}")
            base_files = ftp.nlst()
            print(f"   ✓ Base directory contains {len(base_files)} items")
        except ftplib.error_perm as e:
            print(f"   ❌ Cannot access base directory: {e}")
            print("   → This directory might not exist or have permission issues")
        
        # Test directory creation
        print("6. Testing directory creation...")
        test_dir = f"{settings.ftp_base_path}/test_dir"
        try:
            ftp.mkd(test_dir)
            print(f"   ✓ Created test directory: {test_dir}")
            # Clean up
            ftp.rmd(test_dir)
            print("   ✓ Cleaned up test directory")
        except ftplib.error_perm as e:
            print(f"   ❌ Cannot create directory: {e}")
            print("   → Check permissions or if directory already exists")
        
        # Test file upload
        print("7. Testing file upload...")
        test_content = b"This is a test file for FTP upload"
        test_filename = "test_upload.txt"
        try:
            # Ensure we're in base directory
            ftp.cwd('/')
            if settings.ftp_base_path:
                ftp.cwd(settings.ftp_base_path)
            
            bio = io.BytesIO(test_content)
            ftp.storbinary(f'STOR {test_filename}', bio)
            print(f"   ✓ Uploaded test file: {test_filename}")
            
            # Clean up
            ftp.delete(test_filename)
            print("   ✓ Cleaned up test file")
        except ftplib.error_perm as e:
            print(f"   ❌ Cannot upload file: {e}")
            print("   → Check upload permissions")
        
        print("\n✅ FTP connection test completed successfully!")
        return True
        
    except ftplib.error_perm as e:
        print(f"\n❌ FTP Permission Error: {e}")
        return False
    except ftplib.error_temp as e:
        print(f"\n❌ FTP Temporary Error: {e}")
        return False
    except Exception as e:
        print(f"\n❌ FTP Connection Error: {e}")
        return False
    finally:
        try:
            ftp.quit()
        except:
            ftp.close()

def test_network_connectivity():
    """Test network connectivity to FTP server"""
    import socket
    
    print("Testing Network Connectivity...")
    print(f"Testing connection to {settings.ftp_host}:{settings.ftp_port}")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((settings.ftp_host, settings.ftp_port))
        sock.close()
        
        if result == 0:
            print("   ✓ Network connection successful")
            return True
        else:
            print(f"   ❌ Network connection failed (error code: {result})")
            return False
    except Exception as e:
        print(f"   ❌ Network test error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("FTP CONNECTIVITY TEST")
    print("=" * 60)
    
    # Test network first
    if test_network_connectivity():
        print()
        # If network is ok, test FTP
        test_ftp_connection()
    else:
        print("\n❌ Network connectivity failed - FTP test skipped")
    
    print("\n" + "=" * 60)