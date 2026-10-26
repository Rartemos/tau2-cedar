# Author:       Andrew Yohanes (Advisor: Prof. William Eiers)
# Affiliation:  Pinnacle Scholars Program, Stevens Institute of Technology
# Description:  Cedar Authorization system for tau2-bench
# References:   https://github.com/k9securityio/cedar-py

import json
import time
from pathlib import Path
from typing import Any

from loguru import logger
import cedarpy

DEFAULT_POLICIES_DIR: Path = Path(__file__).resolve().parents[3] / "cedar" / "policies"
DEFAULT_SCHEMA_DIR: Path = Path(__file__).resolve().parents[3] / "cedar" / "schemas"


class CedarError(Exception):
    """Raised when Cedar denies a tool call.

    Creates structured denial and diagnostic data for blocked tool calls.

    Attributes:
        tool_name: The tool call that was denied.
        requestor: The requestor of the tool call.
        reason: The natural language feedback for the requestor.
        cedar_overhead_ms: Evaluation latency in milliseconds.
        cedar_request: The structured request evaluated by Cedar. 
        cedar_policy_ids: Policy IDs that denied the tool call. 
        cedar_eval_errors: Diagnostic errors from the Cedar engine.
    """
    
    def __init__(
        self, 
        tool_name: str, 
        requestor: str, 
        reason: str,
        cedar_overhead_ms: float | None = None,
        cedar_policy_ids: list[str] | None = None, 
        cedar_eval_errors: list[str] | None = None,
        cedar_request: dict[str, Any] | None = None,
    ) -> None:
        self.tool_name = tool_name
        self.requestor = requestor
        self.reason = reason
        self.cedar_overhead_ms = cedar_overhead_ms
        self.cedar_policy_ids = cedar_policy_ids            
        self.cedar_eval_errors = cedar_eval_errors 
        self.cedar_request = cedar_request
        super().__init__(reason)

class CedarAuthorizer:
    """Cedar authorization boundary for Tau2 environment tool calls.
    
    Intercepts tool calls, translates them into Cedar-compliant 
    authorization requests, and evaluates them against Cedar policies.
    
    Attributes:
        default_feedback_mode: The agent will receive structured feedback for Cedar denials.
        domain_name: The name of the domain.
        db: The target database for domain entity extraction.
        policy_path: The Cedar policy file path, if provided.
        schema_path: The Cedar schema file path, if provided.
        cedar_policies: The loaded Cedar policy string. Defaults to a forbid-all policy.
        cedar_schema: The loaded Cedar schema string, or None.
        feedback_mode: Whether structured feedback is sent to the agent when a tool call is denied.
    """
    
    default_feedback_mode: bool = False # If the agent receives structured feedback
    
    def __init__(
        self, 
        domain_name: str, 
        db: Any | None = None,
        policy_path: str | Path | None = None, 
        schema_path: str | Path | None = None,
        feedback_mode: bool | None = None,
    ) -> None:
        """Initialize the authorizer.
        
        Args:
            domain_name: The name of the domain.
            db: The target database for extracting entities.
            policy_path: The Cedar policy file path, or None.
            schema_path: The Cedar schema file path, or None.
            feedback_mode: Toggle structured Cedar feedback for agents. If None,
                defaults to ``CedarAuthorizer.default_feedback_mode``.
        """
        self.domain_name = domain_name.strip().lower()
        self.db = db
        
        default_policy: Path = DEFAULT_POLICIES_DIR / self.domain_name / f"{self.domain_name}.cedar"
        self.policy_path = Path(policy_path) if policy_path is not None else default_policy
        
        default_schema: Path = DEFAULT_SCHEMA_DIR / self.domain_name / f"{self.domain_name}.cedarschema"
        if schema_path is not None:
            self.schema_path = Path(schema_path)
        elif default_schema.exists():
            self.schema_path = default_schema
        else:
            self.schema_path = None
        
        self.cedar_policies: str = self._load_policies()
        self.cedar_schema: str | None = self._load_schema()
        
        self.feedback_mode: bool = self.default_feedback_mode if feedback_mode is None else feedback_mode

    def _load_policies(self) -> str:
        """Load the Cedar policy file.
        
        Returns:
            The raw Cedar policy string. Defaults to ``forbid(principal, action, resource);``
            if the policy file path is omitted, missing, or unreadable.
        """
        try:
            content: str = self.policy_path.read_text(encoding="utf-8")
            logger.info(f"Successfully located and loading Cedar policy from: {self.policy_path}")
            return content
        except FileNotFoundError:
            logger.warning(
                f"No Cedar policy file found at '{self.policy_path}'. "
                "Defaulting to forbid-all policy."
            )
        except Exception as e:
            logger.error(f"Error reading policy file at '{self.policy_path}': {e}")
            
        return "forbid(principal, action, resource);"
    
    def _load_schema(self) -> str | None:
        """Load the Cedar schema file if provided.
        
        Returns:
            The raw Cedar schema string, or None if omitted or missing.
        """
        if self.schema_path is None:
            return None
        
        try:
            content: str = self.schema_path.read_text(encoding="utf-8")
            json.loads(content)
            logger.info(f"Successfully loaded Cedar schema from: {self.schema_path}")
            return content
        except FileNotFoundError:
            logger.warning(
                f"Cedar schema file not found at '{self.schema_path}'. "
                "Proceeding with no schema file."
            )
            return None
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.debug(
                f"Cedar schema at '{self.schema_path}' is in .cedarschema format. "
                "cedarpy requires JSON-formatted schemas; proceeding without schema validation."
            )
            return None
        except Exception as e:
            logger.error(f"Error reading schema file at '{self.schema_path}': {e}")
            return None

    def build_entities(
        self, 
        tool_name: str, 
        arguments: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Builds a list of Cedar entities.
        
        Base implementation returns the framework Agent entity. Subclasses 
        should call ``super().build_entities(tool_name, arguments)`` and append 
        their own entity dictionaries.
        
        Args:
            tool_name: The name of the tool call.
            arguments: The raw tool parameters.
            
        Returns:
            A list of Cedar entity dictionaries for evaluation.
        """
        return [
            {
                "uid": {"type": "Agent", "id": "assistant"},
                "attrs": {"cannot_handle": False},
                "parents": [],
            }
        ]
    
    def _determine_resource(
        self, 
        tool_name: str, 
        arguments: dict[str, Any],
    ) -> str:
        """Determines the Cedar Resource identifier.
        
        Searches arguments for trailing identity keys. Falls back to 
        deriving a scope from the tool name suffix.

        Args:
            tool_name: The name of the tool call.
            arguments: The sanitized tool parameters.

        Returns:
            The formatted Cedar Resource ID string. Defaults to 'System::"EnvironmentState"'.
        """
        resource_type: str = "System"
        resource_id: str = "EnvironmentState"

        # Extract entities using trailing identity keys
        for key, value in arguments.items():
            if key.endswith("_id") and isinstance(value, str):
                resource_type = key.replace("_id", "").title().replace("_", "")
                resource_id = value
                break
        
        # If no ID is found, derive target scope from the function name suffix
        if resource_type == "System":
            parts = tool_name.split("_")
            if len(parts) > 1:
                resource_type = parts[-1].title()
                resource_id = "new_context"

        return f'{resource_type}::"{resource_id}"'
        
    @staticmethod    
    def _sanitize_context(arguments: dict[str, Any]) -> dict[str, Any]:
        """Converts raw parameter values into JSON-compatible Cedar context.
        
        Args:
            arguments: The raw tool parameters.
            
        Returns:
            A JSON-compatible dictionary representation of the arguments.
        """
        try:
            return json.loads(json.dumps(arguments or {}, default=str))
        except Exception as e:
            logger.warning(
                f"Failed to sanitize context for Cedar: {e}. Defaulting to empty context."
            )
            return {}
        
    def _characterize_tool_call(
        self, 
        tool_name: str, 
        requestor: str,
        arguments: dict[str, Any], 
    ) -> dict[str, Any]:
        """Convert a tool call into a Cedar authorization request.
        
        Maps principal, action, resource, and context.

        Args:
            tool_name: The name of the tool call.
            requestor: The requestor of the tool call.
            arguments: The raw tool parameters.

        Returns:
            Cedar request dictionary with ``principal``, ``action``, ``resource``, and ``context``.
        """
        # Map principal
        if requestor.lower() in ("agent", "assistant") or requestor.lower().startswith("agent_"):
            principal = f'Agent::"{requestor}"'
        else:
            principal = f'User::"{requestor}"'
        
        action: str = f'Action::"{tool_name}"'
        safe_context = self._sanitize_context(arguments)
        resource = self._determine_resource(tool_name, safe_context)
        
        return {
            "principal": principal,
            "action": action,
            "resource": resource,
            "context": safe_context,
        }

    def authorize_tool_call(
        self, 
        tool_name: str, 
        requestor: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Evaluate a tool call against the Cedar engine.
        
        Builds the authorization request and entities, 
        evaluates against Cedar, and returns a decision.

        Args:
            tool_name: The name of the tool call.
            requestor: The requestor of the tool call.
            arguments: The raw tool parameters.
            
        Returns:
            Evaluation metadata on a permitted tool call, containing ``cedar_overhead_ms``, 
            ``cedar_request``, ``cedar_policy_ids``, and ``cedar_eval_errors``.

        Raises:
            CedarError: If Cedar denies the request. 
        """
        start_time: float = time.perf_counter()
        cedar_request: dict[str, Any] = self._characterize_tool_call(tool_name, requestor, arguments)
        entities: list[dict[str, Any]] = self.build_entities(tool_name, arguments)
        
        # Authorize request against Cedar
        cedar_result = cedarpy.is_authorized(
            cedar_request,
            self.cedar_policies,
            entities,
            schema=self.cedar_schema,
        )
        

        # Retrieve diagnostic data
        policy_ids = [str(r) for r in cedar_result.diagnostics.reasons]
        eval_errors = [str(e) for e in cedar_result.diagnostics.errors]
        
        cedar_overhead_ms: float = (time.perf_counter() - start_time) * 1000 

        # Raise exception containing feedback and denial context if denied
        if cedar_result.decision == cedarpy.Decision.Deny:
            if self.feedback_mode:
                reason=(
                    f"The '{requestor}' is not authorized to use the '{tool_name}' tool. "
                    "This action is restricted by the active Cedar policy. Do not retry this tool. "
                    "Politely explain the restriction to the user."
                )
            else:
                reason=(f"Action denied. The '{tool_name}' tool was blocked.")
            
            raise CedarError(
                tool_name=tool_name,
                requestor=requestor,
                reason=reason,
                cedar_overhead_ms=cedar_overhead_ms,
                cedar_policy_ids=policy_ids,
                cedar_eval_errors=eval_errors,
                cedar_request=cedar_request,
            )
            
        return {
            "cedar_overhead_ms": cedar_overhead_ms,
            "cedar_policy_ids": policy_ids,
            "cedar_eval_errors": eval_errors,
            "cedar_request": cedar_request,
        }
        