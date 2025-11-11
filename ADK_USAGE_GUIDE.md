# ALM Traceability MCP Package for ADK Agents

A comprehensive MCP (Model Context Protocol) package for ALM (Application Lifecycle Management) operations, designed for seamless integration with ADK agents.

## Features

- **Azure DevOps Integration**: Full CRUD operations for user stories, test cases, and work items
- **Jira Integration**: Complete Jira API support for issues, stories, and test management
- **Vector Search**: AI-powered similarity search using Google Cloud Vertex AI
- **Traceability Management**: PostgreSQL-based traceability matrix between requirements and test cases
- **20+ MCP Tools**: Comprehensive toolset for ALM operations

## Installation

```bash
pip install dist/alm_traceability_mcp-1.0.0-py3-none-any.whl
```

Or install from source:

```bash
pip install dist/alm_traceability_mcp-1.0.0.tar.gz
```

## Quick Start for ADK Agents

### Basic Usage

```python
import asyncio
from alm_traceability_mcp import ALMClient

async def main():
    # Create and initialize the client
    client = ALMClient()
    await client.initialize()

    # Configure Azure DevOps
    ado_result = await client.configure_ado(
        organization="your-org",
        project="your-project",
        pat="your-personal-access-token"
    )
    print("ADO Configuration:", ado_result)

    # Fetch a user story
    story = await client.fetch_user_story(12345)
    print("User Story:", story)

    # Create test cases
    test_case = await client.create_test_case(
        story_id=12345,
        title="Test user login functionality",
        description="Verify user can login with valid credentials"
    )
    print("Created Test Case:", test_case)

# Run the async function
asyncio.run(main())
```

### Advanced Usage - Batch Operations

```python
import asyncio
from alm_traceability_mcp import ALMClient

async def generate_comprehensive_tests():
    client = ALMClient()
    await client.initialize()

    # Prepare test context with AI similarity search
    context = await client.prepare_test_context(
        story_id=12345,
        search_similar=True
    )

    # Batch create multiple test cases
    test_cases = [
        {
            "title": "Test positive login flow",
            "description": "User enters valid credentials",
            "steps": [
                {"action": "Enter username", "expected": "Username accepted"},
                {"action": "Enter password", "expected": "Password accepted"},
                {"action": "Click login", "expected": "User logged in"}
            ]
        },
        {
            "title": "Test invalid login flow",
            "description": "User enters invalid credentials",
            "steps": [
                {"action": "Enter invalid username", "expected": "Error message shown"},
                {"action": "Try login", "expected": "Login rejected"}
            ]
        }
    ]

    batch_result = await client.batch_create_test_cases(
        story_id=12345,
        test_cases=test_cases
    )
    print("Batch Creation Result:", batch_result)

asyncio.run(generate_comprehensive_tests())
```

### Jira Integration

```python
import asyncio
from alm_traceability_mcp import ALMClient

async def jira_example():
    client = ALMClient()
    await client.initialize()

    # Configure Jira
    await client.configure_jira(
        base_url="https://your-domain.atlassian.net",
        email="your-email@company.com",
        api_token="your-api-token",
        project_key="PROJ"
    )

    # Fetch Jira issue
    issue = await client.fetch_jira_issue("PROJ-123")

    # Create test case linked to the issue
    test_case = await client.create_jira_test_case(
        story_key="PROJ-123",
        title="Test API endpoint",
        description="Verify API returns correct response"
    )

asyncio.run(jira_example())
```

## Available Tools

The package exposes 20+ MCP tools through the client interface:

### Configuration Tools

- `configure_ado`: Configure Azure DevOps connection
- `configure_jira`: Configure Jira connection
- `configure_vertex_ai`: Configure Google Cloud AI for vector search

### Azure DevOps Tools

- `fetch_user_story`: Get user story details
- `create_test_case`: Create new test case
- `batch_create_test_cases`: Create multiple test cases
- `prepare_test_context`: Prepare comprehensive context for test generation
- `fetch_testcases`: Get existing test cases for a story

### Jira Tools

- `fetch_jira_issue`: Get Jira issue/story details
- `create_jira_test_case`: Create Jira test case
- `batch_create_jira_testcases`: Create multiple Jira test cases

### Vector Search Tools

- `search_similar_stories`: AI-powered similarity search
- Vector storage and retrieval for context-aware test generation

### Traceability Tools

- `get_traceability_matrix`: Get requirement-test traceability
- `get_test_cases_for_story`: Get tests linked to requirements
- `system_status`: Check system health and configuration

### Direct Tool Access

You can also call any tool directly:

```python
# Call any tool by name
result = await client.call_tool("system_status")

# Get list of all available tools
tools = client.list_tools()
print("Available tools:", tools)

# Get detailed info about a specific tool
tool_info = client.get_tool_info("prepare_test_case_context")
print("Tool info:", tool_info)
```

## Integration with ADK Workflows

### Test Case Generation Workflow

```python
async def adk_test_generation_workflow(story_id: int):
    client = ALMClient()
    await client.initialize()

    # Step 1: Prepare comprehensive context
    context = await client.prepare_test_context(story_id, search_similar=True)

    if not context.get("success"):
        return {"error": "Failed to prepare context"}

    # Step 2: Use context to generate test cases (your ADK logic here)
    # The context includes:
    # - User story details
    # - Existing test cases
    # - Similar stories from vector search
    # - Test generation suggestions

    # Step 3: Create test cases in batch
    generated_tests = your_adk_test_generation_logic(context)

    result = await client.batch_create_test_cases(
        story_id=story_id,
        test_cases=generated_tests
    )

    return result
```

### Traceability Analysis

```python
async def analyze_coverage(project_requirements):
    client = ALMClient()
    await client.initialize()

    coverage_analysis = {}

    for req_id in project_requirements:
        # Get test coverage for each requirement
        tests = await client.get_test_cases_for_story(req_id)
        coverage_analysis[req_id] = {
            "requirement_id": req_id,
            "test_count": len(tests.get("test_cases", [])),
            "has_coverage": len(tests.get("test_cases", [])) > 0
        }

    return coverage_analysis
```

## Error Handling

All methods return dictionaries with `success` boolean and error details:

```python
result = await client.fetch_user_story(999999)
if not result.get("success"):
    print("Error:", result.get("error"))
    print("Details:", result.get("message"))
```

## Logging

Enable logging to see detailed operation logs:

```python
import logging
logging.basicConfig(level=logging.INFO)

# Now all MCP operations will be logged
```

## Requirements

- Python 3.8+
- MCP library
- aiohttp for HTTP operations
- pydantic for data validation
- PostgreSQL for traceability (optional)
- Google Cloud credentials for vector search (optional)

## Support

This package wraps the comprehensive MCP tools from `mcp_tools.py` and `mcp_traceability_tools.py`, providing over 20 specialized tools for ALM operations.
