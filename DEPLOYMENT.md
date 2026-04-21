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
