import json
import time
from pathlib import Path
from typing import Any

from loguru import logger
import cedarpy

class CedarError(Exception):
    """Raised when Cedar denies a tool call.

    Carries structured denial data so the caller
    can produce a useful feedback response for the LLM.

    Attributes:
        tool_name (str): The name of the tool that was denied.
        requestor (str): The identity of the caller (e.g., "assistant" or "user").
        reason (str): The reason for the denial.
        cedar_request (dict[str, Any], optional): The full Cedar authorization request dictionary. Defaults to None.
        cedar_policy_ids (list[str], optional): The Cedar policy IDs that triggered the denial. Defaults to None.
        cedar_eval_errors (list[str], optional): Any errors raised by the Cedar evaluation engine. Defaults to None.
    """
    def __init__(
        self, 
        tool_name: str, 
        requestor: str, 
        reason: str,
        cedar_request: dict[str, Any] | None = None,
        cedar_policy_ids: list[str] | None = None, 
        cedar_eval_errors: list[str] | None = None,
        cedar_overhead_ms: float | None = None,
    ) -> None:
        self.tool_name = tool_name
        self.requestor = requestor
        self.reason = reason
        self.cedar_request = cedar_request
        self.cedar_policy_ids = cedar_policy_ids            
        self.cedar_eval_errors = cedar_eval_errors 
        self.cedar_overhead_ms = cedar_overhead_ms
        super().__init__(reason)

class CedarAuthorizer:
    """Cedar authorization boundary for Tau2 environment tool calls.
    
    Intercepts tool calls, parses them into a standard schema,
    and runs them against a compiled Cedar policy file.
    
    Args:
        domain_name (str): The name of the target domain.
        policy_name (str, optional): The target Cedar policy file. Defaults to None.
        db (Any, optional): The target domain database. Defaults to None.
    
    Attributes:
        domain_name (str): The name of the target domain.
        target_policy (str): The target Cedar policy file.
        cedar_policies (str): The loaded Cedar policy string, or a deny-all fallback if missing.
        cedar_entities (list[dict[str, Any]]): The loaded Cedar entities, or an empty list if missing.
    """
    
    def __init__(
        self, 
        domain_name: str, 
        policy_name: str | None = None, 
        db: Any | None = None,
    ) -> None:
        self.domain_name = domain_name.strip().lower()
        self.db = db
        
        self.target_policy = policy_name or f"{self.domain_name}.cedar"
        self.cedar_policies = self._load_policies()

    def _load_policies(self) -> str:
        """Load Cedar policies based on the domain.
        
        Returns:
            str: The loaded Cedar policies as a string;
                defaults to a deny-all policy if the file is missing.
        """
        current_dir = Path(__file__).resolve().parent
        project_root = current_dir.parent.parent.parent
        policy_path = project_root / "cedar" / "policies" / self.domain_name / self.target_policy
        
        # Fallback to static deny-all policy if file is missing
        if not policy_path.exists():
            logger.warning(
                f"No matching Cedar policy file found at '{policy_path}'. "
                "Defaulting to deny-all policy."
            )
            return "forbid(principal, action, resource);"
        
        try:
            logger.info(f"Successfully located and loading Cedar policy from: {policy_path}")
            return policy_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Error reading policy file at '{policy_path}': {e}")
            
        return "forbid(principal, action, resource);"

    def generate_entities(
        self, 
        tool_name: str, 
        arguments: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generates the full list of Cedar entities for a tool call.
        
        Constructs base entities shared across all domains (such as Agent),
        then appends domain-specific entities.
        
        Args:
            tool_name (str): The name of the tool being executed.
            arguments (dict[str, Any]): The arguments passed to the tool.
            
        Returns:
            list[dict[str, Any]]: The complete entity slice for Cedar evaluation.
        """
        
        # Base generic entities
        entities: list[dict[str, Any]] = [
            {
                "uid": {"type": "Agent", "id": "assistant"},
                "attrs": {"cannot_handle": False},
                "parents": [],
            }
        ]
        
        # Add domain-specific entities (delegated to domain subclasses)
        domain_entities = self._generate_domain_entities(tool_name, arguments)
        entities.extend(domain_entities)
        
        return entities
    
    def _generate_domain_entities(
        self, 
        tool_name: str, 
        arguments: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Hook method for domain-specific entity extraction.
        
        Subclasses (e.g. AirlineCedarAuthorizer, RetailCedarAuthorizer) override
        this method to extract live entities from their specific databases.
        
        Args:
            tool_name (str): The name of the tool being executed.
            arguments (dict[str, Any]): The arguments passed to the tool.
            
        Returns:
            list[dict[str, Any]]: Domain-specific Cedar entity dictionaries.
        """
        
        return []
    
    def _determine_resource(
        self, 
        tool_name: str, 
        arguments: dict[str, Any],
    ) -> str:
        """Determines the Cedar Resource identifier for a tool call.

        Args:
            tool_name (str): The name of the tool being called.
            arguments (dict[str, Any]): The arguments passed to the tool.

        Returns:
            str: The formatted Cedar Resource ID string;
                defaults to a generic System::"EnvironmentState" resource if no ID is found.
        """
        # Default resources
        resource_type: str = "System"
        resource_id: str = "EnvironmentState"

        # Extract entity properties using trailing identity keys
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
        
    def _characterize_tool_call(
        self, 
        tool_name: str, 
        arguments: dict[str, Any], 
        requestor: str,
    ) -> dict[str, Any]:
        """Convert a tool call into a Cedar authorization request.

        Args:
            tool_name (str): The name of the tool being called.
            arguments (dict[str, Any]): The arguments passed to the tool.
            requestor (str): The identity of the caller (e.g., "assistant" or "user").

        Returns:
            dict[str, Any]: A structured request containing the principal, action, resource, and context.
        """
        # Map the requestor to its corresponding Cedar entity type definition
        if requestor.lower() in ("agent", "assistant") or requestor.lower().startswith("agent_"):
            principal = f'Agent::"{requestor}"'
        else:
            principal = f'User::"{requestor}"'
                
        action: str = f'Action::"{tool_name}"'

        # Sanitize parameters via absolute JSON serialization sequence
        try:
            safe_context: dict[str, Any] = json.loads(
                json.dumps(arguments or {}, default=str)
            )
        except Exception as e:
            logger.warning(
                f"Failed to sanitize context for Cedar: {e}. "
                "Defaulting to empty context."
            )
            safe_context = {}

        # Isolate resource mapping components using sanitized parameters
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
        arguments: dict[str, Any], 
        requestor: str,
    ) -> dict[str, Any]:
        """Evaluates the request against the active Cedar policy engine.

        Args:
            tool_name (str): The name of the tool being called.
            arguments (dict[str, Any]): The complete operational parameters tracking block.
            requestor (str): The identity of the caller (e.g., "assistant" or "user").

        Returns:
            dict[str, Any]: A dictionary containing cedar_request, cedar_policy_ids, and cedar_eval_errors.

        Raises:
            CedarError: If Cedar denies the request. 
                Contains the tool name, requestor and the feedback message.
        """
        cedar_request: dict[str, Any] = self._characterize_tool_call(tool_name, arguments, requestor)
        entities: list[dict[str, Any]] = self.generate_entities(tool_name, arguments)
        start_time: float = time.perf_counter()
        
        # Authorize request against Cedar policies and entities
        cedar_result = cedarpy.is_authorized(
            cedar_request,
            self.cedar_policies,
            entities,
        )
        
        cedar_overhead_ms: float = (time.perf_counter() - start_time) * 1000

        policy_ids = [str(r) for r in cedar_result.diagnostics.reasons]
        eval_errors = [str(e) for e in cedar_result.diagnostics.errors]

        # Raise exception containing feedback and denial context if denied
        if cedar_result.decision == cedarpy.Decision.Deny:
            raise CedarError(
                tool_name=tool_name,
                requestor=requestor,
                reason=(
                    f"The '{requestor}' is not authorized to use the '{tool_name}' tool. "
                    "This action is restricted by the active Cedar policy. "
                    "Do not retry this tool. Politely explain the restriction to the user."
                ),
                cedar_request=cedar_request,
                cedar_policy_ids=policy_ids,
                cedar_eval_errors=eval_errors,
                cedar_overhead_ms=cedar_overhead_ms,
            )
            
        return {
            "cedar_request": cedar_request,
            "cedar_policy_ids": policy_ids,
            "cedar_eval_errors": eval_errors,
            "cedar_overhead_ms": cedar_overhead_ms,
        }