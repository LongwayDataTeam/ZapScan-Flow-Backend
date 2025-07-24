# 🔐 Security Setup Guide

This guide will help you secure your Firebase credentials and other sensitive information using environment variables and GitHub Secrets.

## 🚨 Important Security Notice

Your Firebase service account file (`firebase-service-account.json`) contains sensitive credentials that should **NEVER** be committed to a public repository. This guide will help you convert these credentials to environment variables.

## 📋 Prerequisites

- Your Firebase service account JSON file (`firebase-service-account.json`)
- Access to your GitHub repository settings

## 🔧 Step 1: Convert Service Account to Environment Variables

### Option A: Use the Automated Script (Recommended)

1. Navigate to the backend directory:
   ```bash
   cd ZapScan-Flow-backend
   ```

2. Run the conversion script:
   ```bash
   python setup_env.py
   ```

3. The script will:
   - Read your `firebase-service-account.json` file
   - Create a `.env` file with all the credentials
   - Show you the next steps

### Option B: Manual Conversion

If you prefer to do it manually, copy the values from your `firebase-service-account.json` to your `.env` file:

```env
# Firebase Configuration
FIREBASE_TYPE=service_account
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----\nYour-Private-Key-Here\n-----END PRIVATE KEY-----\n
FIREBASE_CLIENT_EMAIL=your-service-account@your-project.iam.gserviceaccount.com
FIREBASE_CLIENT_ID=your-client-id
FIREBASE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
FIREBASE_TOKEN_URI=https://oauth2.googleapis.com/token
FIREBASE_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
FIREBASE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com
FIREBASE_UNIVERSE_DOMAIN=googleapis.com

# Database Configuration
USE_FIRESTORE=true

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000
```

## 🔐 Step 2: Set Up GitHub Secrets

### 2.1 Navigate to GitHub Repository Settings

1. Go to your GitHub repository
2. Click on the **Settings** tab
3. In the left sidebar, click **Secrets and variables** → **Actions**

### 2.2 Add Repository Secrets

Click **New repository secret** and add each of these secrets:

#### Required Secrets:
- `FIREBASE_TYPE` = `service_account`
- `FIREBASE_PROJECT_ID` = Your Firebase project ID
- `FIREBASE_PRIVATE_KEY_ID` = Your private key ID
- `FIREBASE_PRIVATE_KEY` = Your private key (with `\n` for line breaks)
- `FIREBASE_CLIENT_EMAIL` = Your service account email
- `FIREBASE_CLIENT_ID` = Your client ID
- `FIREBASE_AUTH_URI` = `https://accounts.google.com/o/oauth2/auth`
- `FIREBASE_TOKEN_URI` = `https://oauth2.googleapis.com/token`
- `FIREBASE_AUTH_PROVIDER_X509_CERT_URL` = `https://www.googleapis.com/oauth2/v1/certs`
- `FIREBASE_CLIENT_X509_CERT_URL` = Your client x509 cert URL
- `FIREBASE_UNIVERSE_DOMAIN` = `googleapis.com`

#### Optional Secrets:
- `API_HOST` = `0.0.0.0` (or your preferred host)
- `API_PORT` = `8000` (or your preferred port)
- `ALLOWED_ORIGINS` = `http://localhost:3000` (or your frontend URL)

### 2.3 Example: Adding FIREBASE_PRIVATE_KEY

For the `FIREBASE_PRIVATE_KEY`, you need to format it correctly:

1. Copy the private key from your JSON file
2. Replace all line breaks with `\n`
3. Add it as a secret

Example:
```
-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCmq2SucfwkA75r\n...\n-----END PRIVATE KEY-----\n
```

## 🧪 Step 3: Test Your Setup

### Local Testing

1. Make sure your `.env` file is created
2. Run your application:
   ```bash
   python main.py
   ```

### GitHub Actions Testing

The repository includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that will automatically test your environment variables when you push to the main branch.

## 🗑️ Step 4: Clean Up (After Testing)

Once you've confirmed everything works:

1. **Delete the service account file** (optional but recommended):
   ```bash
   rm firebase-service-account.json
   ```

2. **Verify `.gitignore` includes**:
   - `.env`
   - `firebase-service-account.json`

## 🔍 Step 5: Verify Security

### Check Your Repository

1. Ensure no sensitive files are committed:
   ```bash
   git status
   ```

2. Check that `.env` and `firebase-service-account.json` are not tracked:
   ```bash
   git ls-files | grep -E "\.(env|json)$"
   ```

### Test GitHub Actions

1. Push your changes to GitHub
2. Go to the **Actions** tab in your repository
3. Verify the workflow runs successfully with your secrets

## 🚀 Step 6: Deployment

### For Different Platforms

#### Heroku
```bash
heroku config:set FIREBASE_TYPE=service_account
heroku config:set FIREBASE_PROJECT_ID=your-project-id
# ... add all other variables
```

#### Railway
```bash
railway variables set FIREBASE_TYPE=service_account
railway variables set FIREBASE_PROJECT_ID=your-project-id
# ... add all other variables
```

#### Docker
```bash
docker run -e FIREBASE_TYPE=service_account -e FIREBASE_PROJECT_ID=your-project-id ...
```

## 🛡️ Security Best Practices

1. **Never commit sensitive files** to your repository
2. **Use different credentials** for development and production
3. **Rotate credentials regularly**
4. **Monitor access logs** in Firebase Console
5. **Use least privilege principle** for service accounts

## 🔧 Troubleshooting

### Common Issues

1. **"Firebase not initialized" error**
   - Check that all environment variables are set
   - Verify the private key format (with `\n`)

2. **"Permission denied" error**
   - Ensure your service account has the correct permissions
   - Check the Firebase project ID

3. **GitHub Actions failing**
   - Verify all secrets are added correctly
   - Check the secret names match exactly

### Debug Commands

```bash
# Test environment variables locally
python -c "import os; print('FIREBASE_PROJECT_ID:', os.getenv('FIREBASE_PROJECT_ID'))"

# Test Firestore connection
python -c "from app.services.firestore_service import FirestoreService; fs = FirestoreService(); print('Connection successful')"
```

## 📞 Support

If you encounter issues:

1. Check the Firebase Console for authentication errors
2. Verify your service account permissions
3. Test with a minimal example first
4. Check the application logs for detailed error messages

---

**Remember**: Security is an ongoing process. Regularly review and update your credentials and access controls. 