# Flying Pig Public Beta Quickstart

Flying Pig is a supervised Mac desktop app for customer-service chats. The app is
the cockpit. The separate work window is the browser area where you log in,
handle MFA, open support chat, and watch the agent work.

## Install

1. Download the latest `Flying-Pig-*-arm64-mac.zip` from
   [GitHub Releases](https://github.com/lifan-builds/flyingpig/releases).
2. Unzip the download and open `Flying Pig.app`.
3. If macOS blocks the app because it is unsigned, approve it in **System
   Settings -> Privacy & Security** and open it again.

The current beta is unsigned. Flying Pig checks GitHub Releases for newer
versions and opens the release page when one is available. Replacing the app is
manual for now.

## First Run

1. In **Model setup**, choose a provider and save an API key.
   - CLIProxyAPI works if your local CLIProxyAPI setup is already configured.
   - Claude, OpenAI, and Gemini need their own provider keys.
   - Keys are stored only in `~/.flyingpig/.env`.
2. Click **Open Work Window**.
3. In the work window, log in if needed and navigate to the support page or chat.
4. Choose a brief starter or write the exact customer-service goal.
5. Press **Start** once the readiness strip shows the model, work window, chat
   surface, and task brief are ready.
6. Stay near the app for approval checkpoints, MFA prompts, offer decisions, or
   Hangup and Call-again recovery.
7. When the run finishes, mark the result as **Solved**, **Partial**, or
   **Failed**. Flying Pig keeps local, PII-free beta stats from those outcomes.

## Good First Tasks

- Ask for a bill reduction or retention offer.
- Dispute a fee or charge.
- Request a refund, statement credit, or courtesy credit.
- Cancel a subscription after reviewing the exact cancellation message.
- Escalate from a chatbot to a human representative.
- Continue an existing support chat that is already visible in the work window.

## Safety Boundaries

- Login, passwords, and MFA stay in the work-window browser.
- Flying Pig asks before irreversible account changes, offer acceptance,
  sensitive verification, or Hangup and Call-again recovery.
- The work window uses a dedicated Flying Pig profile by default, separate from
  your everyday Chrome profile.
- Do not use the beta for unsupported phone-only, email-only, or unsupervised
  account-change workflows.
