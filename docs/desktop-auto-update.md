# Desktop Auto-Update Path

Flying Pig uses `electron-updater` with `electron-builder` GitHub publishing metadata as
the desktop auto-update path. The GitHub repository is public, so installed apps can
read release assets without an embedded token.

## Release Flow

1. Build the Python helper sidecar:

   ```bash
   npm run build:helper
   ```

2. Build and publish the desktop release artifacts from a signed macOS release
   environment:

   ```bash
   npm run desktop:publish
   ```

3. Publish against the `lifan-builds/flyingpig` GitHub Releases feed. The updater
   expects the release assets and generated metadata, including `latest-mac.yml`,
   to be attached to the GitHub Release for the matching app version.

4. Verify the local package and published update assets:

   ```bash
   npm run desktop:verify-update -- --require-signed --github --tag=vX.Y.Z
   ```

## Product Behavior

- Packaged desktop builds check for updates after app startup.
- Users can run **Flying Pig -> Check for Updates** from the macOS menu.
- Downloaded updates enable **Flying Pig -> Install Update and Relaunch**.
- Development runs skip update checks; updater behavior is only active in packaged
  desktop builds.
- Helper updates ship inside the desktop app resources, so updating the app updates
  the packaged helper sidecar too.

## Required Release Secrets

The GitHub Actions desktop release workflow requires these repository secrets:

- `MAC_CSC_LINK`: Developer ID Application certificate as a `.p12` link or base64
  value supported by `electron-builder`.
- `MAC_CSC_KEY_PASSWORD`: password for the signing certificate.
- `APPLE_API_KEY_P8`: App Store Connect API key file contents.
- `APPLE_API_KEY_ID`: App Store Connect API key id.
- `APPLE_API_ISSUER`: App Store Connect issuer id.
- `APPLE_TEAM_ID`: Apple Developer Team ID.

Do not commit any of these values or embed them in the app.

## Verification Gates

- `npm run desktop:verify-update` confirms `latest-mac.yml` points to an existing
  zip, the size matches, and the `sha512` digest matches.
- `npm run desktop:verify-update -- --require-signed` additionally requires local
  code-signing and Gatekeeper assessment to pass.
- `npm run desktop:verify-update -- --github --tag=vX.Y.Z` checks that the public
  GitHub Release has the zip, blockmap, and `latest-mac.yml` assets needed by
  installed apps.
- The workflow runs the verifier with both `--require-signed` and `--github`, so a
  release cannot pass if update assets are missing or unsigned.

## Current Notes

- The previously published `v1.0.1` release does not include `latest-mac.yml`, so
  it is not an update-capable baseline.
- The first update-capable baseline should be a new signed release, expected to be
  `v1.0.2` unless another version is chosen.
- The local development machine currently has no valid Developer ID identity; use
  the GitHub Actions release workflow after secrets are configured, or install the
  certificate locally before publishing.
- Keep the release scan gate: artifacts must not include PII, API keys, credentials,
  tokens, cookies, logs, recordings, databases, or user-specific account data.
