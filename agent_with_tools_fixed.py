"""Fixed version of agent_with_tools.py with proper tool handling."""

# Key issues found in agent_with_tools.py:

# 1. The tool use parsing logic is incorrect. It's trying to parse tool uses from 
#    content_block_stop events, but should be tracking content blocks with type "tool_use"

# 2. The SSE event parsing needs to properly handle content_block_start events to 
#    identify when a tool_use block begins

# 3. The tool collection logic needs to accumulate tool input data as it streams

# Here's the corrected approach for the stream_response_with_tools method:

"""
Key changes needed:

1. Track content blocks by their type from content_block_start events
2. Accumulate tool use data from content_block_delta events when in a tool_use block
3. Properly format tool uses when content_block_stop is received for a tool_use block

Example of correct event handling:

# When we get content_block_start with type="tool_use":
current_block_type = "tool_use"
current_tool_use = {"id": block_id, "name": "", "input": {}}

# When we get content_block_delta while in tool_use block:
if current_block_type == "tool_use":
    # Parse the delta to build up the tool use

# When we get content_block_stop for a tool_use block:
if current_block_type == "tool_use":
    tool_uses.append(current_tool_use)
    current_block_type = None
"""

# The main issue is that the current code doesn't properly track the content block
# lifecycle and misses the tool use information that streams through the events.