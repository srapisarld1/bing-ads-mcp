"""Core tools: list accessible accounts."""

from typing import Any, Dict, List

from bing_ads_mcp.coordinator import mcp
import bing_ads_mcp.utils as utils


@mcp.tool()
def list_accounts() -> List[Dict[str, Any]]:
    """Lists all Microsoft Advertising accounts accessible to the authenticated user.

    Returns account details including Id, Name, Number, AccountLifeCycleStatus,
    and ParentCustomerId.
    """
    service = utils.get_service_client("CustomerManagementService")

    # Get the customer ID — use config value or auto-detect via GetUser
    config = utils.get_config()
    customer_id = config.get("customer_id")

    if not customer_id:
        user_response = service.GetUser(UserId=None)
        if hasattr(user_response, "CustomerRoles") and user_response.CustomerRoles:
            roles = user_response.CustomerRoles
            if hasattr(roles, "CustomerRole") and roles.CustomerRole:
                customer_id = roles.CustomerRole[0].CustomerId

    if not customer_id:
        return [{"error": "Could not determine customer ID. Set customer_id in bing-ads.yaml."}]

    response = service.GetAccountsInfo(
        CustomerId=int(customer_id),
        OnlyParentAccounts=False,
    )

    accounts = []
    if hasattr(response, "AccountInfo") and response.AccountInfo:
        for acct in response.AccountInfo:
            accounts.append(utils.format_soap_entity(acct))

    return accounts
