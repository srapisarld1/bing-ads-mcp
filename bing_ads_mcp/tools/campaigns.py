"""Campaign management tools."""

from typing import Any, Dict, List, Optional

from bing_ads_mcp.coordinator import mcp
import bing_ads_mcp.utils as utils


@mcp.tool()
def get_campaigns(
    account_id: str,
    campaign_type: str = "Search",
    statuses: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Gets campaigns for a Microsoft Advertising account.

    Args:
        account_id: The account ID to get campaigns from.
        campaign_type: Campaign type filter. Options: Search, Shopping,
            DynamicSearchAds, Audience, Hotel, PerformanceMax. Default: Search.
        statuses: Optional list of status filters. Options: Active, Paused,
            BudgetPaused, BudgetAndManualPaused, Deleted, Suspended.
            If not provided, returns all non-deleted campaigns.

    Returns:
        List of campaign objects with fields like Id, Name, Status,
        BudgetType, DailyBudget, TimeZone, etc.
    """
    service = utils.get_service_client("CampaignManagementService")

    campaign_types = service.factory.create("CampaignType")
    # CampaignType is a flag enum, set the requested type
    campaign_type_value = campaign_type

    response = service.GetCampaignsByAccountId(
        AccountId=account_id,
        CampaignType=campaign_type_value,
    )

    campaigns = []
    if hasattr(response, "Campaign") and response.Campaign:
        for campaign in response.Campaign:
            if statuses:
                status = getattr(campaign, "Status", None)
                if status and str(status) not in statuses:
                    continue
            campaigns.append(utils.format_soap_entity(campaign))

    return campaigns
