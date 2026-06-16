"""CFD post-processing module placeholder."""

__version__ = "0.2.0"
"""Public-safe Fluent postprocessing helpers."""

from .monitor_parser import parse_monitor_file
from .summary import summarize_run
from .video_plan import write_video_plan

__all__ = ["parse_monitor_file", "summarize_run", "write_video_plan"]
