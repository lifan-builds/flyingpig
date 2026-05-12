# Flying Pig Beta Checklist

## Beta Scope

- Site: American Express.
- UX: Chrome side panel controlling the local helper service.
- User mode: supervised only. The user keeps the Amex tab visible and answers mid-run questions.
- Initial playbooks: general support, benefit/credit follow-up, dispute charge.

## Install Flow

1. Install the Python package in editable/dev mode for the first beta cohort:

   ```bash
   pip install -e ".[dev]"
   playwright install
   ```

2. Install the macOS helper service:

   ```bash
   flyingpig-macos-helper install
   ```

3. Load `extension/` as an unpacked Chrome extension.
4. Open the side panel and click **Launch Chrome**.
5. In the FlyingPig Chrome window, prepare the Amex customer-service tab.
6. Confirm the task and supervise the run.

If the copied default Chrome profile is not available yet, quit normal Chrome once and click **Launch Chrome** again. For a clean profile that can run beside normal Chrome during development:

```bash
flyingpig-helper --chrome-profile dedicated
```

Support commands:

```bash
flyingpig-macos-helper status
flyingpig-macos-helper stop
flyingpig-macos-helper start
flyingpig-macos-helper uninstall
```

## Build Release Bundle

Create a local beta zip:

```bash
python scripts/build_beta_release.py --clean
```

The bundle includes the helper code, prompts, Chrome extension, README, and beta install guide.

## Pre-Beta Gates

- `ruff check src scripts tests` passes.
- `pytest tests -q -m "not slow"` passes.
- `npm run test:extension` passes.
- `python scripts/build_beta_release.py --clean` produces `dist/flyingpig-beta-0.1.0.zip`.
- `flyingpig-macos-helper status` shows the helper running after install.
- A supervised Amex smoke reaches chat, sends only after user confirmation, and captures a transcript.
- Cancel from the side panel stops an active run.
- Helper-offline state in the side panel clearly tells users to start the helper.
- Launch Chrome from the side panel returns a CDP endpoint and opens the Amex page.

## Beta Operating Rules

- Do not store Amex credentials.
- Do not ask the agent to make irreversible account changes without explicit user confirmation.
- Review every first-cohort transcript before expanding access.
- Record outcome, failure stage, transcript path, and whether human escalation succeeded.
