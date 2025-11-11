from pydantic import BaseModel
from typing import Literal, Optional

class ADOConfig(BaseModel):
    organization: str
    project: str
    personal_access_token: str
    base_url: str = "https://dev.azure.com"

class JiraConfig(BaseModel):
    base_url: str  # e.g., "https://yourcompany.atlassian.net"
    email: str
    api_token: str
    project_key: str  # e.g., "HEALTH"

class DatabaseConfig(BaseModel):
    """PostgreSQL/CloudSQL database configuration for traceability"""
    host: str
    port: int = 5432
    database: str
    user: str
    password: str
    ssl_mode: str = "require"
    
    # Connection pool settings
    min_connections: int = 5
    max_connections: int = 20
    command_timeout: int = 60
    
    # CloudSQL specific settings
    use_cloud_sql_proxy: bool = False
    cloud_sql_instance: Optional[str] = None  # Format: project:region:instance

class MCPConfig(BaseModel):
    alm_type: Literal["azure_devops", "jira"]
    ado_config: ADOConfig | None = None
    jira_config: JiraConfig | None = None
    database_config: DatabaseConfig | None = None
    
    # Traceability settings
    enable_traceability: bool = True
    auto_create_links: bool = False
