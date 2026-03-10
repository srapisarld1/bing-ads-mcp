"""Entry point for the Bing Ads MCP server."""

from bing_ads_mcp.coordinator import mcp

# The following imports are necessary to register the tools with the `mcp`
# object, even though they are not directly used in this file.
from bing_ads_mcp.tools import core  # noqa: F401
from bing_ads_mcp.tools import campaigns  # noqa: F401
from bing_ads_mcp.tools import ad_groups  # noqa: F401
from bing_ads_mcp.tools import ads  # noqa: F401
from bing_ads_mcp.tools import keywords  # noqa: F401
from bing_ads_mcp.tools import reporting  # noqa: F401


def run_server() -> None:
    mcp.run()


if __name__ == "__main__":
    run_server()
