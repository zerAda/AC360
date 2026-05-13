# Phase 1: Setup & Agent Creation - Research

**Phase:** 01  
**Goal:** Create Copilot Studio agent connected to SharePoint with basic configuration

## Requirements

- QI-01: User can ask questions via Teams to the agent
- QI-02: User can ask questions via SharePoint to the agent
- QI-03: Agent understands natural language questions
- CFA-01: Agent connects to specified SharePoint site
- CFA-02: Agent reads documents from SharePoint folders
- CFA-03: Agent respects SharePoint user permissions
- CFA-04: Agent filters content by user's access rights
- SAF-01: Agent says "not found" when information unavailable
- SAF-04: Agent requests clarification for ambiguous client names

## Project Context

From PROJECT.md:
- Tech Stack: Copilot Studio only, no Azure AI Search
- Data Source: SharePoint only
- Security: SharePoint permissions as baseline
- Timeline: 2-week POC
- Scope: 10-20 client folders, 3-5 pilot users

## Existing Research Reference

See `.planning/research/` for full context:
- STACK.md - Technology stack (Copilot Studio, SharePoint, Teams, Entra ID)
- ARCHITECTURE.md - System architecture and data flow
- FEATURES.md - Feature capabilities
- PITFALLS.md - Known issues to avoid

## Phase-Specific Research

### Copilot Studio Agent Setup

**Agent Creation Process:**
1. Access Copilot Studio (copilotstudio.microsoft.com)
2. Create new agent with "Create" button
3. Configure name and description
4. Add knowledge sources (SharePoint)
5. Configure generative AI settings
6. Set system instructions
7. Test with sample questions
8. Publish to Teams/SharePoint

**Knowledge Source Configuration:**
- SharePoint URL connection (max 4 URLs per agent)
- Single SharePoint site per knowledge source
- Respects SharePoint permissions automatically
- Content freshness: depends on SharePoint search indexing

**System Instructions (Initial):**
```
You are an assistant that helps commercial teams prepare for client meetings.
- Only answer based on information found in the provided SharePoint documents
- If information is not found, say "I couldn't find that information"
- If client name is ambiguous, ask for clarification
- Always cite the source document in your response
- Never invent information
```

### Teams Integration

**Publish to Teams:**
1. In Copilot Studio, go to "Channels"
2. Enable Microsoft Teams channel
3. Configure privacy (org-wide or specific users)
4. Test in Teams chat

**SharePoint Integration**

**Publish to SharePoint:**
1. In Copilot Studio, go to "Channels"
2. Enable SharePoint channel
3. Select target SharePoint site/page
4. Configure embed options

### Permissions (SharePoint)

- Agent inherits user's SharePoint permissions
- No additional permission configuration needed
- CFA-03 and CFA-04 satisfied by SharePoint's built-in permission model

## Key Decisions for Planning

1. **Teams vs SharePoint as primary interface**
   - Teams recommended as primary (more interactive)
   - SharePoint as fallback/additional channel

2. **Initial system instructions**
   - Keep simple, iterate based on testing
   - Focus on safety first (SAF-01, SAF-04)

3. **SharePoint site selection**
   - Need a test site with sample client folders
   - Recommend 3-5 folders for POC

## Validation Architecture

For Nyquist validation, Phase 1 needs:
- Functional test: Agent responds in Teams
- Functional test: Agent connects to SharePoint
- Functional test: Agent respects permissions (simulated)
- Integration test: Natural language question returns result

---

*Research completed: 2026-04-28*
*Source: Project research (.planning/research/) + Phase requirements*