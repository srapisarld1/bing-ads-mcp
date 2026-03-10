"""Reporting tool: async report submit/poll/download/parse."""

import csv
import io
import time
import zipfile
from typing import Any, Dict, List, Optional

from bing_ads_mcp.coordinator import mcp
import bing_ads_mcp.utils as utils

_REPORT_DESCRIPTION = """\
Submits a Microsoft Advertising report request and returns the parsed results.

Handles the full async lifecycle: submit report -> poll for completion ->
download ZIP -> extract CSV -> parse and return rows.

Args:
    account_id: The account ID to report on.
    report_type: The type of report. Options:
        - CampaignPerformanceReport
        - AdGroupPerformanceReport
        - KeywordPerformanceReport
        - AdPerformanceReport
        - SearchQueryPerformanceReport
        - AgeGenderAudienceReport
        - GeographicPerformanceReport
        - ProductDimensionPerformanceReport
        - DestinationUrlPerformanceReport
        - AccountPerformanceReport
    columns: List of column names to include. Common columns by report type:

        CampaignPerformanceReport:
            TimePeriod, AccountName, AccountId, CampaignName, CampaignId,
            CampaignStatus, Impressions, Clicks, Ctr, AverageCpc, Spend,
            Conversions, ConversionRate, Revenue, ReturnOnAdSpend,
            QualityScore, ImpressionSharePercent

        AdGroupPerformanceReport:
            TimePeriod, AccountName, CampaignName, AdGroupName, AdGroupId,
            AdGroupStatus, Impressions, Clicks, Ctr, AverageCpc, Spend,
            Conversions, ConversionRate, Revenue

        KeywordPerformanceReport:
            TimePeriod, AccountName, CampaignName, AdGroupName, Keyword,
            KeywordId, KeywordStatus, BidMatchType, DeliveredMatchType,
            QualityScore, Impressions, Clicks, Ctr, AverageCpc, Spend,
            Conversions, Revenue, AveragePosition

        AdPerformanceReport:
            TimePeriod, AccountName, CampaignName, AdGroupName, AdId,
            AdType, AdTitle, AdDescription, FinalUrl, Impressions,
            Clicks, Ctr, AverageCpc, Spend, Conversions

        SearchQueryPerformanceReport:
            TimePeriod, AccountName, CampaignName, AdGroupName, SearchQuery,
            Keyword, DeliveredMatchType, Impressions, Clicks, Ctr, Spend,
            Conversions

    start_date: Start date in YYYY-MM-DD format.
    end_date: End date in YYYY-MM-DD format.
    aggregation: Time aggregation. Options: Summary, Daily, Weekly, Monthly,
        Hourly, DayOfWeek, HourOfDay. Default: Daily.
        Note: TimePeriod column is incompatible with Summary aggregation.
        If you include TimePeriod in columns with Summary aggregation,
        TimePeriod will be automatically removed from columns.
    limit: Maximum number of rows to return. Default: 1000.

Returns:
    List of dicts, one per row, with column names as keys.
"""


def get_report(
    account_id: str,
    report_type: str,
    columns: List[str],
    start_date: str,
    end_date: str,
    aggregation: str = "Daily",
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    service = utils.get_service_client("ReportingService")

    # Build the report request
    report_request = _build_report_request(
        service, account_id, report_type, columns, start_date, end_date,
        aggregation,
    )

    # Submit the report
    try:
        report_request_id = service.SubmitGenerateReport(
            ReportRequest=report_request,
        )
    except Exception as e:
        error_msg = str(e)
        # Extract detailed SOAP fault info if available
        if hasattr(e, "fault") and hasattr(e.fault, "detail"):
            try:
                detail = e.fault.detail
                if hasattr(detail, "ApiFaultDetail"):
                    fault_detail = detail.ApiFaultDetail
                    if hasattr(fault_detail, "OperationErrors") and fault_detail.OperationErrors:
                        errors = fault_detail.OperationErrors.OperationError
                        parts = []
                        for op_err in errors:
                            parts.append(
                                f"Code {op_err.Code}: {op_err.Message}"
                            )
                        error_msg = "; ".join(parts)
            except Exception:
                pass
        return [{"error": error_msg}]

    utils.logger.info("Report submitted, request ID: %s", report_request_id)

    # Poll for completion
    report_url = _poll_report(service, report_request_id, timeout=120)
    if report_url is None:
        return [{"error": "Report timed out after 120 seconds"}]

    # Download, extract, and parse
    rows = _download_and_parse(report_url, limit)
    return rows


def _build_report_request(
    service,
    account_id: str,
    report_type: str,
    columns: List[str],
    start_date: str,
    end_date: str,
    aggregation: str,
):
    """Builds a SOAP report request object."""
    report_request = service.factory.create(report_type + "Request")

    report_request.Format = "Csv"
    report_request.ReportName = f"MCP {report_type}"
    report_request.ReturnOnlyCompleteData = False
    report_request.Aggregation = aggregation

    # TimePeriod column is incompatible with Summary aggregation (error 2034).
    # Auto-remove it to prevent cryptic SOAP faults.
    if aggregation == "Summary":
        columns = [c for c in columns if c != "TimePeriod"]

    # Set columns
    columns_type = report_type + "Column"
    column_array = service.factory.create(f"ArrayOf{columns_type}")
    for col in columns:
        column_array[columns_type].append(col)
    report_request.Columns = column_array

    # Set time period
    report_time = service.factory.create("ReportTime")
    report_time.PredefinedTime = None

    start_parts = start_date.split("-")
    custom_start = service.factory.create("Date")
    custom_start.Year = int(start_parts[0])
    custom_start.Month = int(start_parts[1])
    custom_start.Day = int(start_parts[2])
    report_time.CustomDateRangeStart = custom_start

    end_parts = end_date.split("-")
    custom_end = service.factory.create("Date")
    custom_end.Year = int(end_parts[0])
    custom_end.Month = int(end_parts[1])
    custom_end.Day = int(end_parts[2])
    report_time.CustomDateRangeEnd = custom_end

    report_time.ReportTimeZone = "GreenwichMeanTimeDublinEdinburghLisbonLondon"
    report_request.Time = report_time

    # Set scope (account level) — the request already has a typed Scope object.
    # Nullify empty sub-arrays that the factory creates (e.g., AdGroups,
    # Campaigns) to prevent serialization issues with some report types.
    report_request.Scope.AccountIds = {"long": [int(account_id)]}
    if hasattr(report_request.Scope, "AdGroups"):
        report_request.Scope.AdGroups = None
    if hasattr(report_request.Scope, "Campaigns"):
        report_request.Scope.Campaigns = None

    # Nullify optional Filter and Sort to avoid sending empty SOAP elements
    if hasattr(report_request, "Filter"):
        report_request.Filter = None
    if hasattr(report_request, "Sort"):
        report_request.Sort = None

    return report_request


def _poll_report(
    service,
    report_request_id: str,
    timeout: int = 120,
    poll_interval: int = 2,
) -> Optional[str]:
    """Polls for report completion. Returns download URL or None on timeout."""
    start_time = time.time()

    while time.time() - start_time < timeout:
        status = service.PollGenerateReport(
            ReportRequestId=report_request_id,
        )

        report_status = status.Status
        utils.logger.info("Report status: %s", report_status)

        if report_status == "Success":
            return status.ReportDownloadUrl
        elif report_status == "Error":
            return None

        time.sleep(poll_interval)

    utils.logger.warning("Report timed out after %d seconds", timeout)
    return None


def _download_and_parse(
    report_url: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """Downloads a report ZIP, extracts the CSV, and parses rows."""
    import urllib.request

    response = urllib.request.urlopen(report_url)
    zip_data = response.read()

    with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
        csv_filename = zf.namelist()[0]
        csv_data = zf.read(csv_filename).decode("utf-8-sig")

    # Bing report CSVs have metadata header lines, a blank line, then
    # column headers, data rows, a blank line, and a copyright footer.
    lines = csv_data.split("\n")

    # Strip \r from each line
    lines = [line.rstrip("\r") for line in lines]

    # Find the column header row: first non-empty line after an empty line
    # that follows the metadata block. The metadata lines all start with '"'
    # and contain ':' (e.g., "Report Name:", "Report Time:", etc.)
    header_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip().strip('"')
        if not stripped:
            # Empty line — the next non-empty line is the column header
            for j in range(i + 1, len(lines)):
                if lines[j].strip():
                    header_idx = j
                    break
            if header_idx is not None:
                break

    if header_idx is None:
        return []

    # Collect data lines from header onwards, stopping at empty lines or footer
    data_lines = []
    for line in lines[header_idx:]:
        stripped = line.strip()
        if not stripped:
            break
        if "Microsoft Corporation" in line:
            break
        data_lines.append(line)

    if not data_lines:
        return []

    reader = csv.DictReader(io.StringIO("\n".join(data_lines)))

    rows = []
    for row in reader:
        rows.append(dict(row))
        if len(rows) >= limit:
            break

    return rows


# Register with dynamic description
mcp.add_tool(
    get_report,
    description=_REPORT_DESCRIPTION,
)
