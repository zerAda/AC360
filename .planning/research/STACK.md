# STACK.md — Copilot Studio + SharePoint Technology Stack

## Required Components

### Core Stack

| Component | Purpose | Version | Confidence |
|-----------|---------|---------|-----------|
| **Microsoft 365** | Base licensing | Current | High |
| **Copilot Studio** | Agent creation | Generative AI enabled | High |
| **SharePoint** | Knowledge source | Modern | High |
| **Microsoft Teams** | Primary interface | Current | High |
| **Microsoft Entra ID** | Authentication | Current | High |

### Optional (Not Required for POC)

| Component | Purpose | Notes |
|-----------|---------|-------|
| Microsoft 365 Copilot | Better semantic search | Recommended but optional |
| Dataverse | File storage | Not needed for Scenario A |
| Azure AI Search | Advanced indexing | Out of scope |

## Technology Details

### Copilot Studio Agent

- **Creation**: Web-based Copilot Studio portal
- **Knowledge source**: SharePoint URL connection
- **Authentication**: Microsoft (built-in for Teams/SharePoint)
- **Publishing**: Teams or SharePoint

### SharePoint Integration

- **Connection type**: SharePoint URL (connector)
- **Search**: Uses SharePoint search index
- **Permissions**: Respects user SharePoint permissions
- **File support**: DOCX, PDF, PPTX (up to 200MB with M365 Copilot)

### Limitations

- Max 4 SharePoint URLs per agent (7MB each without M365 Copilot)
- Single SharePoint site per knowledge source
- Content freshness depends on SharePoint search indexing

---

*Research: Stack for Copilot Studio + SharePoint - 2026-04-28*