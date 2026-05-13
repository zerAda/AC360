# ARCHITECTURE.md — Copilot Studio + SharePoint Architecture

## Component Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Commercial │────>│   Teams    │────>│  Copilot   │
│   (user)   │     │  (chat)    │     │   Studio   │
└─────────────┘     └─────────────┘     │   Agent   │
                                    └─────┬─────┘
                                          │
                                    ┌─────┴─────────┐
                                    │   SharePoint  │
                                    │   (source)   │
                                    └─────────────┘
```

## Components

| Component | Role | Boundary |
|-----------|------|----------|
| **Teams** | User interface | User input |
| **Copilot Studio Agent** | Orchestration | Logic, responses |
| **SharePoint** | Knowledge source | Documents |
| **Entra ID** | Authentication | Permissions |

## Data Flow

1. User asks question in Teams
2. Agent receives via Copilot Studio
3. Agent validates user permissions (Entra ID)
4. Agent queries SharePoint search
5. Agent retrieves authorized content
6. Agent generates response
7. Agent cites sources
8. Response sent back to Teams

## Build Order

1. **Setup** → Create Copilot Studio environment
2. **Connect** → Add SharePoint as knowledge source
3. **Configure** → Set agent instructions (system prompt)
4. **Test** → Validate with sample questions
5. **Publish** → Deploy to Teams
6. **Iterate** → Refine based on feedback

---

*Research: Architecture for Copilot Studio + SharePoint - 2026-04-28*