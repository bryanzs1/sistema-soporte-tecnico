# Post-Launch Checklist (48h)

## 1) Health and uptime
- Verify Render deploy status is successful.
- Check app startup logs for exceptions.
- Confirm health endpoint/pages respond in < 2s.

## 2) Core smoke tests
- Login with admin, technician, and user accounts.
- Create ticket as user.
- Add comment from technician.
- Update status to En proceso and Cerrado.
- Reopen ticket with reason (within 7 days) and verify comment is saved.
- Validate ticket timeline updates.

## 3) Notifications
- Confirm reopen notification email reaches requester and assigned technician.
- Confirm webhook notifications (if enabled) are delivered.

## 4) Security and confirmations
- Confirm logout asks for confirmation.
- Confirm unsaved changes warning appears on form navigation.
- Confirm close ticket requires strong confirmation text.
- Confirm API token revoke requires strong confirmation text.

## 5) Data integrity
- Verify no ticket disappears from list after create/update.
- Check audit logs for key actions and failures.
- Ensure no hard-delete actions are enabled for tickets.

## 6) Performance and capacity
- Check slow endpoints in logs (ticket list, detail, dashboard).
- Validate DB connection health and error rate.
- Monitor memory/cpu on Render service.

## 7) User and technician UX
- Verify KB suggestions appear while typing ticket description.
- Verify quick replies are available to technician/admin in chat.
- Verify mobile usability on ticket create/detail pages.

## 8) Rollback readiness
- Identify previous stable commit hash.
- Confirm rollback command/process in Render is documented.
- Confirm database backup is available before major changes.
