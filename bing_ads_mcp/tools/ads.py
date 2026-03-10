"""Ad management tools."""

from typing import Any, Dict, List, Optional

from bing_ads_mcp.coordinator import mcp
import bing_ads_mcp.utils as utils


@mcp.tool()
def get_ads(
    account_id: str,
    ad_group_id: str,
    ad_types: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Gets ads for an ad group.

    Args:
        account_id: The account ID containing the ad group.
        ad_group_id: The ad group ID to get ads from.
        ad_types: Optional list of ad type filters. Options: Text,
            ExpandedText, ResponsiveSearch, ResponsiveAd, Image,
            Product, AppInstall, DynamicSearch.
            Default: ["ResponsiveSearch"] (most common modern ad type).

    Returns:
        List of ad objects with fields like Id, Type, Status, FinalUrls,
        Headlines, Descriptions, etc. Fields vary by ad type.
    """
    service = utils.get_service_client("CampaignManagementService")
    service.authorization_data.account_id = str(account_id)

    if ad_types is None:
        ad_types = ["ResponsiveSearch"]

    ad_type_array = service.factory.create("ArrayOfAdType")
    for ad_type in ad_types:
        ad_type_array.AdType.append(ad_type)

    response = service.GetAdsByAdGroupId(
        AdGroupId=ad_group_id,
        AdTypes=ad_type_array,
    )

    ads = []
    if hasattr(response, "Ad") and response.Ad:
        for ad in response.Ad:
            ads.append(utils.format_soap_entity(ad))

    return ads
