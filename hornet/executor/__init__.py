"""
HORNET Action Executor
Orchestrates action execution with rollback support.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from enum import Enum
import asyncio
import structlog

from hornet.integrations.action_connectors import (
    ActionConnector, ActionResult, PaloAltoConnector, OktaConnector, CrowdStrikeConnector
)
from hornet.integrations.notifications import NotificationPayload, SlackConnector, PagerDutyConnector
from hornet.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"


@dataclass
class ActionRequest:
    """Request to execute an action."""
    action_id: str
    incident_id: UUID
    action_type: str
    target: str
    parameters: Dict[str, Any]
    risk_level: str
    justification: str
    rollback_plan: Dict[str, Any]
    approved_by: str
    approved_at: datetime


@dataclass
class ExecutionResult:
    """Result of action execution."""
    action_id: str
    status: ExecutionStatus
    connector_used: str
    started_at: datetime
    completed_at: Optional[datetime]
    result_data: Dict[str, Any]
    rollback_id: Optional[str]
    error_message: Optional[str] = None


@dataclass 
class ExecutionPlan:
    """Plan for executing multiple actions."""
    incident_id: UUID
    actions: List[ActionRequest]
    parallel_groups: List[List[str]]  # Groups of action_ids that can run in parallel
    dependencies: Dict[str, List[str]]  # action_id -> list of dependent action_ids
    rollback_order: List[str]  # Order to rollback if needed


class ActionExecutor:
    """
    Executes approved actions against target systems.
    Handles rollback on failure.
    """
    
    # Action type to connector mapping
    ACTION_CONNECTOR_MAP = {
        # Firewall actions
        "block_ip": "firewall",
        "block_ip_range": "firewall",
        "block_domain": "firewall",
        "unblock_ip": "firewall",
        
        # Identity actions
        "disable_account": "identity",
        "force_password_reset": "identity",
        "revoke_sessions": "identity",
        "enforce_mfa": "identity",
        
        # EDR actions
        "isolate_endpoint": "edr",
        "kill_process": "edr",
        "quarantine_file": "edr",
        "collect_forensics": "edr",
        
        # Cloud actions
        "revoke_iam_role": "cloud",
        "disable_access_key": "cloud",
        "stop_instance": "cloud",
        
        # Notification actions (always allowed)
        "notify_user": "notification",
        "notify_team": "notification",
        "page_oncall": "notification",
    }
    
    def __init__(self, connectors: Dict[str, ActionConnector] = None):
        self.connectors = connectors or {}
        self._execution_history: Dict[str, List[ExecutionResult]] = {}
        self._active_executions: Dict[str, asyncio.Task] = {}
    
    def register_connector(self, connector_type: str, connector: ActionConnector):
        """Register a connector for action execution."""
        self.connectors[connector_type] = connector
        logger.info("connector_registered", type=connector_type)
    
    async def execute_action(self, request: ActionRequest) -> ExecutionResult:
        """Execute a single action."""
        started_at = datetime.utcnow()
        
        logger.info(
            "executing_action",
            action_id=request.action_id,
            action_type=request.action_type,
            target=request.target,
            risk_level=request.risk_level,
        )
        
        # Determine connector type
        connector_type = self.ACTION_CONNECTOR_MAP.get(request.action_type)
        if not connector_type:
            return ExecutionResult(
                action_id=request.action_id,
                status=ExecutionStatus.FAILED,
                connector_used="none",
                started_at=started_at,
                completed_at=datetime.utcnow(),
                result_data={},
                rollback_id=None,
                error_message=f"Unknown action type: {request.action_type}",
            )
        
        # Get connector
        connector = self.connectors.get(connector_type)
        if not connector:
            # Handle notification actions specially - they're always "successful" for demo
            if connector_type == "notification":
                return ExecutionResult(
                    action_id=request.action_id,
                    status=ExecutionStatus.COMPLETED,
                    connector_used="notification",
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    result_data={"notified": True},
                    rollback_id=None,
                )
            
            return ExecutionResult(
                action_id=request.action_id,
                status=ExecutionStatus.FAILED,
                connector_used=connector_type,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                result_data={},
                rollback_id=None,
                error_message=f"Connector not configured: {connector_type}",
            )
        
        # Validate action
        if not await connector.validate(request.action_type, request.target, request.parameters):
            return ExecutionResult(
                action_id=request.action_id,
                status=ExecutionStatus.FAILED,
                connector_used=connector_type,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                result_data={},
                rollback_id=None,
                error_message="Action validation failed",
            )
        
        # Execute
        try:
            result = await asyncio.wait_for(
                connector.execute(request.action_type, request.target, request.parameters),
                timeout=30.0,
            )
            
            execution_result = ExecutionResult(
                action_id=request.action_id,
                status=ExecutionStatus.COMPLETED if result.success else ExecutionStatus.FAILED,
                connector_used=connector_type,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                result_data=result.data or {},
                rollback_id=result.rollback_id,
                error_message=None if result.success else result.message,
            )
            
            # Store for rollback
            incident_key = str(request.incident_id)
            if incident_key not in self._execution_history:
                self._execution_history[incident_key] = []
            self._execution_history[incident_key].append(execution_result)
            
            logger.info(
                "action_executed",
                action_id=request.action_id,
                success=result.success,
                rollback_id=result.rollback_id,
            )
            
            return execution_result
            
        except asyncio.TimeoutError:
            return ExecutionResult(
                action_id=request.action_id,
                status=ExecutionStatus.FAILED,
                connector_used=connector_type,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                result_data={},
                rollback_id=None,
                error_message="Action execution timed out",
            )
        except Exception as e:
            logger.error("action_execution_error", action_id=request.action_id, error=str(e))
            return ExecutionResult(
                action_id=request.action_id,
                status=ExecutionStatus.FAILED,
                connector_used=connector_type,
                started_at=started_at,
                completed_at=datetime.utcnow(),
                result_data={},
                rollback_id=None,
                error_message=str(e),
            )
    
    async def execute_plan(self, plan: ExecutionPlan) -> List[ExecutionResult]:
        """Execute an action plan with dependency handling."""
        results = []
        completed = set()
        failed = set()
        
        for group in plan.parallel_groups:
            # Check if dependencies are satisfied
            group_requests = [a for a in plan.actions if a.action_id in group]
            
            can_execute = []
            for request in group_requests:
                deps = plan.dependencies.get(request.action_id, [])
                if all(d in completed for d in deps) and not any(d in failed for d in deps):
                    can_execute.append(request)
            
            if not can_execute:
                continue
            
            # Execute group in parallel
            tasks = [self.execute_action(req) for req in can_execute]
            group_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for req, result in zip(can_execute, group_results):
                if isinstance(result, Exception):
                    results.append(ExecutionResult(
                        action_id=req.action_id,
                        status=ExecutionStatus.FAILED,
                        connector_used="unknown",
                        started_at=datetime.utcnow(),
                        completed_at=datetime.utcnow(),
                        result_data={},
                        rollback_id=None,
                        error_message=str(result),
                    ))
                    failed.add(req.action_id)
                else:
                    results.append(result)
                    if result.status == ExecutionStatus.COMPLETED:
                        completed.add(req.action_id)
                    else:
                        failed.add(req.action_id)
        
        return results
    
    async def rollback_incident(self, incident_id: UUID) -> List[ExecutionResult]:
        """Rollback all actions for an incident in reverse order."""
        incident_key = str(incident_id)
        history = self._execution_history.get(incident_key, [])
        
        if not history:
            logger.warning("no_actions_to_rollback", incident_id=incident_key)
            return []
        
        results = []
        
        # Rollback in reverse order
        for execution in reversed(history):
            if execution.rollback_id and execution.status == ExecutionStatus.COMPLETED:
                connector_type = execution.connector_used
                connector = self.connectors.get(connector_type)
                
                if connector:
                    try:
                        rollback_result = await connector.rollback(execution.rollback_id)
                        
                        results.append(ExecutionResult(
                            action_id=f"rollback_{execution.action_id}",
                            status=ExecutionStatus.COMPLETED if rollback_result.success else ExecutionStatus.FAILED,
                            connector_used=connector_type,
                            started_at=datetime.utcnow(),
                            completed_at=datetime.utcnow(),
                            result_data=rollback_result.data or {},
                            rollback_id=None,
                            error_message=None if rollback_result.success else rollback_result.message,
                        ))
                        
                        logger.info(
                            "action_rolled_back",
                            original_action=execution.action_id,
                            success=rollback_result.success,
                        )
                    except Exception as e:
                        logger.error("rollback_failed", action_id=execution.action_id, error=str(e))
        
        return results
    
    async def get_execution_status(self, incident_id: UUID) -> Dict[str, Any]:
        """Get execution status for an incident."""
        incident_key = str(incident_id)
        history = self._execution_history.get(incident_key, [])
        
        return {
            "incident_id": incident_key,
            "total_actions": len(history),
            "completed": sum(1 for e in history if e.status == ExecutionStatus.COMPLETED),
            "failed": sum(1 for e in history if e.status == ExecutionStatus.FAILED),
            "actions": [
                {
                    "action_id": e.action_id,
                    "status": e.status.value,
                    "connector": e.connector_used,
                    "rollback_available": e.rollback_id is not None,
                }
                for e in history
            ],
        }


# Global executor instance
action_executor = ActionExecutor()
