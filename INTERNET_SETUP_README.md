# E-ink Display Manager - Internet Access Setup

Complete guide to set up secure internet access to your E-ink display using Cloudflare Tunnel with authentication.

## 🚀 Quick Setup

### Prerequisites
- Cloudflare account (free)
- Domain name added to Cloudflare (free .tk domain works fine)

### Step 1: Get a Domain
If you don't have one:
- **Free option**: Get a .tk domain from [dot.tk](http://dot.tk)
- **Cheap option**: Buy a .xyz domain (~$2/year) from Namecheap

Add your domain to Cloudflare and wait for activation (5-30 minutes).

### Step 2: Run Setup
```bash
./setup_internet_access.sh
```

This will:
- Install cloudflared
- Authenticate with Cloudflare
- Create a tunnel
- Set up DNS
- Configure system service
- Set up admin authentication

### Step 3: Start Server
```bash
./start_internet_server.sh
```

## 🌐 Result

Your E-ink display will be accessible at:
**https://eink.yourdomain.com**

## 🎨 TouchDesigner Integration

Use these settings in WebClient DAT:
- **URL**: `https://eink.yourdomain.com/upload`
- **Authentication Type**: None
- **Custom Header**:
  - Name: `X-API-Key`
  - Value: `[your-api-key-from-.env-file]`

## 🔧 Management

```bash
# Check tunnel status
sudo systemctl status cloudflared.service

# View logs
sudo journalctl -u cloudflared.service -f

# Restart tunnel
sudo systemctl restart cloudflared.service
```

## 🔐 Security Features

- ✅ Admin password protection
- ✅ HTTPS encryption (automatic)
- ✅ Server binds to localhost only
- ✅ API key authentication for TouchDesigner
- ✅ No port forwarding needed

## 📁 Files

- `setup_internet_access.sh` - One-time setup
- `start_internet_server.sh` - Start the Flask server
- `setup_admin_password.py` - Set/reset admin password
- `.env` - Your credentials (auto-generated)

## 🖥️ Headless Pi Setup

If you're running without a GUI (headless):

1. **Authentication**: When the setup asks for browser authentication, copy the URL and open it on your phone/laptop
2. **Domain setup**: Add your domain to Cloudflare from any device with a browser
3. **Everything else works the same**

## 🎨 TouchDesigner Configuration

### WebClient DAT Settings:
- **URL**: `https://eink.yourdomain.com/upload`
- **Method**: `PUT` (automatically optimized for tunnel)
- **Authentication Type**: `None`
- **Custom Header**:
  - **Name**: `X-API-Key`
  - **Value**: `[your-api-key-from-.env-file]`

### Smart Upload Method:
The system automatically detects your connection:
- **Local network** (192.168.x.x) → Uses PUT with `uploadFile`
- **Internet tunnel** (domain) → Uses POST with binary data

**No configuration changes needed!** Same code works everywhere.

### Getting Your API Key:
```bash
# Your API key is in the .env file
cat .env | grep API_KEY
```

### TouchDesigner Upload Code:
```python
# Use WebClient DAT - works both locally and through tunnel
connection_id = op('webclient1').request(
    'https://eink.yourdomain.com/upload',
    'PUT',
    header={'X-API-Key': 'your-api-key-here'},
    uploadFile='/path/to/image.jpg'
)

```

**Benefits:**
- ✅ **Same code** works locally and through internet
- ✅ **Automatic optimization** for each connection type
- ✅ **No manual switching** between methods

## 🔧 Troubleshooting

### "Please select the zone" Error
- **Problem**: No domain in your Cloudflare account
- **Solution**: Add a domain to Cloudflare first (free .tk domain works)

### "Host Error" on Domain
- **Problem**: DNS record conflict (parking page A record exists)
- **Solution**:
  1. Go to Cloudflare Dashboard → DNS → Records
  2. Delete existing A record for your domain
  3. Run: `cloudflared tunnel route dns TUNNEL_ID yourdomain.com`

### DNS Route Creation Failed
- **Problem**: Existing DNS record conflicts with tunnel
- **Solution**: Delete conflicting records in Cloudflare dashboard first

### "Authentication required" Error
- **Problem**: Missing or wrong API key
- **Solution**: Check your `.env` file for the correct API key

### "Connection timeout" Error
- **Problem**: Tunnel service not running
- **Solution**: `sudo systemctl start cloudflared.service`

### Pi Zero Installation Issues
- **Problem**: Architecture mismatch
- **Solution**: The script automatically detects Pi Zero and uses the correct ARM binary

### Random URL Changes
- **Problem**: Using quick tunnels instead of named tunnels
- **Solution**: You need a domain in Cloudflare for permanent URLs

## 🔐 Security Notes

- **Admin password**: Set a strong password (12+ characters)
- **API key**: Keep it secret, regenerate if compromised
- **HTTPS only**: Cloudflare provides automatic SSL
- **Localhost binding**: Flask server only accepts local connections
- **No port forwarding**: Tunnel makes outbound connections only

## 📊 API Endpoints

All endpoints require authentication (web login or API key):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Web interface |
| `/upload` | POST/PUT | Upload files |
| `/api/files` | GET | List files with thumbnails |
| `/display_file` | POST | Display specific file |
| `/delete_file` | POST | Delete file |
| `/clear_screen` | POST | Clear display |
| `/status` | GET | Server status |

## 🆘 Getting Help

1. **Check the logs**: `sudo journalctl -u cloudflared.service -f`
2. **Test locally first**: `curl http://localhost:5000/status`
3. **Verify tunnel**: `sudo systemctl status cloudflared.service`
4. **Check Flask server**: Look for error messages when starting

## 🎉 Success!

Once everything is working, you'll have:
- ✅ Secure internet access to your E-ink display
- ✅ Admin web interface with authentication
- ✅ TouchDesigner integration with API keys
- ✅ Permanent HTTPS URL
- ✅ No router configuration needed

That's it! Clean and simple. 🎉
