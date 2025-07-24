#!/usr/bin/env python3
"""
Script to convert Firebase service account JSON to environment variables
This helps secure your Firebase credentials when pushing to GitHub
"""

import json
import os
import sys

def convert_service_account_to_env():
    """Convert Firebase service account JSON to environment variables"""
    
    # Check if service account file exists
    service_account_path = 'firebase-service-account.json'
    if not os.path.exists(service_account_path):
        print(f"Error: {service_account_path} not found!")
        print("Please ensure the Firebase service account file is in the current directory.")
        return False
    
    try:
        # Read the service account file
        with open(service_account_path, 'r') as f:
            service_account = json.load(f)
        
        # Create .env file content
        env_content = """# Firebase Configuration (Generated from service account)
FIREBASE_TYPE={}
FIREBASE_PROJECT_ID={}
FIREBASE_PRIVATE_KEY_ID={}
FIREBASE_PRIVATE_KEY={}
FIREBASE_CLIENT_EMAIL={}
FIREBASE_CLIENT_ID={}
FIREBASE_AUTH_URI={}
FIREBASE_TOKEN_URI={}
FIREBASE_AUTH_PROVIDER_X509_CERT_URL={}
FIREBASE_CLIENT_X509_CERT_URL={}
FIREBASE_UNIVERSE_DOMAIN={}

# Database Configuration
USE_FIRESTORE=true

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000
""".format(
            service_account.get('type', ''),
            service_account.get('project_id', ''),
            service_account.get('private_key_id', ''),
            service_account.get('private_key', '').replace('\n', '\\n'),
            service_account.get('client_email', ''),
            service_account.get('client_id', ''),
            service_account.get('auth_uri', ''),
            service_account.get('token_uri', ''),
            service_account.get('auth_provider_x509_cert_url', ''),
            service_account.get('client_x509_cert_url', ''),
            service_account.get('universe_domain', '')
        )
        
        # Write to .env file
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("✅ Successfully converted Firebase service account to environment variables!")
        print("📁 Created .env file with your Firebase credentials")
        print("🔒 The .env file is already in .gitignore and will not be committed")
        print("\n📋 Next steps:")
        print("1. Add your environment variables to GitHub Secrets:")
        print("   - Go to your GitHub repository")
        print("   - Navigate to Settings > Secrets and variables > Actions")
        print("   - Add each environment variable as a repository secret")
        print("2. For deployment, set these environment variables in your hosting platform")
        print("3. You can now safely delete the firebase-service-account.json file")
        
        return True
        
    except Exception as e:
        print(f"Error converting service account: {e}")
        return False

def show_github_secrets_instructions():
    """Show instructions for setting up GitHub Secrets"""
    print("\n🔐 GitHub Secrets Setup Instructions:")
    print("=" * 50)
    print("1. Go to your GitHub repository")
    print("2. Click on 'Settings' tab")
    print("3. In the left sidebar, click 'Secrets and variables' > 'Actions'")
    print("4. Click 'New repository secret'")
    print("5. Add each of these secrets:")
    print("\n   Required secrets:")
    print("   - FIREBASE_TYPE")
    print("   - FIREBASE_PROJECT_ID") 
    print("   - FIREBASE_PRIVATE_KEY_ID")
    print("   - FIREBASE_PRIVATE_KEY")
    print("   - FIREBASE_CLIENT_EMAIL")
    print("   - FIREBASE_CLIENT_ID")
    print("   - FIREBASE_AUTH_URI")
    print("   - FIREBASE_TOKEN_URI")
    print("   - FIREBASE_AUTH_PROVIDER_X509_CERT_URL")
    print("   - FIREBASE_CLIENT_X509_CERT_URL")
    print("   - FIREBASE_UNIVERSE_DOMAIN")
    print("\n   Optional secrets:")
    print("   - API_HOST")
    print("   - API_PORT")
    print("   - ALLOWED_ORIGINS")

if __name__ == "__main__":
    print("🔧 Firebase Service Account to Environment Variables Converter")
    print("=" * 60)
    
    if convert_service_account_to_env():
        show_github_secrets_instructions()
    else:
        sys.exit(1) 