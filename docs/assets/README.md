# Birthmark Standard - Image Verification Tool

## Overview

This directory contains the client-side image verification tool for the Birthmark Standard. The tool allows users to verify whether images have been authenticated through the Birthmark camera authentication system.

## Architecture

### Files

- **`js/verifier.js`** - Core verification logic
  - SHA-256 hashing using Web Crypto API
  - Blockchain query functionality
  - Result display and UI management
  - Provenance chain visualization

- **`css/verifier.css`** - Styling for verification interface
  - Responsive design (mobile + desktop)
  - Status badges for modification levels
  - Drag-and-drop interface
  - Accessibility features

### Privacy-First Design

All image processing happens **client-side** in the browser:

1. User selects/drops an image file
2. JavaScript reads the file using FileReader API
3. SHA-256 hash is computed using Web Crypto API
4. **Only the hash** is sent to blockchain for verification
5. Results are displayed with provenance chain

**The image itself never leaves the user's device.**

## Usage

### Basic Integration

Include the verification tool in any HTML page:

```html
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="assets/css/verifier.css">
</head>
<body>
    <!-- Your verification UI elements -->

    <script src="assets/js/verifier.js"></script>
</body>
</html>
```

### Blockchain Configuration

The tool queries the Birthmark Media Registry blockchain. Configure endpoints in `verifier.js`:

```javascript
const CONFIG = {
    endpoints: [
        'http://localhost:26657/abci_query',  // Local testnet
        'https://registry.birthmarkstandard.org/query'  // Production
    ]
};
```

The tool automatically falls back through endpoints if one fails.

## Verification Response Format

The blockchain query returns JSON in this format:

### Verified Image

```json
{
  "verified": true,
  "image_hash": "a9d1dbb063ffd40ed3da020e14aa994a...",
  "modification_level": 1,
  "modification_display": "Validated",
  "authority": {
    "type": "camera",
    "authority_id": "CANON_EOS_R5"
  },
  "timestamp": "2025-12-28T00:00:00Z",
  "parent_image_hash": "29d6c8498815c58cb274cb4878cd3f4f...",
  "provenance_chain": [
    {
      "hash": "29d6c8498815c58cb274cb4878cd3f4f...",
      "modification_level": 0,
      "modification_display": "Validated Raw",
      "timestamp": "2025-12-27T23:00:00Z"
    }
  ]
}
```

### Not Found

```json
{
  "verified": false,
  "image_hash": "abc123..."
}
```

## Modification Levels

The tool displays three modification levels with distinct visual indicators:

### Level 0: Validated Raw
- **Color:** Green (`#22c55e`)
- **Description:** Unprocessed sensor data from verified camera
- **Guarantee:** Untouched sensor capture from authenticated hardware

### Level 1: Validated
- **Color:** Blue (`#3b82f6`)
- **Description:** Camera ISP processing OR minor edits (exposure, cropping)
- **Guarantee:** Content originated from authenticated camera

### Level 2: Modified
- **Color:** Yellow/Orange (`#f59e0b`)
- **Description:** Significant content modifications (compositing, object removal)
- **Guarantee:** Derived from authenticated source, but altered

## Features

### Drag-and-Drop Interface
- Click to select or drag-and-drop image files
- Visual feedback during drag operations
- Support for all major image formats (JPG, PNG, GIF, WebP, etc.)

### SHA-256 Hashing
- Uses native Web Crypto API for performance
- Displays full hash with copy-to-clipboard functionality
- Processes large images efficiently

### Blockchain Querying
- Automatic endpoint fallback for reliability
- Loading indicators during network requests
- Clear error messages for network failures

### Results Display
- Color-coded status badges
- Detailed verification information
- Authority identification
- Timestamp display
- Provenance chain visualization

### Responsive Design
- Mobile-first approach
- Touch-friendly interface
- Adapts to screen sizes 320px - 4K
- Accessible keyboard navigation

## Testing

### Mock Responses

For development/testing, the tool includes mock responses when querying `localhost`:

```javascript
// In verifier.js
function createMockResponse(hash) {
    // Returns "not found" by default
    return {
        verified: false,
        image_hash: hash
    };

    // Uncomment for verified response testing:
    /*
    return {
        verified: true,
        image_hash: hash,
        modification_level: 1,
        // ...
    };
    */
}
```

### Testing Workflow

1. Start local blockchain testnet: `http://localhost:26657`
2. Open `verify.html` in browser
3. Select test image
4. Verify SHA-256 hash is computed correctly
5. Check blockchain query is sent
6. Verify results display properly

## Browser Compatibility

Requires modern browsers with Web Crypto API support:

- Chrome/Edge 60+
- Firefox 57+
- Safari 11+
- Mobile browsers (iOS Safari 11+, Chrome Mobile 60+)

## Security Considerations

### No Server-Side Processing
- Images are never uploaded to servers
- Only 64-character SHA-256 hash is transmitted
- No cookies or tracking

### Content Security Policy
Recommended CSP headers:

```
Content-Security-Policy:
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  connect-src 'self' https://registry.birthmarkstandard.org;
```

### CORS Requirements

The blockchain API must allow cross-origin requests:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST
Access-Control-Allow-Headers: Content-Type
```

## Deployment

### GitHub Pages

The tool is designed for GitHub Pages deployment:

1. All files are static (HTML/CSS/JS)
2. No build step required
3. Works with Jekyll (`.nojekyll` file present)
4. CDN-friendly for global distribution

### Custom Hosting

For self-hosting:

```bash
# Serve with any static file server
cd docs
python3 -m http.server 8000
# Open http://localhost:8000/verify.html
```

## Integration with Blockchain

### Phase 1: Local Testnet

For Phase 1 development, the tool queries a local Cosmos SDK testnet:

```bash
# Start testnet
birthmark-registry start --home ~/.birthmark-testnet

# Query endpoint
http://localhost:26657/abci_query?data=<hex_encoded_hash>
```

### Production: Cosmos SDK Network

For production, the blockchain runs Cosmos SDK with custom modules:

- **Endpoint:** `https://registry.birthmarkstandard.org/query`
- **Method:** GET or POST
- **Input:** SHA-256 hash (hex string)
- **Output:** JSON verification record

## Accessibility

The tool follows WCAG 2.1 AA standards:

- Semantic HTML structure
- Keyboard navigation support
- ARIA labels for screen readers
- Color contrast ratios > 4.5:1
- Focus indicators on interactive elements

## Future Enhancements

Planned features for future releases:

- **Batch Verification:** Verify multiple images at once
- **QR Code Scanning:** Scan QR codes containing hashes
- **Browser Extension:** Verify images with right-click
- **API Integration:** Direct C2PA metadata reading
- **Advanced Search:** Search by authority, date range
- **Export Reports:** Generate PDF verification reports

## License

Apache License 2.0 - See LICENSE file in repository root.

## Contact

For technical questions or contributions:
- **GitHub:** https://github.com/Birthmark-Standard/Birthmark
- **Email:** contact@birthmarkstandard.org
- **Issues:** https://github.com/Birthmark-Standard/Birthmark/issues

---

**Last Updated:** December 28, 2025
**Version:** 1.0.0 (Phase 1)
