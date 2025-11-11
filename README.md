# ALM Traceability MCP Server

PostgreSQL-based Model Context Protocol (MCP) server for ALM traceability management across Azure DevOps, Jira, and vector search.

## Features

- ✅ **Azure DevOps Integration** - User stories, test cases, work items
- ✅ **Jira Integration** - Issues, test cases, custom fields
- ✅ **PostgreSQL Traceability** - Persistent traceability matrix
- ✅ **Vector Search** - Similarity search with Google Cloud Vertex AI
- ✅ **Batch Operations** - Create multiple test cases efficiently
- ✅ **MCP Protocol** - Full Claude Desktop integration

## Installation

### Option 1: Direct Python Installation

```bash
# Clone repository
git clone https://github.com/Vk171127/mcp-server-for-alm-tools.git
cd mcp-server-for-alm-tools

# Install
pip install -e .

# With vector search support
pip install -e ".[vector]"
```

### Option 2: Using NPX (Recommended for MCP)

```bash
# Install globally
npm install -g @yourorg/alm-traceability-mcp

# Or use directly with npx
npx @yourorg/alm-traceability-mcp
```

## Configuration

### 1. Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Azure DevOps
ADO_ORG=your-organization
ADO_PROJECT=your-project
ADO_PAT=your-pat-token

# Jira
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token
JIRA_PROJECT_KEY=PROJECT

# PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=alm_traceability
DB_USER=postgres
DB_PASSWORD=your-password
```

### 2. Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "alm-traceability": {
      "command": "python",
      "args": ["-m", "mcp_main"],
      "env": {
        "ADO_ORG": "your-org",
        "ADO_PROJECT": "your-project",
        "ADO_PAT": "your-pat",
        "DB_HOST": "localhost",
        "DB_NAME": "alm_traceability",
        "DB_USER": "postgres",
        "DB_PASSWORD": "your-password"
      }
    }
  }
}
```

### 3. Database Setup

```sql
-- Create database
CREATE DATABASE alm_traceability;

-- Run schema (see schema.sql)
\i schema.sql
```

## Usage

### Starting the Server

```bash
# Activate virtual environment
source venv/bin/activate

# Run server
python -m mcp_main
```

### Available MCP Tools

#### Configuration Tools
- `configure_ado_connection` - Set up Azure DevOps
- `configure_jira_connection` - Set up Jira
- `initialize_traceability_database` - Initialize PostgreSQL

#### Azure DevOps Tools
- `fetch_user_story` - Get user story details
- `fetch_testcases` - Get linked test cases
- `create_testcase` - Create new test case
- `batch_create_testcases` - Create multiple test cases
- `prepare_test_case_context` - Prepare context for generation

#### Jira Tools
- `fetch_jira_issue` - Get Jira issue details
- `fetch_jira_testcases` - Get linked test cases
- `create_jira_testcase` - Create new test case
- `batch_create_jira_testcases` - Create multiple test cases
- `prepare_jira_test_case_context` - Prepare context for generation

#### Traceability Tools
- `create_traceability_link` - Link items
- `get_traceability_links_for_item` - Get all links
- `generate_traceability_report` - Generate reports
- `get_traceability_matrix_for_session` - Get full matrix

#### Vector Search Tools
- `search_similar_stories` - Find similar user stories
- `configure_vertex_ai` - Set up vector search

## Example Usage with Claude

```
User: "Configure Azure DevOps for my organization 'contoso' and project 'HealthApp'"

Claude: [calls configure_ado_connection]

User: "Fetch user story 12345 and prepare context for test generation"

Claude: [calls prepare_test_case_context with user_story_id=12345]

User: "Generate 5 test cases covering positive, negative, and edge cases"

Claude: [calls batch_create_testcases with generated test cases]
```

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black .
isort .

# Lint
flake8
```

## Architecture

```
┌─────────────────┐
│  Claude Desktop │
└────────┬────────┘
         │ MCP Protocol
         ▼
┌─────────────────┐
│   MCP Server    │
│   (Python)      │
└────────┬────────┘
         │
    ┌────┴────┬────────┬─────────┐
    ▼         ▼        ▼         ▼
┌───────┐ ┌──────┐ ┌──────┐ ┌──────────┐
│  ADO  │ │ Jira │ │ DB   │ │ Vector   │
│Client │ │Client│ │(PG)  │ │ Search   │
└───────┘ └──────┘ └──────┘ └──────────┘
```

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure PostgreSQL is running
   - Check connection string in .env

2. **Authentication Errors**
   - Verify PAT/API tokens are valid
   - Check token permissions

3. **Import Errors**
   - Ensure all dependencies installed: `pip install -e ".[vector]"`
   - Activate virtual environment

### Logs

Check logs at: `~/.mcp/logs/alm-traceability.log`

## License

MIT

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Run tests
5. Submit pull request

## Support

- GitHub Issues: https://github.com/Vk171127/mcp-server-for-alm-tools/issues
- Documentation: See `/docs` folder