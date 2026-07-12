"""Permissioned local tools for Nexus."""

from .audit import AuditEntry, ToolAuditLog
from .agent import ToolCallingAgent
from .calling import PendingToolCall, ToolAgentRun, ToolCallingModel, ToolRunStatus
from .commands import EvidenceCommandTool, RunCommandTool
from .development_files import ReplaceTextTool, RestoreSnapshotTool, SearchTextTool, WriteTextTool
from .filesystem import InspectProjectTool, ListDirectoryTool, ReadTextFileTool
from .factory import create_development_tool_registry, create_project_tool_registry
from .models import (
    RiskLevel,
    Tool,
    ToolDescriptor,
    ToolError,
    ToolPermissionError,
    ToolRequest,
    ToolResult,
    ToolValidationError,
)
from .permissions import PermissionDecision, PermissionPolicy
from .registry import ToolRegistry
from .gmail_factory import create_gmail_registry
from .gmail_models import AttachmentMetadata, GmailDraft, GmailMessage, GmailProvider, GmailThread
from .gmail_tools import (
    ArchiveTool, AttachmentMetadataTool, CreateDraftTool, DeleteTool, LabelTool,
    ReadMessageTool, ReplyTool, SearchMessagesTool, SendDraftTool, ThreadSummaryTool,
    UpdateDraftTool,
)
from .web_models import PageProvider, SearchProvider, SourceType, WebPage, WebSource
from .web_factory import create_web_research_registry
from .web_tools import CompareSourcesTool, OpenPageTool, SaveResearchNoteTool, WebSearchTool

__all__ = [
    "AuditEntry", "InspectProjectTool", "ListDirectoryTool", "PendingToolCall",
    "PermissionPolicy", "ReadTextFileTool", "RiskLevel", "Tool", "ToolAuditLog",
    "ToolAgentRun", "ToolCallingAgent", "ToolCallingModel", "ToolDescriptor", "ToolError",
    "ToolPermissionError", "ToolRegistry", "ToolRequest", "ToolResult", "ToolRunStatus",
    "ToolValidationError",
    "EvidenceCommandTool", "ReplaceTextTool", "RestoreSnapshotTool", "RunCommandTool",
    "SearchTextTool", "WriteTextTool", "create_development_tool_registry", "create_project_tool_registry",
    "CompareSourcesTool", "OpenPageTool", "PageProvider", "SaveResearchNoteTool",
    "SearchProvider", "SourceType", "WebPage", "WebSearchTool", "WebSource",
    "create_web_research_registry",
    "ArchiveTool", "AttachmentMetadataTool", "AttachmentMetadata", "CreateDraftTool",
    "DeleteTool", "GmailDraft", "GmailMessage", "GmailProvider", "GmailThread",
    "LabelTool", "ReadMessageTool", "ReplyTool", "SearchMessagesTool", "SendDraftTool",
    "ThreadSummaryTool", "UpdateDraftTool", "create_gmail_registry",
]
