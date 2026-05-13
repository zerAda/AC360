# PITFALLS.md — Common Pitfalls for Copilot Studio + SharePoint POC

## Pitfalls to Avoid

### 1. Permission Configuration

| Pitfall | Warning Signs | Prevention | Phase |
|--------|---------------|------------|--------|
| Users see unauthorized content | Test with non-accessible folder | Verify permissions before rollout | Setup |

### 2. SharePoint Search Indexing

| Pitfall | Warning Signs | Prevention | Phase |
|--------|---------------|------------|--------|
| Old content shown | Recent docs not found | Wait for indexing or force sync | Setup |

### 3. Vague Questions

| Pitfall | Warning Signs | Prevention | Phase |
|--------|---------------|------------|--------|
| Agent guesses | Invented information | Clear "not found" instructions | Configure |

### 4. Large File Issues

| Pitfall | Warning Signs | Prevention | Phase |
|--------|---------------|------------|--------|
| Files not processed | Error messages, incomplete answers | Split files >7MB | Setup |

### 5. Ambiguous Client Names

| Pitfall | Warning Signs | Prevention | Phase |
|--------|---------------|------------|--------|
| Wrong client matched | Mix of two clients | Ask for clarification | Configure |

---

*Research: Common pitfalls for Copilot Studio + SharePoint - 2026-04-28*