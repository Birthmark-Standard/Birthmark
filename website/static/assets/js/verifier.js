/**
 * Birthmark Standard - Image Verification Tool
 *
 * This tool allows users to verify image authenticity by:
 * 1. Computing SHA-256 hash locally (no upload)
 * 2. Querying the Birthmark Media Registry blockchain
 * 3. Displaying verification status with provenance chain
 *
 * Privacy: All image processing happens client-side.
 * Only the hash is sent to the blockchain for verification.
 */

// Configuration
const CONFIG = {
    // Blockchain endpoints (fallback from testnet to production)
    endpoints: [
        'http://localhost:26657/abci_query',  // Local testnet
        'https://registry.birthmarkstandard.org/query'  // Production (future)
    ],
    maxFileSize: 100 * 1024 * 1024,  // 100MB max file size
    supportedFormats: ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp', 'image/tiff']
};

// DOM Elements
let dropZone, fileInput, selectButton, clearButton;
let imagePreview, previewImage;
let hashDisplay, hashValue;
let verificationStatus, loadingIndicator;

// State
let currentFile = null;
let currentHash = null;

/**
 * Initialize the application
 */
function init() {
    // Get DOM elements
    dropZone = document.getElementById('dropZone');
    fileInput = document.getElementById('fileInput');
    selectButton = document.getElementById('selectButton');
    clearButton = document.getElementById('clearButton');
    imagePreview = document.getElementById('imagePreview');
    previewImage = document.getElementById('previewImage');
    hashDisplay = document.getElementById('hashDisplay');
    hashValue = document.getElementById('hashValue');
    verificationStatus = document.getElementById('verificationStatus');
    loadingIndicator = document.getElementById('loadingIndicator');

    // Set up event listeners
    setupEventListeners();
}

/**
 * Set up all event listeners
 */
function setupEventListeners() {
    // File selection button
    selectButton.addEventListener('click', () => fileInput.click());

    // File input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFile(e.target.files[0]);
        }
    });

    // Clear button
    clearButton.addEventListener('click', resetUI);

    // Drag and drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');

        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFile(files[0]);
        }
    });

    // Click on drop zone to select file
    dropZone.addEventListener('click', (e) => {
        if (e.target === dropZone || dropZone.contains(e.target)) {
            fileInput.click();
        }
    });
}

/**
 * Handle file selection
 */
async function handleFile(file) {
    // Validate file
    const validation = validateFile(file);
    if (!validation.valid) {
        showError(validation.error);
        return;
    }

    currentFile = file;

    // Show preview
    showImagePreview(file);

    // Compute hash
    await computeAndDisplayHash(file);

    // Query blockchain
    await queryBlockchain(currentHash);
}

/**
 * Validate file before processing
 */
function validateFile(file) {
    // Check if it's an image
    if (!file.type.startsWith('image/')) {
        return { valid: false, error: 'Please select an image file.' };
    }

    // Check file size
    if (file.size > CONFIG.maxFileSize) {
        return {
            valid: false,
            error: `File size (${formatFileSize(file.size)}) exceeds maximum allowed size (${formatFileSize(CONFIG.maxFileSize)}).`
        };
    }

    return { valid: true };
}

/**
 * Show image preview
 */
function showImagePreview(file) {
    const reader = new FileReader();

    reader.onload = (e) => {
        previewImage.src = e.target.result;
        dropZone.style.display = 'none';
        imagePreview.style.display = 'block';
    };

    reader.readAsDataURL(file);
}

/**
 * Compute SHA-256 hash of the image file
 */
async function computeAndDisplayHash(file) {
    try {
        hashDisplay.style.display = 'block';
        hashValue.innerHTML = '<div class="hash-computing">Computing hash...</div>';

        // Read file as ArrayBuffer
        const arrayBuffer = await file.arrayBuffer();

        // Compute SHA-256 hash using Web Crypto API
        const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);

        // Convert to hex string
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

        currentHash = hashHex;

        // Display hash
        hashValue.innerHTML = `
            <div class="hash-text">${hashHex}</div>
            <button class="copy-hash-btn" onclick="copyHash()">Copy Hash</button>
        `;

    } catch (error) {
        console.error('Error computing hash:', error);
        showError('Failed to compute image hash. Please try again.');
    }
}

/**
 * Copy hash to clipboard
 */
function copyHash() {
    navigator.clipboard.writeText(currentHash).then(() => {
        const btn = document.querySelector('.copy-hash-btn');
        const originalText = btn.textContent;
        btn.textContent = 'Copied!';
        setTimeout(() => {
            btn.textContent = originalText;
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy hash:', err);
    });
}

/**
 * Query the blockchain for verification
 */
async function queryBlockchain(hash) {
    loadingIndicator.style.display = 'block';
    verificationStatus.style.display = 'none';

    try {
        // Try each endpoint in order
        for (const endpoint of CONFIG.endpoints) {
            try {
                const result = await queryEndpoint(endpoint, hash);
                displayVerificationResult(result);
                loadingIndicator.style.display = 'none';
                return;
            } catch (error) {
                console.warn(`Endpoint ${endpoint} failed:`, error);
                // Continue to next endpoint
            }
        }

        // All endpoints failed
        throw new Error('All blockchain endpoints are unavailable');

    } catch (error) {
        console.error('Blockchain query error:', error);
        loadingIndicator.style.display = 'none';
        showError('Unable to connect to the Birthmark Media Registry. Please check your internet connection and try again.');
    }
}

/**
 * Query a specific blockchain endpoint
 */
async function queryEndpoint(endpoint, hash) {
    // For Phase 1 testnet, we'll construct the appropriate query
    // In production, this would be a REST API call

    // Mock response for development/testing
    // In production, this will be replaced with actual blockchain query
    if (endpoint.includes('localhost')) {
        // Simulate network delay
        await new Promise(resolve => setTimeout(resolve, 1000));

        // Return mock data for testing
        // This will be replaced with actual blockchain query
        return createMockResponse(hash);
    }

    // Production endpoint query
    const response = await fetch(`${endpoint}?hash=${hash}`);

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
}

/**
 * Create mock response for testing
 * This will be removed in production
 */
function createMockResponse(hash) {
    // Simulate "not found" for most hashes
    // In testing, you can modify this to return verified results
    return {
        verified: false,
        image_hash: hash
    };

    /* Example verified response:
    return {
        verified: true,
        image_hash: hash,
        modification_level: 1,
        modification_display: "Validated",
        authority: {
            type: "camera",
            authority_id: "CANON_EOS_R5"
        },
        timestamp: new Date().toISOString(),
        parent_image_hash: "a9d1dbb063ffd40ed3da020e14aa994a123456789abcdef",
        provenance_chain: [
            {
                hash: "a9d1dbb063ffd40ed3da020e14aa994a123456789abcdef",
                modification_level: 0,
                modification_display: "Validated Raw",
                timestamp: new Date(Date.now() - 3600000).toISOString()
            }
        ]
    };
    */
}

/**
 * Display verification result
 */
function displayVerificationResult(result) {
    verificationStatus.style.display = 'block';

    if (!result.verified) {
        verificationStatus.innerHTML = `
            <div class="result-card result-not-found">
                <div class="result-icon">❓</div>
                <h3>No Record Found</h3>
                <p>This image has not been authenticated through the Birthmark Standard.</p>
                <div class="result-details">
                    <p><strong>What this means:</strong></p>
                    <ul>
                        <li>The image may have been captured by a camera without Birthmark hardware</li>
                        <li>The image may be AI-generated or created digitally</li>
                        <li>The image may have been modified since authentication (different hash)</li>
                        <li>The image may predate the Birthmark system</li>
                    </ul>
                </div>
            </div>
        `;
        return;
    }

    // Verified image - display based on modification level
    const statusClass = getStatusClass(result.modification_level);
    const statusText = result.modification_display || getModificationLevelText(result.modification_level);

    let html = `
        <div class="result-card result-verified ${statusClass}">
            <div class="result-icon">✓</div>
            <h3>Verified Authentic</h3>
            <div class="status-badge ${statusClass}">${statusText}</div>

            <div class="result-details">
                <div class="detail-row">
                    <span class="detail-label">Authority:</span>
                    <span class="detail-value">${formatAuthority(result.authority)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Authenticated:</span>
                    <span class="detail-value">${formatTimestamp(result.timestamp)}</span>
                </div>
                <div class="detail-row">
                    <span class="detail-label">Modification Level:</span>
                    <span class="detail-value">${result.modification_level} - ${statusText}</span>
                </div>
            </div>

            ${getModificationLevelDescription(result.modification_level)}
    `;

    // Add provenance chain if available
    if (result.provenance_chain && result.provenance_chain.length > 0) {
        html += `
            <div class="provenance-chain">
                <h4>Provenance Chain</h4>
                <p class="provenance-intro">This image has been edited. Below is the complete lineage back to the original camera capture:</p>
                <div class="chain-items">
        `;

        // Add current image
        html += `
            <div class="chain-item chain-current">
                <div class="chain-marker">Current</div>
                <div class="chain-content">
                    <div class="chain-hash">${result.image_hash.substring(0, 16)}...</div>
                    <div class="chain-level">${statusText}</div>
                    <div class="chain-time">${formatTimestamp(result.timestamp)}</div>
                </div>
            </div>
        `;

        // Add parent images
        result.provenance_chain.forEach((parent, index) => {
            const parentStatusClass = getStatusClass(parent.modification_level);
            const parentStatusText = parent.modification_display || getModificationLevelText(parent.modification_level);

            html += `
                <div class="chain-arrow">↓</div>
                <div class="chain-item ${parentStatusClass}">
                    <div class="chain-marker">${index === result.provenance_chain.length - 1 ? 'Original' : 'Parent'}</div>
                    <div class="chain-content">
                        <div class="chain-hash">${parent.hash.substring(0, 16)}...</div>
                        <div class="chain-level">${parentStatusText}</div>
                        <div class="chain-time">${formatTimestamp(parent.timestamp)}</div>
                    </div>
                </div>
            `;
        });

        html += `
                </div>
            </div>
        `;
    }

    html += '</div>';

    verificationStatus.innerHTML = html;
}

/**
 * Get status class for modification level
 */
function getStatusClass(level) {
    switch (level) {
        case 0: return 'status-validated-raw';
        case 1: return 'status-validated';
        case 2: return 'status-modified';
        default: return 'status-unknown';
    }
}

/**
 * Get text description for modification level
 */
function getModificationLevelText(level) {
    switch (level) {
        case 0: return 'Validated Raw';
        case 1: return 'Validated';
        case 2: return 'Modified';
        default: return 'Unknown';
    }
}

/**
 * Get detailed description for modification level
 */
function getModificationLevelDescription(level) {
    const descriptions = {
        0: `
            <div class="level-description level-0">
                <p><strong>Validated Raw (Level 0)</strong> means this is unprocessed sensor data directly from a verified camera. This is the purest form of authenticated imagery—raw Bayer data before any image processing.</p>
                <p class="guarantee">✓ Guarantee: Untouched sensor capture from authenticated hardware</p>
            </div>
        `,
        1: `
            <div class="level-description level-1">
                <p><strong>Validated (Level 1)</strong> means this image was either processed by the camera's Image Signal Processor (ISP) OR edited using standard photo adjustments like exposure correction, cropping, or color grading.</p>
                <p class="guarantee">✓ Guarantee: Content originated from authenticated camera; may have non-destructive edits</p>
            </div>
        `,
        2: `
            <div class="level-description level-2">
                <p><strong>Modified (Level 2)</strong> means this image has significant content modifications such as compositing, content-aware fill, object removal, or other alterations that change the semantic content.</p>
                <p class="guarantee">✓ Guarantee: Derived from authenticated source, but content has been altered</p>
            </div>
        `
    };

    return descriptions[level] || '';
}

/**
 * Format authority information
 */
function formatAuthority(authority) {
    if (!authority) return 'Unknown';

    const type = authority.type === 'camera' ? 'Camera' : 'Software';
    return `${type}: ${authority.authority_id}`;
}

/**
 * Format timestamp
 */
function formatTimestamp(timestamp) {
    if (!timestamp) return 'Unknown';

    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short'
    });
}

/**
 * Format file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';

    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Show error message
 */
function showError(message) {
    verificationStatus.style.display = 'block';
    verificationStatus.innerHTML = `
        <div class="result-card result-error">
            <div class="result-icon">⚠️</div>
            <h3>Error</h3>
            <p>${message}</p>
        </div>
    `;
}

/**
 * Reset UI to initial state
 */
function resetUI() {
    currentFile = null;
    currentHash = null;

    dropZone.style.display = 'block';
    imagePreview.style.display = 'none';
    hashDisplay.style.display = 'none';
    verificationStatus.style.display = 'none';
    loadingIndicator.style.display = 'none';

    previewImage.src = '';
    fileInput.value = '';
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// Make copyHash available globally
window.copyHash = copyHash;
