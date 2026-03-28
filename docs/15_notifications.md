# Notification System (Slack Integration)

This document describes the real-time notification system implemented for the Automated Book Generation System.

## Why Slack Webhooks?

Slack webhooks provide a simple, robust way to send real-time alerts to a team channel. They are non-blocking and ensure that all stakeholders are immediately informed of critical project events without needing to check the database or logs manually.

## Triggered Events

Notifications are sent to the configured Slack channel during the following events:

| Event | Icon | Message Details |
| :--- | :---: | :--- |
| **Outline Generated** | 📘 | Initial outline or version ready for human review. |
| **Review Waiting** | 🟡 | Outline requires editor feedback before proceeding. |
| **Outline Paused** | ⛔ | Outline stage is explicitly paused (HITL). |
| **Chapter Ready** | 📝 | Chapter draft generation is complete and pending review. |
| **Chapter Blocked** | ⏳ | Chapter generation halted because a previous chapter isn't approved. |
| **Chapter Regenerated** | 🔄 | A chapter has been rewritten based on feedback. |
| **Compilation Ready** | ✅ | The book's final draft has been compiled successfully. |
| **Compile Blocked** | ⚠️ | Compilation attempt failed due to review status or missing notes. |
| **System Blocks** | ⚠️ | Workflow interrupted due to missing required user input. |

## Configuration

To enable Slack notifications:

1. Create an **Incoming Webhook** in your Slack workplace.
2. Copy the Webhook URL.
3. Add it to your `.env` file:
   ```bash
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   ```

## Fallback Behavior

The notification system is designed to be **fail-safe**:
- If `SLACK_WEBHOOK_URL` is missing from the environment, the system gracefully fallbacks to local console logging: `[NOTIFICATION - LOCAL LOG] {message}`.
- If the Slack API is down or returns an error, the error is logged locally, and the primary application workflow continues uninterrupted.
- Network timeouts are capped at 5 seconds to ensure the API response time remains fast.

## Note on MS Teams

This notification service uses a generic pattern that can be easily extended to MS Teams or Discord by adding additional webhook URL configurations and updating the `send_notification` service logic.
