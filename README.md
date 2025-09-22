# GitHub Research MCP and Agents.md Generator

A Model Context Protocol (MCP) server for researching GitHub repositories, issues, and pull requests with sampling-powered analysis and summarization capabilities.

## Agents.md Generator

The Agents.md Generator is a free & public MCP Server that generates AGENTS.md files for public GitHub repositories that have at least 10 stars. The Agents.md generator is powered by the GitHub Research MCP and leverages the repo summarization tool to generate the AGENTS.md file.

Try it out!

| IDE | Command | 
| --- | --- |
| Cursor | [Add it to Cursor](cursor://anysphere.cursor-deeplink/mcp/install?name=agents-md-generator&config=eyJ1cmwiOiJodHRwczovL2FnZW50cy1tZC1nZW5lcmF0b3IuZmFzdG1jcC5hcHAvbWNwIn0%3D) |
| Gemini CLI | `gemini mcp add agents-md-generator https://agents-md-generator.fastmcp.app/mcp --transport http` |
| Claude Desktop | [Download manifest](https://agents-md-generator.fastmcp.app/manifest.dxt?v=7b0947b4-15b1-48f2-90bc-f6352cf125f2) |
| Claude Code | `claude mcp add --scope local --transport http agents-md-generator https://agents-md-generator.fastmcp.app/mcp`

## Features

### Repository Analysis
- **File Discovery**: Browse repository structure and find files by patterns
- **Code Search**: Search for code across repositories with advanced filtering
- **File Analysis**: Get file contents, README files, and file extension statistics
- **Repository Summarization**: AI-powered analysis of entire repositories

### Issue & Pull Request Research
- **Detailed Research**: Get comprehensive information about specific issues and pull requests
- **Advanced Search**: Search issues/PRs by keywords, labels, authors, and more
- **Timeline Analysis**: Track related issues, PRs, and cross-references
- **Comment Analysis**: Review all comments and discussion threads

### AI-Powered Analysis
- **Intelligent Summarization**: Generate focused summaries using Google Gemini by default (OpenAI optional)
- **Context-Aware Research**: AI-driven analysis of complex GitHub data
- **Flexible Prompting**: Customizable prompts for different analysis needs
- **Structured Data Extraction**: Convert unstructured GitHub data into structured formats

### Technical Features
- **GraphQL Integration**: Efficient data fetching using GitHub's GraphQL API
- **REST API Support**: Fallback to REST API for broader compatibility
- **Rate Limiting**: Built-in rate limiting and request management
- **Flexible Configuration**: Support for both stdio and HTTP transports
- **Public Repository Support**: Specialized tools for public repository analysis

## Self Hosting GitHub Research MCP

To run the server as a stdio MCP Server, use the following command:
```bash
uvx github-research-mcp
```

To run the server as a HTTP MCP Server, use the following command:
```bash
uvx github-research-mcp --mcp-transport streamable-http
```

Note: To disable AI-powered analysis, set `DISABLE_SAMPLING=true`.

### Environment Variables

**Required:**
- `GITHUB_TOKEN` or `GITHUB_PERSONAL_ACCESS_TOKEN`: Required for GitHub API access

**Sampling Fallback:**
For clients that dont support sampling, you can provide an API key for either Google or OpenAI to enable sampling fallback -- where the server performs an AI call to generate the response instead of relying on the client's sampling capabilities.

- Google AI (default):
  - `GOOGLE_API_KEY`: Required to enable summarization and research tools
  - `GOOGLE_MODEL`: Gemini model to use (default: `gemini-2.5-flash`)
- OpenAI (optional alternative):
  - `OPENAI_API_KEY`: If using OpenAI with a compatible sampling handler
  - `OPENAI_MODEL`: OpenAI model (e.g., `gpt-4o`) if using OpenAI
  - `OPENAI_BASE_URL`: Custom OpenAI API base URL (optional)
- Control:
  - `DISABLE_SAMPLING`: Set to `true` to disable AI summarization/research tools

**Public Repository Features:**
- `MINIMUM_STARS`: Minimum star count for repository summarization (default: 10)
- `OWNER_ALLOWLIST`: Comma-separated list of owners to allow regardless of star count

### Available Tools

The server provides multiple tool categories:

**Repository Tools** (always available):
- `get_files`: Browse repository file structure
- `find_files`: Search for files by patterns
- `search_files`: Advanced file search with filtering
- `get_readmes`: Retrieve README files
- `get_file_extensions`: Analyze file type distribution

**Issue & Pull Request Tools** (always available):
- `get_issue_or_pull_request`: Get detailed information about specific issues/PRs
- `search_issues_or_pull_requests`: Search issues/PRs with advanced filtering

**Sampling-Powered Tools** (requires Sampling or Sampling Fallback configuration):
- `summarize`: Generate AI-powered repository summaries
- `research_issue_or_pull_request`: AI-driven analysis of issues/PRs

## MCP Client Configuration

### VS Code

1. Open the command palette (Ctrl+Shift+P or Cmd+Shift+P).
2. Type "Settings" and select "Preferences: Open User Settings (JSON)".
3. Add the following MCP Server configuration:

```json
{
  "mcp": {
    "servers": {
      "GitHub Research MCP": {
        "command": "uvx",
        "args": [
          "github-research-mcp",
        ],
        "env": {
          "GITHUB_TOKEN": "your_github_token_here",
        }
      }
    }
  }
}
```

### Cline / Roo Code

Add the following to your MCP Server configuration:

```json
{
  "GitHub Research MCP": {
    "command": "uvx",
    "args": [
      "github-research-mcp",
    ],
    "env": {
      "GITHUB_TOKEN": "your_github_token_here",
    }
  }
}
```

## License

See [LICENSE](LICENSE).