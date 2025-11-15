# Simulated Software Authority (SSA) Validation Server

The SSA Validation Server is a Flask-based service that issues certificates to editing software and validates their integrity as part of the Birthmark Standard ecosystem.

## Overview

The SSA serves a similar role to the Simulated Manufacturer Authority (SMA), but for editing software instead of cameras:

- **Issues certificates** to validated editing software/plugins
- **Validates software integrity** using versioned hash system
- **Manages valid software versions** to prevent unauthorized modifications
- **Provides validation endpoint** for the aggregation server

## Architecture

```
Editing Software                 SSA                          Aggregation Server
     │                           │                                    │
     │  1. Provision Request     │                                    │
     ├──────────────────────────>│                                    │
     │     (baseline hash)        │                                    │
     │                           │                                    │
     │  2. Software Certificate  │                                    │
     │<──────────────────────────┤                                    │
     │                           │                                    │
     │  3. Validation Request    │                                    │
     │     (during operation)    │                                    │
     ├───────────────────────────┼───────────────────────────────────>│
     │                           │                                    │
     │                           │  4. Validate Certificate           │
     │                           │<───────────────────────────────────┤
     │                           │     (hash + version)               │
     │                           │                                    │
     │                           │  5. PASS/FAIL Response             │
     │                           ├───────────────────────────────────>│
```

## Versioned Hash System

The SSA uses a versioned hash system to allow legitimate software updates without requiring re-provisioning:

1. **Baseline Hash**: SHA-256 of the original plugin code
2. **Version String**: Embedded in the plugin (e.g., "1.0.0")
3. **Versioned Hash**: SHA-256(baseline_hash + version_string)

This allows:
- Legitimate version updates (SSA adds version to valid list)
- Detection of unauthorized modifications (hash mismatch)
- Prevention of old vulnerable versions (version not in valid list)

## Project Structure

```
ssa/
├── certificates/                   # CA certificates and keys
│   ├── ssa-root-ca.crt            # Root CA certificate (10-year validity)
│   ├── ssa-root-ca.key            # Root CA private key (encrypted)
│   ├── ssa-intermediate-ca.crt    # Intermediate CA certificate (5-year validity)
│   └── ssa-intermediate-ca.key    # Intermediate CA private key (encrypted)
│
├── provisioned_software/           # Provisioned software data
│   └── <software-id>/
│       ├── software_certificate.pem
│       ├── software_private_key.pem
│       ├── certificate_chain.pem
│       └── provisioning_data.json
│
├── generate_ca.py                  # Generate SSA CA hierarchy
├── provision_software.py           # Provision software with certificate
├── ssa_server.py                   # Flask validation server
├── requirements.txt                # Python dependencies
└── README.md                       # This file
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Generate CA certificates:**
   ```bash
   python3 generate_ca.py
   ```

   This creates:
   - SSA root CA (10-year validity)
   - SSA intermediate CA (5-year validity)
   - Both private keys are encrypted with password: `birthmark-ssa-dev-password`

3. **Provision editing software:**
   ```bash
   python3 provision_software.py \
     --software-id "GIMP-Wrapper-POC-001" \
     --wrapper-path /path/to/your/plugin.py \
     --version "1.0.0"
   ```

   This generates:
   - Software certificate (1-year validity)
   - Software private key (unencrypted for POC)
   - Certificate chain (software → intermediate → root)
   - Provisioning metadata (baseline hash, versioned hash, valid versions)

4. **Start the SSA validation server:**
   ```bash
   python3 ssa_server.py
   ```

   Server runs on: `http://0.0.0.0:8001`

## Usage

### Provision New Software

```bash
python3 provision_software.py \
  --software-id "MyEditor-Plugin-001" \
  --wrapper-path ./my_plugin.py \
  --version "1.0.0" \
  --supported-editors GIMP Photoshop
```

**Output:**
- `provisioned_software/myeditor-plugin-001/software_certificate.pem`
- `provisioned_software/myeditor-plugin-001/software_private_key.pem`
- `provisioned_software/myeditor-plugin-001/certificate_chain.pem`
- `provisioned_software/myeditor-plugin-001/provisioning_data.json`

### Validate Software

**Endpoint:** `POST /api/v1/validate/software`

**Request:**
```json
{
  "software_certificate": "<PEM encoded certificate>",
  "current_wrapper_hash": "<SHA-256 hash of wrapper baseline>",
  "version": "1.0.0"
}
```

**Success Response (200):**
```json
{
  "validation_result": "PASS",
  "software_id": "GIMP-Wrapper-POC-001",
  "version": "1.0.0",
  "authority": "SimulatedSoftwareAuthority",
  "supported_editors": ["GIMP"],
  "timestamp": "2025-11-15T12:00:00"
}
```

**Failure Response (400):**
```json
{
  "validation_result": "FAIL",
  "reason": "Version 2.0.0 not authorized",
  "valid_versions": ["1.0.0"],
  "software_id": "GIMP-Wrapper-POC-001",
  "timestamp": "2025-11-15T12:00:00"
}
```

### Add Valid Version

**Endpoint:** `POST /api/v1/versions/add`

**Request:**
```json
{
  "software_id": "GIMP-Wrapper-POC-001",
  "version": "1.1.0"
}
```

**Response (200):**
```json
{
  "status": "success",
  "software_id": "GIMP-Wrapper-POC-001",
  "valid_versions": ["1.0.0", "1.1.0"],
  "timestamp": "2025-11-15T12:00:00"
}
```

### Health Check

**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "SSA Validation Server",
  "registered_software": 2,
  "software_list": ["GIMP-Wrapper-POC-001", "MyEditor-Plugin-001"],
  "timestamp": "2025-11-15T12:00:00"
}
```

## Testing the System

### Example Test Flow

1. **Create a test wrapper file:**
   ```bash
   echo "# Test wrapper v1.0.0" > test_wrapper.py
   ```

2. **Provision the software:**
   ```bash
   python3 provision_software.py \
     --software-id "Test-Wrapper-001" \
     --wrapper-path test_wrapper.py \
     --version "1.0.0"
   ```

3. **Start the SSA server:**
   ```bash
   python3 ssa_server.py
   ```

4. **Test validation (in another terminal):**
   ```bash
   # Compute baseline hash
   BASELINE_HASH=$(sha256sum test_wrapper.py | cut -d' ' -f1)

   # Load certificate
   CERT=$(cat provisioned_software/test-wrapper-001/software_certificate.pem)

   # Make validation request
   curl -X POST http://localhost:8001/api/v1/validate/software \
     -H "Content-Type: application/json" \
     -d '{
       "software_certificate": "'"$CERT"'",
       "current_wrapper_hash": "'"$BASELINE_HASH"'",
       "version": "1.0.0"
     }'
   ```

5. **Test adding a new version:**
   ```bash
   curl -X POST http://localhost:8001/api/v1/versions/add \
     -H "Content-Type: application/json" \
     -d '{
       "software_id": "Test-Wrapper-001",
       "version": "1.1.0"
     }'
   ```

## Security Model

### Trust Assumptions

1. **SSA is Honest**: Only authorizes valid versions of legitimate plugins
2. **Certificate Chain is Secure**: Private keys are properly protected
3. **Baseline Hash is Immutable**: Original plugin hash stored at provisioning is trusted
4. **Version String is Embedded**: Plugin contains version constant matching SSA's valid versions
5. **Network Communication is Secure**: HTTPS in production

### Validation Flow

1. Plugin computes its own baseline hash at runtime
2. Plugin sends: certificate + baseline hash + version to SSA
3. SSA validates:
   - Certificate is valid and not expired
   - Software is registered in provisioning database
   - Version is in the valid versions list
   - Computed versioned hash matches expected hash
4. SSA returns PASS/FAIL to aggregation server

### Attack Mitigations

| Attack | Mitigation | Residual Risk |
|--------|------------|---------------|
| Modified plugin claims to be original | Hash mismatch → validation fails | Low |
| Old version with vulnerabilities | Version not in valid list → validation fails | Low |
| Forked plugin | Different baseline hash → validation fails | Low |
| Man-in-the-middle | HTTPS with cert pinning (production) | Low (with proper TLS) |
| Tampering after installation | Validation on each use; modified code fails hash check | Medium (runtime attacks possible) |

### POC Limitations

This is a proof of concept. **Not suitable for production** without:
- Proper key management (HSM, key vault)
- Certificate revocation (CRL/OCSP)
- Audit logging
- Rate limiting and DDoS protection
- Full certificate chain validation
- Secure password management (environment variables, secrets manager)

## Development

### CA Password

The CA private keys are encrypted with password: `birthmark-ssa-dev-password`

**In production:**
- Use environment variables or secure key management system
- Rotate passwords regularly
- Use HSM for CA key storage

### Certificate Validity Periods

- **Root CA:** 10 years (3650 days)
- **Intermediate CA:** 5 years (1825 days)
- **Software Certificate:** 1 year (365 days)

### Adding a New Software Version

When a plugin is updated:

1. Developer increments version constant in plugin code
2. Developer registers new version with SSA:
   ```bash
   curl -X POST http://localhost:8001/api/v1/versions/add \
     -H "Content-Type: application/json" \
     -d '{"software_id": "GIMP-Wrapper-POC-001", "version": "1.1.0"}'
   ```
3. Plugin validates successfully with new version

**Note:** The baseline hash remains the same! Only the version string changes, which produces a different versioned hash.

## API Reference

### POST /api/v1/validate/software

Validates software certificate and integrity.

**Request Body:**
- `software_certificate` (string): PEM-encoded certificate
- `current_wrapper_hash` (string): SHA-256 hash of wrapper baseline
- `version` (string): Version string

**Response:**
- `validation_result` (string): "PASS" or "FAIL"
- `software_id` (string): Registered software ID
- `version` (string): Validated version
- `authority` (string): Authority name
- `supported_editors` (array): List of supported editors
- `timestamp` (string): ISO 8601 timestamp

### POST /api/v1/versions/add

Adds a new valid version for existing software.

**Request Body:**
- `software_id` (string): Registered software ID
- `version` (string): New version to add

**Response:**
- `status` (string): "success" or "error"
- `software_id` (string): Software ID
- `valid_versions` (array): Updated list of valid versions
- `timestamp` (string): ISO 8601 timestamp

### GET /health

Health check endpoint.

**Response:**
- `status` (string): "healthy"
- `service` (string): Service name
- `registered_software` (integer): Count of registered software
- `software_list` (array): List of registered software IDs
- `timestamp` (string): ISO 8601 timestamp

## Integration with Birthmark System

### Camera → Aggregator → SSA Flow

1. **Camera** captures image and submits hash to **Aggregator**
2. **Editing software** loads authenticated image
3. **Plugin** validates itself with **SSA** on initialization
4. **Plugin** tracks modifications and creates provenance record
5. **Plugin** submits modification record to **Aggregator**
6. **Aggregator** validates plugin certificate with **SSA**
7. **SSA** returns PASS/FAIL (never sees image hash)
8. **Aggregator** records modification in provenance chain

### Privacy Invariants

- **SSA never sees image hashes** - only validates software authenticity
- **Aggregator cannot track individual plugins** - rotating encrypted tokens (future enhancement)
- **Images never stored** - only SHA-256 hashes
- **SSA validates software, not content** - separation of concerns

## Troubleshooting

### Certificate Not Found

**Error:** `FileNotFoundError: ssa-intermediate-ca.crt`

**Solution:** Run `python3 generate_ca.py` first to generate CA certificates.

### Software Not Registered

**Error:** `{"validation_result": "FAIL", "reason": "Software not registered"}`

**Solution:** Provision the software first with `provision_software.py`.

### Version Not Authorized

**Error:** `{"validation_result": "FAIL", "reason": "Version X.X.X not authorized"}`

**Solution:** Add the version to valid list using `/api/v1/versions/add` endpoint.

### Hash Mismatch

**Error:** `{"validation_result": "FAIL", "reason": "Wrapper integrity check failed"}`

**Solution:** The wrapper file has been modified. Re-provision or revert changes.

## Future Enhancements

### Production Readiness
- [ ] HSM integration for CA keys
- [ ] Certificate revocation (CRL/OCSP)
- [ ] Full certificate chain validation
- [ ] Audit logging for all operations
- [ ] Rate limiting and DDoS protection
- [ ] Database backend (PostgreSQL) instead of JSON files
- [ ] HTTPS with proper TLS configuration

### Feature Additions
- [ ] Rotating encrypted tokens for privacy
- [ ] Multi-factor authentication for admin endpoints
- [ ] Automated certificate renewal
- [ ] Batch validation for performance
- [ ] Webhook notifications for events
- [ ] Monitoring and alerting integration

## License

Part of the Birthmark Standard - Open source (license TBD)

## Contact

**Project:** The Birthmark Standard Foundation
**Repository:** github.com/Birthmark-Standard/Birthmark

For issues and questions, see the main project repository.
