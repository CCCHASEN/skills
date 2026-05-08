---
name: apple
description: "Apple ecosystem automation for macOS: Notes, Reminders, FindMy, and iMessage. Route to the right tool based on the user's intent."
metadata:
  hermes:
    tags: [Apple, macOS, Notes, Reminders, FindMy, iMessage]
    related_skills: []
---

# Apple Ecosystem Skill

macOS-native app automation via CLI tools. All commands require macOS and the respective app installed.

## Quick Router

| User Says | Tool | Reference |
|-----------|------|-----------|
| "create a note", "save to Notes" | `memo` (Apple Notes) | `references/apple-notes.md` |
| "remind me", "set a reminder", "to-do" | `remindctl` (Reminders) | `references/apple-reminders.md` |
| "where is my phone/AirTag/device?" | FindMy.app + AppleScript | `references/findmy.md` |
| "send a message", "text someone" | `imsg` (Messages) | `references/imessage.md` |

## macOS Permission Checklist

All Apple tools require granting terminal access in **System Settings → Privacy & Security**:

- **memo** → Automation → Notes.app
- **remindctl** → Reminders
- **FindMy** → Screen Recording (for UI capture)
- **imsg** → Full Disk Access + Automation → Messages.app

## Common Installation Path

```bash
# memo (Notes)
brew tap antoniorodr/memo && brew install antoniorodr/memo/memo

# remindctl (Reminders)
brew install steipete/tap/remindctl

# imsg (Messages)
brew install steipete/tap/imsg

# peekaboo (optional, for FindMy UI automation)
brew install steipete/tap/peekaboo
```

## Workflow: Capture → Organize → Communicate → Locate

1. **Capture information** → `memo` (Apple Notes) — syncs across iCloud
2. **Organize tasks** → `remindctl` (Reminders) — due dates, lists, completion
3. **Communicate** → `imsg` (Messages) — iMessage/SMS with history
4. **Locate devices** → FindMy.app — devices and AirTags

For detailed commands, installation, permissions, and edge cases — load the specific reference above.
