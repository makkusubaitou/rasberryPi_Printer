# Raspberry Pi Print Server

A lightweight print server that receives images via webhook and prints them to your network printer. Exposed to the internet securely using Cloudflare Tunnel.

## Architecture

```
Your Website → Cloudflare Tunnel → Raspberry Pi → Network Printer
                 (encrypted)        (Flask API)      (via CUPS)
```

## Quick Start

### 1. Clone the repo on your Raspberry Pi

```bash
# SSH into your Pi
ssh pi@<your-pi-ip>

# Clone the repository
git clone https://github.com/makkusubaitou/rasberryPi_Printer.git
cd rasberryPi_Printer
```

### 2. Run the setup script

```bash
chmod +x setup.sh
./setup.sh
```

The setup script will:
- Install Python, CUPS, and dependencies
- Generate a secure API key (save this!)
- Set up the print server as a system service
- Install Cloudflare Tunnel

### 3. Configure your printer

Make sure your printer is detected:

```bash
lpstat -p -d
```

If your printer isn't listed, add it via the CUPS web interface:
- Go to `http://<your-pi-ip>:631` in your browser
- Administration → Add Printer
- Select your network printer

### 4. Configure Cloudflare Tunnel

```bash
# Login to Cloudflare (opens a browser link)
cloudflared tunnel login

# Create a tunnel
cloudflared tunnel create print-server

# Route your subdomain
cloudflared tunnel route dns print-server printer.yourdomain.com

# Create config file
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

Add this to `config.yml`:

```yaml
tunnel: print-server
credentials-file: /home/pi/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: printer.yourdomain.com
    service: http://localhost:5000
  - service: http_status:404
```

Replace `<TUNNEL_ID>` with the ID shown when you created the tunnel.

```bash
# Install as a service and start
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

## API Reference

### Health Check

```bash
GET /health
```

Returns server status and printer information.

### Print Image

```bash
POST /print
Headers:
  X-API-Key: your-api-key

Form Data:
  image: (file) The image to print
  copies: (optional) Number of copies (default: 1, max: 10)
```

**Example:**

```bash
curl -X POST https://printer.yourdomain.com/print \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "image=@receipt.png" \
  -F "copies=1"
```

**Response:**

```json
{
  "success": true,
  "message": "Print job submitted successfully",
  "job_id": "Printer-123",
  "copies": 1
}
```

### List Printers

```bash
GET /printers
Headers:
  X-API-Key: your-api-key
```

Returns list of available printers.

## Website Integration

### JavaScript/Fetch Example

```javascript
async function printImage(imageFile) {
  const formData = new FormData();
  formData.append('image', imageFile);
  formData.append('copies', '1');

  const response = await fetch('https://printer.yourdomain.com/print', {
    method: 'POST',
    headers: {
      'X-API-Key': 'YOUR_API_KEY'
    },
    body: formData
  });

  return response.json();
}
```

### Node.js Example

```javascript
const FormData = require('form-data');
const fs = require('fs');
const fetch = require('node-fetch');

async function printImage(imagePath) {
  const form = new FormData();
  form.append('image', fs.createReadStream(imagePath));

  const response = await fetch('https://printer.yourdomain.com/print', {
    method: 'POST',
    headers: {
      'X-API-Key': process.env.PRINT_API_KEY,
      ...form.getHeaders()
    },
    body: form
  });

  return response.json();
}
```

### Python Example

```python
import requests

def print_image(image_path: str, copies: int = 1) -> dict:
    with open(image_path, 'rb') as f:
        response = requests.post(
            'https://printer.yourdomain.com/print',
            headers={'X-API-Key': 'YOUR_API_KEY'},
            files={'image': f},
            data={'copies': copies}
        )
    return response.json()
```

## Configuration

Edit `/home/pi/print-server/config.py` to customize:

- `PRINTER_NAME`: Specific printer to use (leave empty for default)
- `PRINT_OPTIONS`: CUPS print options (e.g., `fit-to-page`, `media=A4`)
- `MAX_COPIES`: Maximum copies per request
- `PORT`: Server port (default: 5000)

## Managing the Service

```bash
# Check status
sudo systemctl status print-server
sudo systemctl status cloudflared

# View logs
journalctl -u print-server -f
journalctl -u cloudflared -f

# Restart services
sudo systemctl restart print-server
sudo systemctl restart cloudflared
```

## Troubleshooting

### Printer not found
1. Check if CUPS is running: `sudo systemctl status cups`
2. Add printer via CUPS web UI: `http://localhost:631`
3. Verify: `lpstat -p -d`

### API returns 403
- Check your API key is correct
- Make sure there's no extra whitespace

### Tunnel not connecting
1. Check tunnel status: `cloudflared tunnel info print-server`
2. Verify DNS: `dig printer.yourdomain.com`
3. Check logs: `journalctl -u cloudflared -f`

### Print quality issues
Add options to `PRINT_OPTIONS` in `config.py`:
- `fit-to-page` - Scale to fit
- `media=A4` or `media=Letter` - Paper size
- `print-quality=5` - High quality

## Security Notes

- Keep your API key secret
- The tunnel encrypts all traffic
- Consider adding [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/policies/access/) for extra security
- The server only binds to localhost (127.0.0.1), Cloudflare handles external access

