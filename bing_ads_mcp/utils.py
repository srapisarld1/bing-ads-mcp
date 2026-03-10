"""Auth, config loading, and SOAP helpers for the Bing Ads MCP server."""

import os
import logging
import yaml
from typing import Any, Dict, Optional

from bingads.authorization import (
    AuthorizationData,
    OAuthDesktopMobileAuthCodeGrant,
    OAuthTokens,
)
from bingads.service_client import ServiceClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

_ENVIRONMENT = "production"
_REDIRECT_URI = "https://login.microsoftonline.com/common/oauth2/nativeclient"

_config: Optional[Dict[str, str]] = None
_authorization_data: Optional[AuthorizationData] = None


def _get_config_path() -> str:
    """Returns the path to the bing-ads.yaml config file."""
    path = os.environ.get("BING_ADS_CREDENTIALS")
    if path is None:
        raise ValueError(
            "BING_ADS_CREDENTIALS environment variable not set. "
            "Set it to the path of your bing-ads.yaml file."
        )
    return path


def get_config() -> Dict[str, str]:
    """Loads and caches the YAML config file."""
    global _config
    if _config is not None:
        return _config

    config_path = _get_config_path()
    with open(config_path, "r") as f:
        _config = yaml.safe_load(f)

    required = ["client_id", "developer_token", "refresh_token"]
    for key in required:
        if not _config.get(key):
            raise ValueError(
                f"Missing required config key '{key}' in {config_path}. "
                f"Run 'bing-ads-mcp-auth' to complete setup."
            )

    return _config


def _save_refresh_token(new_refresh_token: str) -> None:
    """Persists a new refresh token back to the YAML config file."""
    config_path = _get_config_path()
    config = get_config()
    config["refresh_token"] = new_refresh_token

    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    logger.info("Refresh token updated in %s", config_path)


def _token_refreshed_callback(oauth_tokens: OAuthTokens) -> None:
    """Called by the SDK when a token is auto-refreshed."""
    if oauth_tokens.refresh_token:
        _save_refresh_token(oauth_tokens.refresh_token)


def _build_authorization_data() -> AuthorizationData:
    """Creates an AuthorizationData instance with OAuth refresh token auth."""
    config = get_config()

    authentication = OAuthDesktopMobileAuthCodeGrant(
        client_id=config["client_id"],
        env=_ENVIRONMENT,
    )
    authentication.token_refreshed_callback = _token_refreshed_callback

    authentication.request_oauth_tokens_by_refresh_token(
        config["refresh_token"]
    )

    authorization_data = AuthorizationData(
        authentication=authentication,
        developer_token=config["developer_token"],
    )

    customer_id = config.get("customer_id")
    if customer_id:
        authorization_data.customer_id = str(customer_id)

    account_id = config.get("account_id")
    if account_id:
        authorization_data.account_id = str(account_id)

    return authorization_data


def get_authorization_data() -> AuthorizationData:
    """Returns the cached AuthorizationData singleton."""
    global _authorization_data
    if _authorization_data is None:
        _authorization_data = _build_authorization_data()
    return _authorization_data


def get_service_client(service_name: str) -> ServiceClient:
    """Creates a ServiceClient for the given Bing Ads service."""
    auth_data = get_authorization_data()
    return ServiceClient(
        service=service_name,
        version=13,
        authorization_data=auth_data,
        environment=_ENVIRONMENT,
    )


def format_soap_entity(entity: Any) -> Dict[str, Any]:
    """Converts a Bing Ads SOAP entity (suds object) to a plain dict.

    Recursively converts suds objects, handling lists and nested types.
    Skips None values and internal attributes.
    """
    if entity is None:
        return None

    # Handle lists/arrays from SOAP
    if isinstance(entity, list):
        return [format_soap_entity(item) for item in entity]

    # Handle suds ArrayOf* wrappers — they have a single key whose value is a list
    entity_type = type(entity).__name__
    if entity_type.startswith("ArrayOf"):
        # suds ArrayOf types have a single attribute that is the list
        for attr_name in _get_suds_attrs(entity):
            val = getattr(entity, attr_name, None)
            if val is not None:
                if isinstance(val, list):
                    return [format_soap_entity(item) for item in val]
                # Sometimes it wraps a single item
                return [format_soap_entity(val)]
        return []

    # Handle primitive-like types
    if isinstance(entity, (str, int, float, bool)):
        return entity

    # Handle suds objects by iterating their attributes
    attrs = _get_suds_attrs(entity)
    if not attrs:
        return str(entity)

    result = {}
    for attr_name in attrs:
        if attr_name.startswith("_"):
            continue
        val = getattr(entity, attr_name, None)
        if val is None:
            continue
        result[attr_name] = format_soap_entity(val)

    return result


def _get_suds_attrs(obj: Any) -> list:
    """Gets attribute names from a suds object."""
    # suds objects store their data in __dict__ or via __keylist__
    if hasattr(obj, "__keylist__"):
        return list(obj.__keylist__)
    if hasattr(obj, "__dict__"):
        return [k for k in obj.__dict__ if not k.startswith("_")]
    return []
