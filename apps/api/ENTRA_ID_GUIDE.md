# Azure Entra ID Authentication Guide

## Overview

This guide explains how to set up Azure Entra ID (formerly Azure AD) authentication for both the backend API and the Astro frontend.

## Architecture

```
┌─────────────────┐
│  Astro Frontend │
│  (Static Site)  │
└────────┬────────┘
         │ 1. User clicks "Sign In"
         │
         ▼
┌─────────────────────────┐
│  Microsoft Login Page   │
│  (login.microsoft.com)  │
└────────┬────────────────┘
         │ 2. User authenticates
         │ 3. Redirects back with token
         ▼
┌─────────────────┐
│  Astro Frontend │
│  (Has JWT)      │
└────────┬────────┘
         │ 4. API calls with Bearer token
         │
         ▼
┌─────────────────┐
│  FastAPI Backend│
│  (Validates JWT)│
└─────────────────┘
```

## Backend Setup (FastAPI)

### 1. Azure Portal Configuration

1. **Go to Azure Portal** → Azure Active Directory → App registrations
2. **Click "New registration"**
   - Name: `County Research API`
   - Supported account types: `Accounts in this organizational directory only`
   - Redirect URI: Leave blank for now
   - Click **Register**

3. **Note these values:**
   - Application (client) ID: `abc-123-def-456`
   - Directory (tenant) ID: `xyz-789-uvw-012`

4. **Configure API Permissions** (Optional)
   - Click "API permissions"
   - Add Microsoft Graph permissions if needed
   - Grant admin consent

5. **Configure Token Configuration**
   - Click "Token configuration"
   - Add optional claims if needed (email, name, etc.)

### 2. Backend Environment Variables

Update `apps/api/.env`:

```env
# Azure Entra ID
AZURE_TENANT_ID="xyz-789-uvw-012"
AZURE_CLIENT_ID="abc-123-def-456"
REQUIRE_AUTH="true"  # Set to true for production
```

### 3. How Backend Validates Tokens

The backend (`apps/api/auth/entra_id.py`) validates tokens using:

1. **JWKS (JSON Web Key Set)** - Downloads public keys from Microsoft
2. **JWT Verification** - Validates:
   - Signature (using public key)
   - Expiration (exp claim)
   - Audience (aud claim = CLIENT_ID)
   - Issuer (iss claim = Microsoft)

```python
# Token validation happens automatically in routes
@app.get("/jobs/{job_id}")
async def get_job(job_id: str, user: dict = Depends(get_current_user)):
    # user contains: user_id, email, name, roles, scopes
    return {"job_id": job_id, "user": user}
```

## Frontend Setup (Astro)

### 1. Azure Portal Configuration (Frontend)

1. **Go back to your App registration**
2. **Click "Authentication"**
3. **Add platform** → Single-page application
4. **Add Redirect URIs:**
   - Development: `http://localhost:4321/auth/callback`
   - Production: `https://your-site.azurestaticapps.net/auth/callback`
5. **Enable tokens:**
   - ✅ Access tokens
   - ✅ ID tokens
6. **Save**

### 2. Install MSAL for JavaScript

```bash
cd apps/web
npm install @azure/msal-browser
```

### 3. Create Auth Configuration

Create `apps/web/src/lib/auth.ts`:

```typescript
import { PublicClientApplication, type Configuration } from '@azure/msal-browser';

// MSAL configuration
const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.PUBLIC_AZURE_CLIENT_ID,
    authority: `https://login.microsoftonline.com/${import.meta.env.PUBLIC_AZURE_TENANT_ID}`,
    redirectUri: import.meta.env.PUBLIC_REDIRECT_URI || window.location.origin + '/auth/callback',
  },
  cache: {
    cacheLocation: 'localStorage',
    storeAuthStateInCookie: false,
  },
};

// Create MSAL instance
export const msalInstance = new PublicClientApplication(msalConfig);

// Initialize MSAL
export async function initializeMsal() {
  await msalInstance.initialize();
  await msalInstance.handleRedirectPromise();
}

// Login
export async function login() {
  try {
    await msalInstance.loginRedirect({
      scopes: ['openid', 'profile', 'email'],
    });
  } catch (error) {
    console.error('Login failed:', error);
  }
}

// Logout
export async function logout() {
  try {
    await msalInstance.logoutRedirect();
  } catch (error) {
    console.error('Logout failed:', error);
  }
}

// Get access token
export async function getAccessToken(): Promise<string | null> {
  const accounts = msalInstance.getAllAccounts();
  
  if (accounts.length === 0) {
    return null;
  }

  try {
    const response = await msalInstance.acquireTokenSilent({
      scopes: ['openid', 'profile', 'email'],
      account: accounts[0],
    });
    
    return response.idToken; // Use idToken for API calls
  } catch (error) {
    console.error('Token acquisition failed:', error);
    
    // If silent acquisition fails, try interactive
    try {
      const response = await msalInstance.acquireTokenRedirect({
        scopes: ['openid', 'profile', 'email'],
        account: accounts[0],
      });
      return response.idToken;
    } catch (redirectError) {
      console.error('Interactive token acquisition failed:', redirectError);
      return null;
    }
  }
}

// Get current user
export function getCurrentUser() {
  const accounts = msalInstance.getAllAccounts();
  return accounts.length > 0 ? accounts[0] : null;
}

// Check if user is authenticated
export function isAuthenticated(): boolean {
  return msalInstance.getAllAccounts().length > 0;
}
```

### 4. Create Auth Callback Page

Create `apps/web/src/pages/auth/callback.astro`:

```astro
---
// This page handles the redirect from Microsoft login
---

<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Authenticating...</title>
</head>
<body>
  <div style="display: flex; justify-content: center; align-items: center; height: 100vh;">
    <div style="text-align: center;">
      <h2>Authenticating...</h2>
      <p>Please wait while we complete your sign-in.</p>
    </div>
  </div>

  <script>
    import { msalInstance } from '../../lib/auth';

    // Handle redirect promise
    msalInstance.handleRedirectPromise()
      .then(() => {
        // Redirect to home page after successful login
        window.location.href = '/';
      })
      .catch((error) => {
        console.error('Authentication error:', error);
        alert('Authentication failed. Please try again.');
        window.location.href = '/';
      });
  </script>
</body>
</html>
```

### 5. Create API Client with Auth

Create `apps/web/src/lib/api.ts`:

```typescript
import { getAccessToken } from './auth';

const API_BASE_URL = import.meta.env.PUBLIC_API_URL || 'http://localhost:8000';

async function fetchWithAuth(url: string, options: RequestInit = {}) {
  const token = await getAccessToken();
  
  const headers = new Headers(options.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Token expired or invalid, redirect to login
      window.location.href = '/login';
      throw new Error('Authentication required');
    }
    throw new Error(`API error: ${response.statusText}`);
  }

  return response;
}

// API methods
export const api = {
  // Create job
  async createJob(formData: FormData) {
    const response = await fetchWithAuth('/jobs/create', {
      method: 'POST',
      body: formData,
    });
    return response.json();
  },

  // Get job status
  async getJobStatus(jobId: string) {
    const response = await fetchWithAuth(`/jobs/${jobId}`);
    return response.json();
  },

  // Download result
  async downloadResult(jobId: string, fileType: string) {
    const response = await fetchWithAuth(`/jobs/${jobId}/download/${fileType}`);
    return response.json();
  },

  // List jobs
  async listJobs(limit = 50, offset = 0) {
    const response = await fetchWithAuth(`/jobs?limit=${limit}&offset=${offset}`);
    return response.json();
  },

  // Delete job
  async deleteJob(jobId: string) {
    const response = await fetchWithAuth(`/jobs/${jobId}`, {
      method: 'DELETE',
    });
    return response.json();
  },
};
```

### 6. Update Main Layout

Update `apps/web/src/layouts/Layout.astro`:

```astro
---
// ... existing imports
---

<!DOCTYPE html>
<html lang="en">
<head>
  <!-- ... existing head content -->
</head>
<body>
  <nav>
    <div id="auth-status"></div>
  </nav>

  <slot />

  <script>
    import { initializeMsal, isAuthenticated, getCurrentUser, login, logout } from '../lib/auth';

    // Initialize MSAL on page load
    initializeMsal().then(() => {
      updateAuthStatus();
    });

    function updateAuthStatus() {
      const authStatus = document.getElementById('auth-status');
      if (!authStatus) return;

      if (isAuthenticated()) {
        const user = getCurrentUser();
        authStatus.innerHTML = `
          <span>Welcome, ${user?.name || user?.username}</span>
          <button id="logout-btn">Sign Out</button>
        `;
        
        document.getElementById('logout-btn')?.addEventListener('click', logout);
      } else {
        authStatus.innerHTML = `
          <button id="login-btn">Sign In</button>
        `;
        
        document.getElementById('login-btn')?.addEventListener('click', login);
      }
    }
  </script>
</body>
</html>
```

### 7. Environment Variables

Create `apps/web/.env`:

```env
PUBLIC_AZURE_CLIENT_ID="abc-123-def-456"
PUBLIC_AZURE_TENANT_ID="xyz-789-uvw-012"
PUBLIC_API_URL="http://localhost:8000"
PUBLIC_REDIRECT_URI="http://localhost:4321/auth/callback"
```

For production (`apps/web/.env.production`):

```env
PUBLIC_AZURE_CLIENT_ID="abc-123-def-456"
PUBLIC_AZURE_TENANT_ID="xyz-789-uvw-012"
PUBLIC_API_URL="https://your-api.azurecontainerapps.io"
PUBLIC_REDIRECT_URI="https://your-site.azurestaticapps.net/auth/callback"
```

### 8. Example: Job Creation Page

Create `apps/web/src/pages/create-job.astro`:

```astro
---
import Layout from '../layouts/Layout.astro';
---

<Layout title="Create Job">
  <h1>Create Parcel Research Job</h1>

  <form id="job-form">
    <div>
      <label for="county">County:</label>
      <input type="text" id="county" name="county" required />
    </div>

    <div>
      <label for="crs_id">CRS (EPSG):</label>
      <input type="number" id="crs_id" name="crs_id" required />
    </div>

    <div>
      <label for="gis_url">GIS URL:</label>
      <input type="url" id="gis_url" name="gis_url" required />
    </div>

    <div>
      <label for="parcel_file">Parcel File:</label>
      <input type="file" id="parcel_file" name="parcel_file" accept=".txt,.csv,.xlsx" required />
    </div>

    <div>
      <label for="shapefile_zip">Shapefile ZIP:</label>
      <input type="file" id="shapefile_zip" name="shapefile_zip" accept=".zip" required />
    </div>

    <button type="submit">Create Job</button>
  </form>

  <div id="result"></div>

  <script>
    import { api } from '../lib/api';
    import { isAuthenticated } from '../lib/auth';

    const form = document.getElementById('job-form') as HTMLFormElement;
    const result = document.getElementById('result');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();

      // Check authentication
      if (!isAuthenticated()) {
        alert('Please sign in first');
        window.location.href = '/';
        return;
      }

      const formData = new FormData(form);

      try {
        result!.innerHTML = '<p>Creating job...</p>';
        
        const response = await api.createJob(formData);
        
        result!.innerHTML = `
          <div class="success">
            <h3>Job Created!</h3>
            <p>Job ID: ${response.job_id}</p>
            <p>Status: ${response.status}</p>
            <p>Parcels: ${response.parcel_count}</p>
            <a href="/jobs/${response.job_id}">View Job</a>
          </div>
        `;
      } catch (error) {
        result!.innerHTML = `
          <div class="error">
            <h3>Error</h3>
            <p>${error.message}</p>
          </div>
        `;
      }
    });
  </script>
</Layout>
```

## Token Flow Diagram

```
┌─────────────┐
│   User      │
└──────┬──────┘
       │ 1. Clicks "Sign In"
       ▼
┌─────────────────────────────────────────┐
│  Frontend calls login()                 │
│  → msalInstance.loginRedirect()         │
└──────┬──────────────────────────────────┘
       │ 2. Redirects to Microsoft
       ▼
┌─────────────────────────────────────────┐
│  Microsoft Login Page                   │
│  (login.microsoftonline.com)            │
└──────┬──────────────────────────────────┘
       │ 3. User enters credentials
       │ 4. Microsoft validates
       ▼
┌─────────────────────────────────────────┐
│  Microsoft redirects back to            │
│  /auth/callback with token in URL       │
└──────┬──────────────────────────────────┘
       │ 5. MSAL handles redirect
       │ 6. Stores token in localStorage
       ▼
┌─────────────────────────────────────────┐
│  Frontend: User is now authenticated    │
│  Token stored, ready for API calls      │
└──────┬──────────────────────────────────┘
       │ 7. User creates job
       ▼
┌─────────────────────────────────────────┐
│  Frontend calls api.createJob()         │
│  → getAccessToken() retrieves token     │
│  → Adds "Authorization: Bearer TOKEN"   │
└──────┬──────────────────────────────────┘
       │ 8. POST /jobs/create
       ▼
┌─────────────────────────────────────────┐
│  Backend receives request               │
│  → Extracts Bearer token from header    │
│  → Validates token with Microsoft JWKS  │
│  → Verifies signature, exp, aud, iss    │
│  → Extracts user info from token        │
│  → Processes request                    │
└──────┬──────────────────────────────────┘
       │ 9. Returns response
       ▼
┌─────────────────────────────────────────┐
│  Frontend displays result               │
└─────────────────────────────────────────┘
```

## Testing

### Development (No Auth)

```env
# Backend .env
REQUIRE_AUTH="false"
```

All API calls work without tokens.

### Development (With Auth)

```env
# Backend .env
REQUIRE_AUTH="true"
AZURE_TENANT_ID="your-tenant-id"
AZURE_CLIENT_ID="your-client-id"

# Frontend .env
PUBLIC_AZURE_CLIENT_ID="your-client-id"
PUBLIC_AZURE_TENANT_ID="your-tenant-id"
```

1. Start backend: `uvicorn main:app --reload`
2. Start frontend: `npm run dev`
3. Navigate to `http://localhost:4321`
4. Click "Sign In"
5. Authenticate with Microsoft
6. Create a job (token sent automatically)

## Troubleshooting

### "Invalid token audience"
- Verify `AZURE_CLIENT_ID` matches in both backend and frontend
- Check token audience claim matches CLIENT_ID

### "Token has expired"
- MSAL automatically refreshes tokens
- If refresh fails, user is redirected to login

### "CORS error"
- Add frontend URL to backend CORS configuration:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321", "https://your-site.azurestaticapps.net"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### "Redirect URI mismatch"
- Verify redirect URI in Azure Portal matches exactly
- Check for trailing slashes

## Security Best Practices

1. **Never expose secrets** - CLIENT_ID is public, but never expose CLIENT_SECRET
2. **Use HTTPS in production** - Required for secure token transmission
3. **Validate tokens on backend** - Never trust frontend validation alone
4. **Set short token lifetimes** - Tokens expire after 1 hour by default
5. **Use PKCE flow** - MSAL uses PKCE by default for SPAs
6. **Store tokens securely** - MSAL uses localStorage (acceptable for SPAs)

## Production Deployment

### Azure Static Web Apps

1. **Configure authentication** in Azure Portal
2. **Set environment variables** in Static Web App configuration
3. **Deploy** - Authentication works automatically

### Backend (Azure Container Apps)

1. **Set environment variables** in Container App configuration
2. **Enable HTTPS** - Required for production
3. **Configure CORS** - Add Static Web App URL

## Summary

- **Backend**: Validates JWT tokens using Microsoft's public keys
- **Frontend**: Uses MSAL to handle login/logout and token management
- **Token**: Automatically included in API requests via Authorization header
- **Flow**: User logs in → Gets token → Token sent with API calls → Backend validates
- **Optional**: Can disable auth for development with `REQUIRE_AUTH=false`
