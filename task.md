
## Storing OAuth Token for reuse

### Purpose:
OAuth access tokens are currently stored in memory (see InMemoryTokenStorage in mcp_client/client_session_provider.py). The purpose of this task is
to store them in a secure storage for reuse.

### High level solution:

Dual Storage Strategy:
  1. Primary: System keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service)
  2. Fallback: Secured file storage if keychain unavailable

  Key Features:
  - Automatic fallback: Falls back to file storage if keychain access fails
  - Configurable security: Can disable keychain and use file-only storage
  - Cross-platform support: Works across different operating systems

  Storage Locations

  System Keychain

  - Service Name: "contextkit"
  - Username: "secrets"
  - Storage: Platform-specific secure storage (Keychain Access on macOS, etc.)

  File Fallback

  - Location: ~/.config/contextkit/secrets.yaml (or platform-specific app data directory)
  - Format: YAML-serialized credential data
  - Permissions: Restricted file permissions for security


### Scope of task:
- Create a new class KeychainTokenStorageWithFallback under mcp_client/token_storage.py folder to manage the OAuth tokens (replaces InMemoryTokenStorage and impl TokenStorage).
- The new class is initialized with the State class in state.py which will be passed. The state can contain any configuration needed for the storage like path names, names of service names in keychain, etc.
- Implement the dual storage strategy as described above.