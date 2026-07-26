# Cloudflare Pages Deployment Guide

## Overview
Your Data Dictionary app is now split into two sections:
- **Public View** (`/index.html`) - Read-only access for everyone
- **Admin Interface** (`/admin/index.html`) - Full edit capabilities, protected by Cloudflare Access

## Step-by-Step Deployment

### 1. Set Up Cloudflare Pages

1. **Sign up/Login to Cloudflare**
   - Go to https://dash.cloudflare.com/
   - Create an account or sign in

2. **Create a New Project**
   - Go to **Pages** in the sidebar
   - Click **Create a project**
   - Connect your GitHub account
   - Select the `data-dictionary` repository

3. **Configure Build Settings**
   - **Production branch**: `main`
   - **Build command**: Leave empty (static site)
   - **Build output directory**: `/`
   - Click **Save and Deploy**

4. **Wait for Initial Deployment**
   - Cloudflare will deploy your site
   - You'll get a URL like: `https://data-dictionary.pages.dev`

### 2. Set Up Cloudflare Access (Protect Admin)

1. **Go to Zero Trust Dashboard**
   - Navigate to https://one.dash.cloudflare.com/
   - Or from your main dashboard: **Zero Trust** in the sidebar

2. **Set Up Your Team**
   - If first time: Create a team name (e.g., `your-company`)
   - Your team domain will be: `your-company.cloudflareaccess.com`

3. **Create an Access Application**
   - Go to **Access** → **Applications**
   - Click **Add an application**
   - Select **Self-hosted**

4. **Configure Application Settings**
   ```
   Application name: Data Dictionary Admin
   Session duration: 24 hours (or your preference)
   
   Application domain: 
   - Subdomain: admin
   - Domain: data-dictionary.pages.dev (or your custom domain)
   - Path: /admin/*
   ```

5. **Create Access Policy**
   - Click **Next** to add policies
   - Policy name: `Admin Users`
   - Action: **Allow**
   - Include rule options:
     - **Emails**: Add specific email addresses (e.g., admin@yourcompany.com)
     - OR **Email domains**: Add your company domain (e.g., @yourcompany.com)
     - OR **Groups**: If you have Cloudflare groups set up

6. **Save the Application**
   - Click **Add application**
   - Cloudflare Access is now protecting `/admin/*`

### 3. Update _headers File (if needed)

The `_headers` file in your repository configures path protection. Update it with your actual team name:

```
/admin/*
  CF-Access-Team-Domain: your-company.cloudflareaccess.com
```

Replace `your-company` with your actual Cloudflare team name.

### 4. Test Your Deployment

1. **Test Public Access**
   - Visit: `https://data-dictionary.pages.dev/`
   - You should see the read-only dictionary (no login required)

2. **Test Admin Access**
   - Visit: `https://data-dictionary.pages.dev/admin/`
   - Cloudflare Access will prompt you to authenticate
   - After authentication, you'll see the full admin interface with edit/delete/add capabilities

### 5. Custom Domain (Optional)

1. **Add Custom Domain in Cloudflare Pages**
   - In Pages dashboard, go to your project
   - Click **Custom domains**
   - Add your domain (e.g., `dictionary.yourcompany.com`)
   - Update DNS records as instructed

2. **Update Cloudflare Access Application**
   - Go back to your Access Application
   - Update the domain to match your custom domain

## How It Works

### Public Users (No Auth Required)
- Visit: `yoursite.com/` or `yoursite.com/index.html`
- See all dictionary entries (read-only)
- Can search and filter
- Cannot edit, delete, or add entries

### Admin Users (Cloudflare Access Required)
- Visit: `yoursite.com/admin/`
- Prompted to authenticate via Cloudflare Access
- Choose authentication method:
  - One-time PIN (sent to email)
  - Social login (Google, GitHub, etc.) if configured
  - SSO if configured
- After authentication: Full admin interface with all features

### Access Roles

The app supports three access tiers. The role is resolved by the API
from the reverse proxy's authenticated-user header, so the app works
with Cloudflare Access **or** any other SSO proxy (oauth2-proxy,
nginx auth_request, etc.) without code changes.

| Role | Who | Can do |
|------|-----|--------|
| **public** | Anonymous (no auth) | Read all `GET` endpoints: browse, search, view entries, tags, history |
| **viewer** | Authenticated by the proxy but not on the admin allow-list | Everything public can do, plus load the admin panel in **read-only** mode and download `/api/backup` |
| **admin** | Authenticated and on the `ADMIN_EMAILS` allow-list | Everything, including create/update/delete entries, tags, definitions, links, bulk import, restore |

#### API configuration (environment variables)

| Variable | Default | Purpose |
|----------|---------|---------|
| `AUTH_DISABLED` | `true` | When `true`, auth is bypassed and all requests are treated as `public` (the default for tests and standalone local dev). Set to `false` in any deployment behind an authenticating proxy. |
| `ADMIN_EMAILS` | *(empty)* | Comma-separated allow-list of emails granted the `admin` role. Example: `ADMIN_EMAILS=alice@ncc.edu,bob@ncc.edu` |
| `AUTH_TRUSTED_EMAIL_HEADER` | `Cf-Access-Authenticated-User-Email` | The request header carrying the authenticated user's email. Override for non-Cloudflare proxies (e.g. `X-Forwarded-Email` for oauth2-proxy). |

The proxy must overwrite this header before forwarding to the app;
the app trusts whatever the proxy sets. Never expose the API directly
to untrusted networks without a proxy in front.

#### `GET /api/auth/me`

Returns the current user's resolved role:

```json
{ "email": "alice@ncc.edu", "role": "admin", "authenticated": true }
```

The admin UI calls this on load to gate the interface: non-admin users
get a read-only view with the edit/delete buttons hidden.

## Authentication Methods

Cloudflare Access supports multiple authentication methods:

1. **One-time PIN** (Default, Free)
   - User enters email
   - Receives 6-digit code
   - Enters code to access

2. **Social Logins** (Free)
   - Google
   - GitHub
   - Facebook
   - LinkedIn

3. **SSO/SAML** (Paid plans)
   - Okta
   - Azure AD
   - OneLogin
   - Others

Configure these under: **Settings** → **Authentication** in Zero Trust dashboard

## Data Storage

- All dictionary data is stored in **browser localStorage**
- Each browser maintains its own copy
- To share data across browsers:
  - Admins can export as Excel/CSV
  - Import into other browsers manually

### Future Enhancement: Shared Storage
Consider adding a backend (like Cloudflare Workers KV or D1) to share data across all users.

## Troubleshooting

### Admin page not protected
- Check Cloudflare Access application path is `/admin/*`
- Verify DNS is pointing to Cloudflare
- Ensure SSL/TLS is set to "Full" or "Full (strict)"

### Can't log in to admin
- Check email is added to Access policy
- Verify email matches exactly (case-sensitive)
- Check spam folder for PIN email

### Changes not deploying
- Check GitHub is connected to Cloudflare Pages
- Verify automatic deployments are enabled
- Manually trigger deployment from Pages dashboard

## Cost

- **Cloudflare Pages**: Free (unlimited bandwidth, unlimited requests)
- **Cloudflare Access**: Free tier includes up to 50 users
- **Custom Domain**: Free if domain already on Cloudflare

## Support

- Cloudflare Docs: https://developers.cloudflare.com/pages/
- Cloudflare Access Docs: https://developers.cloudflare.com/cloudflare-one/
- Community: https://community.cloudflare.com/
