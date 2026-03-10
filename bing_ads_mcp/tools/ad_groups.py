"""Ad group management tools."""

from typing import Any, Dict, List

from bing_ads_mcp.coordinator import mcp
import bing_ads_mcp.utils as utils


@mcp.tool()
def get_ad_groups(
    account_id: str,
    campaign_id: str,
) -> List[Dict[str, Any]]:
    """Gets ad groups for a campaign.

    Args:
        account_id: The account ID containing the campaign.
        campaign_id: The campaign ID to get ad groups from.

    Returns:
        List of ad group objects with fields like Id, Name, Status,
        CpcBid, StartDate, EndDate, Language, Network, etc.
    """
    service = utils.get_service_client("CampaignManagementService")
    service.authorization_data.account_id = str(account_id)

    response = service.GetAdGroupsByCampaignId(
        CampaignId=campaign_id,
    )

    ad_groups = []
    if hasattr(response, "AdGroup") and response.AdGroup:
        for ad_group in response.AdGroup:
            ad_groups.append(utils.format_soap_entity(ad_group))

    return ad_groups
