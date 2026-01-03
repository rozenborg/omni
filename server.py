#!/usr/bin/env python3

import asyncio
import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple

from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import BaseModel

# Define the 7 life domains
LIFE_DOMAINS = [
    "Health",
    "Home & Family",
    "People",
    "Work",
    "Wealth",
    "Hobbies",
    "Society"
]

# Create sessions directory if it doesn't exist
SESSIONS_DIR = Path(__file__).parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

# Initialize MCP server
server = Server("life-domains-tracker")

class SessionData(BaseModel):
    id: str
    timestamp: str
    domains_covered: List[str]
    summary: List[str]
    notes: str = ""

def git_sync_session(filepath: Path, session_id: str) -> Tuple[bool, str]:
    """Git add, commit, and push the session file"""
    try:
        # Change to the repository directory
        repo_dir = filepath.parent.parent

        # Git add the file
        result = subprocess.run(
            ["git", "add", str(filepath.relative_to(repo_dir))],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return False, f"Git add failed: {result.stderr}"

        # Git commit
        commit_msg = f"Log session: {session_id}"
        result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            # Check if it's just "nothing to commit" (already committed)
            if "nothing to commit" in result.stdout:
                return True, "Session already committed"
            return False, f"Git commit failed: {result.stderr}"

        # Git pull --rebase
        pull_warning = None
        result = subprocess.run(
            ["git", "pull", "--rebase"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            pull_warning = f"Git pull --rebase failed: {result.stderr.strip()}"

        # Git push
        result = subprocess.run(
            ["git", "push", "origin"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            error_msg = f"Git push failed: {result.stderr}"
            if pull_warning:
                error_msg += f" (Previous warning: {pull_warning})"
            return False, error_msg

        success_msg = "Session synced to git successfully"
        if pull_warning:
            success_msg += f" (Warning: {pull_warning})"
        return True, success_msg

    except subprocess.TimeoutExpired:
        return False, "Git operation timed out"
    except Exception as e:
        return False, f"Git sync error: {str(e)}"

def save_session(session_data: SessionData) -> Tuple[str, str]:
    """Save session data to JSON file and sync to git"""
    filename = f"{session_data.id}.json"
    filepath = SESSIONS_DIR / filename

    # Save the session file
    with open(filepath, 'w') as f:
        json.dump(session_data.model_dump(), f, indent=2)

    # Attempt git sync
    git_success, git_message = git_sync_session(filepath, session_data.id)

    return filepath.name, git_message

def load_sessions(days: int = 7) -> List[SessionData]:
    """Load sessions from the last N days"""
    cutoff_date = datetime.now() - timedelta(days=days)
    sessions = []

    for filepath in SESSIONS_DIR.glob("*.json"):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                session = SessionData(**data)
                session_time = datetime.fromisoformat(session.timestamp)
                if session_time >= cutoff_date:
                    sessions.append(session)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Error loading {filepath}: {e}")

    return sorted(sessions, key=lambda x: x.timestamp, reverse=True)

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools"""
    return [
        Tool(
            name="log_session",
            description="Log a life domain check-in session",
            inputSchema={
                "type": "object",
                "properties": {
                    "domains_covered": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": LIFE_DOMAINS
                        },
                        "description": f"List of domains covered from: {', '.join(LIFE_DOMAINS)}"
                    },
                    "summary": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key insights, decisions, or follow-ups as bullet points"
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional additional context",
                        "default": ""
                    }
                },
                "required": ["domains_covered", "summary"]
            }
        ),
        Tool(
            name="get_recent_sessions",
            description="Get recent session history",
            inputSchema={
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back",
                        "default": 7
                    }
                }
            }
        ),
        Tool(
            name="suggest_focus",
            description="Suggest which domains need attention based on recent activity",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_domain_history",
            description="Get history for a specific domain",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "enum": LIFE_DOMAINS,
                        "description": f"One of: {', '.join(LIFE_DOMAINS)}"
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days to look back",
                        "default": 30
                    }
                },
                "required": ["domain"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle tool calls"""

    if name == "log_session":
        # Create session ID and timestamp
        now = datetime.now()
        session_id = now.strftime("%Y-%m-%dT%H-%M")
        timestamp = now.isoformat()

        # Validate domains
        domains_covered = arguments.get("domains_covered", [])
        invalid_domains = [d for d in domains_covered if d not in LIFE_DOMAINS]
        if invalid_domains:
            return [TextContent(
                type="text",
                text=f"Error: Invalid domains: {', '.join(invalid_domains)}. Valid domains are: {', '.join(LIFE_DOMAINS)}"
            )]

        # Create session data
        session = SessionData(
            id=session_id,
            timestamp=timestamp,
            domains_covered=domains_covered,
            summary=arguments.get("summary", []),
            notes=arguments.get("notes", "")
        )

        # Save session
        filename, git_message = save_session(session)

        # Build response message
        response_text = f"✓ Session logged successfully\n\nSession ID: {session_id}\nDomains: {', '.join(domains_covered)}\nSaved to: sessions/{filename}\n\nGit sync: {git_message}"

        return [TextContent(
            type="text",
            text=response_text
        )]

    elif name == "get_recent_sessions":
        days = arguments.get("days", 7)
        sessions = load_sessions(days)

        if not sessions:
            return [TextContent(
                type="text",
                text=f"No sessions found in the last {days} days."
            )]

        result = f"Recent sessions (last {days} days):\n\n"
        for session in sessions:
            result += f"📅 {session.timestamp[:16]}\n"
            result += f"   Domains: {', '.join(session.domains_covered)}\n"
            if session.summary:
                result += "   Summary:\n"
                for point in session.summary[:2]:  # Show first 2 points
                    result += f"   • {point}\n"
                if len(session.summary) > 2:
                    result += f"   ... and {len(session.summary) - 2} more\n"
            result += "\n"

        return [TextContent(type="text", text=result)]

    elif name == "suggest_focus":
        # Look at last 14 days of sessions
        sessions = load_sessions(14)

        # Track last seen date for each domain
        domain_last_seen = {domain: None for domain in LIFE_DOMAINS}

        for session in sessions:
            session_date = datetime.fromisoformat(session.timestamp).date()
            for domain in session.domains_covered:
                if domain_last_seen[domain] is None:
                    domain_last_seen[domain] = session_date
                else:
                    domain_last_seen[domain] = max(domain_last_seen[domain], session_date)

        # Calculate days since last mention
        today = datetime.now().date()
        domain_days = []

        for domain, last_date in domain_last_seen.items():
            if last_date is None:
                days_since = 14  # Not seen in last 14 days
            else:
                days_since = (today - last_date).days
            domain_days.append((domain, days_since))

        # Sort by days since (most neglected first)
        domain_days.sort(key=lambda x: x[1], reverse=True)

        result = "📊 Domain Focus Suggestions (last 14 days):\n\n"

        # Categorize
        urgent = [d for d in domain_days if d[1] >= 7]
        moderate = [d for d in domain_days if 3 <= d[1] < 7]
        recent = [d for d in domain_days if d[1] < 3]

        if urgent:
            result += "🔴 Needs attention (7+ days):\n"
            for domain, days in urgent:
                if days >= 14:
                    result += f"   • {domain}: Not covered in last 14 days\n"
                else:
                    result += f"   • {domain}: {days} days ago\n"
            result += "\n"

        if moderate:
            result += "🟡 Consider reviewing (3-6 days):\n"
            for domain, days in moderate:
                result += f"   • {domain}: {days} days ago\n"
            result += "\n"

        if recent:
            result += "🟢 Recently covered (< 3 days):\n"
            for domain, days in recent:
                if days == 0:
                    result += f"   • {domain}: Today\n"
                elif days == 1:
                    result += f"   • {domain}: Yesterday\n"
                else:
                    result += f"   • {domain}: {days} days ago\n"

        return [TextContent(type="text", text=result)]

    elif name == "get_domain_history":
        domain = arguments.get("domain")
        days = arguments.get("days", 30)

        if domain not in LIFE_DOMAINS:
            return [TextContent(
                type="text",
                text=f"Error: Invalid domain '{domain}'. Valid domains are: {', '.join(LIFE_DOMAINS)}"
            )]

        sessions = load_sessions(days)
        domain_sessions = [s for s in sessions if domain in s.domains_covered]

        if not domain_sessions:
            return [TextContent(
                type="text",
                text=f"No sessions found for '{domain}' in the last {days} days."
            )]

        result = f"📚 History for '{domain}' (last {days} days):\n\n"
        result += f"Total sessions: {len(domain_sessions)}\n\n"

        for session in domain_sessions:
            result += f"📅 {session.timestamp[:16]}\n"
            result += f"   Other domains: {', '.join([d for d in session.domains_covered if d != domain]) or 'None'}\n"

            # Show relevant summary points
            if session.summary:
                result += "   Summary:\n"
                for point in session.summary:
                    result += f"   • {point}\n"

            if session.notes:
                result += f"   Notes: {session.notes[:100]}{'...' if len(session.notes) > 100 else ''}\n"

            result += "\n"

        return [TextContent(type="text", text=result)]

    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]

async def main():
    """Main entry point for the server"""
    # Run the server using stdio transport
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())