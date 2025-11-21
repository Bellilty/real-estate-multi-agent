"""
Performance Tracking and Chain-of-Thought System
Tracks agent reasoning, execution time, and resource usage
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ReasoningStep:
    """A single step in the chain of thought"""
    agent: str
    action: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    reasoning: str
    duration_ms: float
    timestamp: str
    success: bool
    error: Optional[str] = None


@dataclass
class ExecutionMetrics:
    """Performance metrics for the entire workflow"""
    total_duration_ms: float
    llm_calls: int
    total_tokens: int = 0
    steps_count: int = 0
    success: bool = True
    error: Optional[str] = None


class ChainOfThoughtTracker:
    """Tracks the reasoning and performance of the multi-agent system"""
    
    def __init__(self):
        self.steps: List[ReasoningStep] = []
        self.start_time: float = 0
        self.llm_call_count: int = 0
        self.total_tokens: int = 0
        
    def start_tracking(self):
        """Start tracking a new workflow"""
        self.steps = []
        self.start_time = time.time()
        self.llm_call_count = 0
        self.total_tokens = 0
    
    def add_step(
        self,
        agent: str,
        action: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        reasoning: str,
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Add a reasoning step to the chain"""
        step = ReasoningStep(
            agent=agent,
            action=action,
            input_data=input_data,
            output_data=output_data,
            reasoning=reasoning,
            duration_ms=duration_ms,
            timestamp=datetime.now().isoformat(),
            success=success,
            error=error
        )
        self.steps.append(step)
        
        # Count LLM calls
        if "llm" in action.lower() or agent in ["Router", "Extractor", "Formatter"]:
            self.llm_call_count += 1
    
    def get_metrics(self) -> ExecutionMetrics:
        """Get execution metrics"""
        total_duration = (time.time() - self.start_time) * 1000  # ms
        success = all(step.success for step in self.steps)
        
        return ExecutionMetrics(
            total_duration_ms=round(total_duration, 2),
            llm_calls=self.llm_call_count,
            total_tokens=self.total_tokens,
            steps_count=len(self.steps),
            success=success
        )
    
    def get_chain_of_thought(self) -> List[Dict[str, Any]]:
        """Get the full chain of thought for display"""
        return [
            {
                "agent": step.agent,
                "action": step.action,
                "reasoning": step.reasoning,
                "duration_ms": step.duration_ms,
                "success": step.success,
                "error": step.error,
                "input": step.input_data,
                "output": step.output_data
            }
            for step in self.steps
        ]
    
    def get_summary(self) -> str:
        """Get a human-readable summary of the chain of thought"""
        lines = ["🧠 Chain of Thought:\n"]
        
        for i, step in enumerate(self.steps, 1):
            status = "✅" if step.success else "❌"
            lines.append(f"{i}. {status} **{step.agent}** ({step.duration_ms:.0f}ms)")
            lines.append(f"   *{step.reasoning}*")
            
            if step.error:
                lines.append(f"   ⚠️ Error: {step.error}")
            
            lines.append("")
        
        metrics = self.get_metrics()
        lines.append(f"📊 **Total Time:** {metrics.total_duration_ms:.0f}ms | **LLM Calls:** {metrics.llm_calls}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tracker to dictionary for serialization"""
        metrics = self.get_metrics()
        return {
            "steps": self.get_chain_of_thought(),
            "metrics": {
                "total_duration_ms": metrics.total_duration_ms,
                "llm_calls": metrics.llm_calls,
                "total_tokens": metrics.total_tokens,
                "steps_count": metrics.steps_count,
                "success": metrics.success,
                "error": metrics.error
            },
            "start_time": self.start_time,
            "llm_call_count": self.llm_call_count
        }


def time_execution(func):
    """Decorator to time function execution"""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = (time.time() - start) * 1000
        return result, duration
    return wrapper

