import os
import json
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, Dimension, Metric, DateRange, OrderBy
)
from googleapiclient.discovery import build

CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["GOOGLE_REFRESH_TOKEN"]
GA4_PROPERTY_ID = os.environ["GA4_PROPERTY_ID"]
GSC_SITE_URL = os.environ["GSC_SITE_URL"]

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
]

def get_credentials():
    return Credentials(
        token=None,
        refresh_token=REFRESH_TOKEN,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )

def fetch_ga4(creds):
    client = BetaAnalyticsDataClient(credentials=creds)
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=27)).strftime("%Y-%m-%d")

    # 일별 세션/사용자 추이
    trend_req = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="date")],
        metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))]
    )
    trend_res = client.run_report(trend_req)
    trend = [
        {
            "date": r.dimension_values[0].value,
            "sessions": int(r.metric_values[0].value),
            "users": int(r.metric_values[1].value),
        }
        for r in trend_res.rows
    ]

    # 요약 지표
    summary_req = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        metrics=[
            Metric(name="sessions"),
            Metric(name="activeUsers"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
        ],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )
    summary_res = client.run_report(summary_req)
    row = summary_res.rows[0]
    summary = {
        "sessions": int(row.metric_values[0].value),
        "users": int(row.metric_values[1].value),
        "bounceRate": round(float(row.metric_values[2].value) * 100, 1),
        "avgSessionDuration": round(float(row.metric_values[3].value)),
    }

    # 상위 페이지
    pages_req = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="pageTitle"), Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews"), Metric(name="averageSessionDuration")],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
        limit=5,
    )
    pages_res = client.run_report(pages_req)
    pages = [
        {
            "title": r.dimension_values[0].value,
            "path": r.dimension_values[1].value,
            "pageviews": int(r.metric_values[0].value),
            "avgDuration": round(float(r.metric_values[1].value)),
        }
        for r in pages_res.rows
    ]

    # 디바이스 유형
    device_req = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="deviceCategory")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
    )
    device_res = client.run_report(device_req)
    devices = [
        {
            "device": r.dimension_values[0].value,
            "sessions": int(r.metric_values[0].value),
        }
        for r in device_res.rows
    ]

    # 유입 채널
    channel_req = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
    )
    channel_res = client.run_report(channel_req)
    channels = [
        {
            "channel": r.dimension_values[0].value,
            "sessions": int(r.metric_values[0].value),
        }
        for r in channel_res.rows
    ]

    return {"trend": trend, "summary": summary, "pages": pages, "devices": devices, "channels": channels}


def fetch_gsc(creds):
    service = build("searchconsole", "v1", credentials=creds)
    end_date = datetime.today().strftime("%Y-%m-%d")
    start_date = (datetime.today() - timedelta(days=27)).strftime("%Y-%m-%d")

    # 요약 지표
    summary_res = service.searchanalytics().query(
        siteUrl=GSC_SITE_URL,
        body={"startDate": start_date, "endDate": end_date, "dimensions": []}
    ).execute()
    summary = summary_res.get("rows", [{}])[0]
    gsc_summary = {
        "clicks": int(summary.get("clicks", 0)),
        "impressions": int(summary.get("impressions", 0)),
        "ctr": round(summary.get("ctr", 0) * 100, 2),
        "position": round(summary.get("position", 0), 1),
    }

    # 상위 쿼리
    queries_res = service.searchanalytics().query(
        siteUrl=GSC_SITE_URL,
        body={
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": ["query"],
            "rowLimit": 10,
        }
    ).execute()
    queries = [
        {
            "query": r["keys"][0],
            "clicks": int(r.get("clicks", 0)),
            "impressions": int(r.get("impressions", 0)),
            "ctr": round(r.get("ctr", 0) * 100, 2),
            "position": round(r.get("position", 0), 1),
        }
        for r in queries_res.get("rows", [])
    ]

    # 일별 클릭 추이
    trend_res = service.searchanalytics().query(
        siteUrl=GSC_SITE_URL,
        body={
            "startDate": start_date,
            "endDate": end_date,
            "dimensions": ["date"],
        }
    ).execute()
    trend = [
        {
            "date": r["keys"][0],
            "clicks": int(r.get("clicks", 0)),
            "impressions": int(r.get("impressions", 0)),
        }
        for r in trend_res.get("rows", [])
    ]

    return {"summary": gsc_summary, "queries": queries, "trend": trend}


def main():
    creds = get_credentials()
    ga4_data = fetch_ga4(creds)
    gsc_data = fetch_gsc(creds)

    output = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "ga4": ga4_data,
        "gsc": gsc_data,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/dashboard.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("✅ data/dashboard.json 생성 완료")


if __name__ == "__main__":
    main()
