"""Keyword management tools."""

from typing import Any, Dict, List

from bing_ads_mcp.coordinator import mcp
import bing_ads_mcp.utils as utils


@mcp.tool()
def get_keywords(
    account_id: str,
    ad_group_id: str,
) -> List[Dict[str, Any]]:
    """Gets keywords for an ad group.

    Args:
        account_id: The account ID containing the ad group.
        ad_group_id: The ad group ID to get keywords from.

    Returns:
        List of keyword objects with fields like Id, Text, MatchType,
        Status, Bid (CpcBid), FinalUrls, DestinationUrl, etc.
    """
    service = utils.get_service_client("CampaignManagementService")
    service.authorization_data.account_id = str(account_id)

    response = service.GetKeywordsByAdGroupId(
        AdGroupId=ad_group_id,
    )

    keywords = []
    if hasattr(response, "Keyword") and response.Keyword:
        for keyword in response.Keyword:
            keywords.append(utils.format_soap_entity(keyword))

    return keywords
