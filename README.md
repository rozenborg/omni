# Life Domains Tracker MCP Server

An MCP (Model Context Protocol) server for tracking check-ins across 7 life domains: Health, Home & Family, People, Work, Wealth, Hobbies, and Society.

## Features

This MCP server provides tools to:
- **Log sessions**: Track which life domains were discussed and key takeaways
- **View history**: Review recent sessions and their summaries
- **Get suggestions**: Identify which domains haven't been covered recently
- **Domain analysis**: View all sessions related to a specific domain
- **Auto-sync**: Automatically commits and pushes new sessions to git

## Requirements

- Python 3.10 or higher (required by MCP SDK)

## Installation

1. Create a virtual environment with Python 3.10+:
```bash
python3.11 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make the server executable (macOS/Linux):
```bash
chmod +x server.py
```

## Configuration for Claude Desktop

Add the following to your Claude Desktop configuration file:

### macOS
Location: `~/Library/Application Support/Claude/claude_desktop_config.json`

### Windows
Location: `%APPDATA%\Claude\claude_desktop_config.json`

### Configuration to add:

```json
{
  "mcpServers": {
    "life-domains": {
      "command": "python",
      "args": ["/path/to/your/omni/server.py"],
      "env": {}
    }
  }
}
```

**Important**: Replace `/path/to/your/omni/server.py` with the actual full path to your server.py file.

For this specific installation, use:
```json
{
  "mcpServers": {
    "life-domains": {
      "command": "python",
      "args": ["/Users/michaelrosenberg/Code/omni/server.py"],
      "env": {}
    }
  }
}
```

After updating the configuration, restart Claude Desktop for the changes to take effect.

## Available Tools

### 1. log_session
Logs a check-in session with domains covered and key takeaways.

**Parameters:**
- `domains_covered`: List of domains from the 7 life domains
- `summary`: List of bullet points with key insights/decisions
- `notes`: (Optional) Additional context

**Example:**
```
domains_covered: ["Health", "Work"]
summary: ["Started new exercise routine", "Completed project milestone"]
notes: "Feeling productive this week"
```

### 2. get_recent_sessions
Retrieves session history for a specified number of days.

**Parameters:**
- `days`: (Optional, default 7) Number of days to look back

### 3. suggest_focus
Analyzes the last 14 days and suggests which domains need attention.

**No parameters required**

Returns domains categorized by urgency:
- 🔴 Needs attention (7+ days)
- 🟡 Consider reviewing (3-6 days)
- 🟢 Recently covered (< 3 days)

### 4. get_domain_history
Gets all sessions that included a specific domain.

**Parameters:**
- `domain`: One of the 7 life domains
- `days`: (Optional, default 30) Number of days to look back

## The 7 Life Domains

1. **Health**: Physical and mental wellbeing, exercise, nutrition, sleep
2. **Home & Family**: Relationships with family, home environment, household matters
3. **People**: Friendships, social connections, networking, community
4. **Work**: Career, professional development, job satisfaction, projects
5. **Wealth**: Financial planning, investments, budgeting, economic goals
6. **Hobbies**: Personal interests, recreation, creative pursuits, learning
7. **Society**: Civic engagement, contributions to community, global awareness

## Data Storage

Sessions are stored as JSON files in the `sessions/` directory with timestamps as filenames (e.g., `2026-01-02T17-05.json`).

### Git Integration

When a new session is logged, the server automatically:
1. Saves the session JSON file
2. Runs `git add` on the new file
3. Creates a commit with message "Log session: {session_id}"
4. Pushes to the origin remote

If any git operation fails, the session is still saved successfully, but the failure is reported in the response. This ensures your data is never lost due to git issues.

## Session Structure

Each session is saved with the following structure:
```json
{
  "id": "2026-01-02T17-05",
  "timestamp": "2026-01-02T17:05:00",
  "domains_covered": ["Health", "Wealth"],
  "summary": [
    "Discussed 8-week Apple Watch experiment",
    "Reviewed monthly investment ritual"
  ],
  "notes": "Optional additional context"
}
```

## Usage Tips

1. **Regular Check-ins**: Use `log_session` after conversations to track which life areas you're discussing
2. **Weekly Reviews**: Use `get_recent_sessions` to review your week
3. **Balance Check**: Use `suggest_focus` to identify neglected areas
4. **Deep Dives**: Use `get_domain_history` to analyze patterns in specific life domains

## Troubleshooting

If the server doesn't appear in Claude:
1. Ensure the configuration path is correct and absolute
2. Check that Python is accessible from your PATH
3. Restart Claude Desktop after configuration changes
4. Verify the server runs without errors: `python server.py`