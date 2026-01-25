# Web Application Testing Skill

Automated testing of web applications using Python and Playwright.

**Source:** [anthropics/skills/webapp-testing](https://github.com/anthropics/skills)

## When to Use

Load this skill when:
- Project has a web frontend (React, Vue, Angular, etc.)
- E2E/integration tests require browser automation
- Testing dynamic content that requires JavaScript execution

## Core Pattern: Reconnaissance-Then-Action

1. Navigate to target URL
2. Wait for network idle: `page.wait_for_load_state('networkidle')`
3. Inspect rendered DOM to discover selectors
4. Execute automation actions

## Server Management

Use `with_server.py` to manage server lifecycle:

```bash
# Single server
python skills/webapp-testing/scripts/with_server.py \
  --server "npm run dev" --port 5173 \
  -- python test_script.py

# Multiple servers (backend + frontend)
python skills/webapp-testing/scripts/with_server.py \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python test_script.py
```

## Playwright Test Template

```python
from playwright.sync_api import sync_playwright

def run_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Navigate and wait for content
        page.goto("http://localhost:5173")
        page.wait_for_load_state('networkidle')

        # Discover selectors via screenshot or DOM inspection
        page.screenshot(path="page.png")

        # Execute actions
        page.click("text=Submit")
        page.fill("#email", "test@example.com")

        # Assert results
        assert page.locator(".success-message").is_visible()

        browser.close()

if __name__ == "__main__":
    run_test()
```

## Selector Strategies

| Type | Example | Use When |
|------|---------|----------|
| Text | `text=Submit` | Button/link text is stable |
| Role | `role=button[name="Save"]` | Semantic HTML |
| CSS | `.btn-primary` | Class names are stable |
| ID | `#submit-btn` | IDs are stable |
| Test ID | `[data-testid="submit"]` | Test-specific attributes |

## Dependencies

```bash
pip install playwright
playwright install chromium
```

## Integration with Task 704

This skill augments E2E testing agents with:
- Server lifecycle management (`with_server.py`)
- Playwright patterns for browser automation
- DOM inspection techniques for selector discovery
