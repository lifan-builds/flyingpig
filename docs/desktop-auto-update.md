# Desktop Beta Update Path

Flying Pig currently uses a no-paid-Apple-account beta update path on macOS. The
packaged app checks the public `lifan-builds/flyingpig` GitHub Releases feed and,
when a newer release exists, opens the latest release page so the user can download
and replace the app manually.

This is intentionally **not** full in-place auto-update on macOS. Unsigned apps can
be packaged and distributed for beta users, but reliable self-installing updates
require Developer ID signing and notarization.

## Release Flow

1. Build the Python helper sidecar:

   ```bash
   npm run build:helper
   ```

2. Build and publish the desktop release artifacts from GitHub Actions:

   ```bash
   npm run desktop:publish
   ```

3. Publish against the `lifan-builds/flyingpig` GitHub Releases feed. The beta
   updater reads the latest GitHub Release and sends users to the release page.
   `latest-mac.yml` is still generated and verified so the signed auto-update path
   can be restored later without changing release shape.

4. Verify the local package and published update assets:

   ```bash
   npm run desktop:verify-update -- --github --tag=vX.Y.Z
   ```

## Product Behavior

- Packaged desktop builds check the GitHub latest release after app startup.
- Users can run **Flying Pig -> Check for Updates** from the macOS menu.
- Users can run **Flying Pig -> Download Latest Version** to open the latest
  GitHub Release in their browser.
- Users manually replace the installed app after downloading a newer beta.
- Development runs skip update checks; updater behavior is only active in packaged
  desktop builds.
- Helper updates ship inside the desktop app resources, so updating the app updates
  the packaged helper sidecar too.

## Optional Signed Release Secrets

The current unsigned beta release workflow does **not** require paid Apple signing
secrets. If we later move to reliable in-place macOS auto-update, the GitHub
Actions desktop release workflow will need these repository secrets:

- `MAC_CSC_LINK`: Developer ID Application certificate as a `.p12` link or base64
  value supported by `electron-builder`.
- `MAC_CSC_KEY_PASSWORD`: password for the signing certificate.
- `APPLE_API_KEY_P8`: App Store Connect API key file contents.
- `APPLE_API_KEY_ID`: App Store Connect API key id.
- `APPLE_API_ISSUER`: App Store Connect issuer id.
- `APPLE_TEAM_ID`: Apple Developer Team ID.

Do not commit any of these values or embed them in the app.

## Future Developer ID Setup

Flying Pig needs a **Developer ID Application** certificate only when we decide to
ship reliable signed/notarized in-place updates. Apple issues Developer ID
certificates only through a paid Apple Developer Program or Apple Developer
Enterprise Program team, and the Account Holder role is required to create the
certificate. Apple allows up to five Developer ID Application certificates per
account.

1. Generate a Certificate Signing Request on the Mac that will own the private key:

   - Open **Keychain Access** in `/Applications/Utilities`.
   - Choose **Keychain Access -> Certificate Assistant -> Request a Certificate
     from a Certificate Authority**.
   - Enter the Apple Developer account email and a clear common name, for example
     `Flying Pig Developer ID`.
   - Leave CA Email Address empty, choose **Saved to disk**, and save the
     `.certSigningRequest` file.

2. Create the certificate in Apple Developer:

   - Open [Certificates, Identifiers & Profiles](https://developer.apple.com/account/resources/certificates/list).
   - Click **Certificates**, then the add button.
   - Under Software, choose **Developer ID -> Developer ID Application**.
   - Upload the `.certSigningRequest`, continue, then download the `.cer`.
   - Double-click the downloaded `.cer` so it appears in Keychain Access under
     **My Certificates** with its private key.

3. Confirm the local identity exists:

   ```bash
   security find-identity -v -p codesigning
   npm run desktop:check-signing
   ```

   The identity must look like `Developer ID Application: <name> (<TEAM_ID>)`.

4. Export the certificate for GitHub Actions:

   - In Keychain Access, select the **Developer ID Application** certificate under
     **My Certificates** and expand it to confirm the private key is present.
   - Export the certificate plus private key as a password-protected `.p12`.
   - Convert it to base64 without printing the result into shell history:

     ```bash
     base64 -i path/to/FlyingPigDeveloperID.p12 | pbcopy
     gh secret set MAC_CSC_LINK --repo lifan-builds/flyingpig
     gh secret set MAC_CSC_KEY_PASSWORD --repo lifan-builds/flyingpig
     ```

   Paste the copied base64 value when `gh secret set MAC_CSC_LINK` prompts, and
   enter the `.p12` export password for `MAC_CSC_KEY_PASSWORD`.

5. Create the App Store Connect API key for notarization:

   - In [App Store Connect](https://appstoreconnect.apple.com/access/integrations/api),
     open **Users and Access -> Integrations -> App Store Connect API**.
   - Use a **Team Key**. Apple documents that individual keys cannot use
     `notaryTool`.
   - Generate an API key, download the `.p8` once, and record its Key ID and Issuer
     ID.
   - Add these repository secrets:

     ```bash
     gh secret set APPLE_API_KEY_P8 --repo lifan-builds/flyingpig < path/to/AuthKey_KEYID.p8
     gh secret set APPLE_API_KEY_ID --repo lifan-builds/flyingpig
     gh secret set APPLE_API_ISSUER --repo lifan-builds/flyingpig
     gh secret set APPLE_TEAM_ID --repo lifan-builds/flyingpig
     ```

6. Verify GitHub secret names are present:

   ```bash
   npm run desktop:check-signing -- --github
   ```

   This checks only whether the expected secret names exist; it does not print or
   validate secret values.

## Verification Gates

- `npm run desktop:verify-update` confirms `latest-mac.yml` points to an existing
  zip, the size matches, and the `sha512` digest matches.
- `npm run desktop:verify-update -- --require-signed` additionally requires local
  code-signing and Gatekeeper assessment to pass.
- `npm run desktop:verify-update -- --github --tag=vX.Y.Z` checks that the public
  GitHub Release has the zip, blockmap, and `latest-mac.yml` assets needed by
  future signed update feeds.
- `npm run desktop:check-signing` checks whether this Mac has a local Developer ID
  Application identity and the local release environment variables. Add `-- --github`
  to check that required GitHub repository secret names exist.
- The unsigned beta workflow runs the verifier with `--github`, so a release cannot
  pass if public update assets are missing. It intentionally does not require code
  signing.

## Current Notes

- The previously published `v1.0.1` release does not include `latest-mac.yml`, so
  it is not an update-capable baseline.
- The first no-pay beta update-checking baseline should be `v1.0.2` unless another
  version is chosen.
- The local development machine currently has no valid Developer ID identity. That
  is acceptable for the unsigned beta path.
- Keep the release scan gate: artifacts must not include PII, API keys, credentials,
  tokens, cookies, logs, recordings, databases, or user-specific account data.
