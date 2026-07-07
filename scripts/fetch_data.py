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
    "https://www.googleapis.com/auth/adsense.readonly",
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

def get_dates():
    today = datetime.today()
    yesterday = today - timedelta(days=1)
    start_28 = today - timedelta(days=27)
    return {
        "yesterday": yesterday.strftime("%Y-%m-%d"),
        "start_28": start_28.strftime("%Y-%m-%d"),
        "today": today.strftime("%Y-%m-%d"),
    }

def fetch_ga4(creds, dates):
    client = BetaAnalyticsDataClient(credentials=creds)

    # 어제 요약
    yesterday_req = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        metrics=[Metric(name="sessions"), Metric(name="activeUsers"), Metric(name="screenPageViews")],
        date_ranges=[DateRange(start_date=dates["yesterday"], end_date=dates["yesterday"])],
    )
    y_res = client.run_report(yesterday_req)
    y_row = y_res.rows[0] if y_res.rows else None
    yesterday_summary = {
        "sessions": int(y_row.metric_values[0].value) if y_row else 0,
        "users": int(y_row.metric_values[1].value) if y_row else 0,
        "pageviews": int(y_row.metric_values[2].value) if y_row else 0,
    }

    # 28일 추이
    trend_req = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="date")],
        metrics=[Metric(name="sessions"), Metric(name="activeUsers")],
        date_ranges=[DateRange(start_date=dates["start_28"], end_date=dates["yesterday"])],
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

    # 28일 요약
    summary_req = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        metrics=[Metric(name="sessions"), Metric(name="activeUsers"), Metric(name="bounceRate")],
        date_ranges=[DateRange(start_date=dates["start_28"], end_date=dates["yesterday"])],
    )
    summary_res = client.run_report(summary_req)
    row = summary_res.rows[0]
    summary = {
        "sessions": int(row.metric_values[0].value),
        "users": int(row.metric_values[1].value),
        "bounceRate": round(float(row.metric_values[2].value) * 100, 1),
    }

    # 상위 페이지
    pages_req = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="pageTitle"), Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews")],
        date_ranges=[DateRange(start_date=dates["start_28"], end_date=dates["yesterday"])],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
        limit=5,
    )
    pages_res = client.run_report(pages_req)
    pages = [
        {
            "title": r.dimension_values[0].value,
            "path": r.dimension_values[1].value,
            "pageviews": int(r.metric_values[0].value),
        }
        for r in pages_res.rows
    ]

    # 디바이스
    device_req = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="deviceCategory")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=dates["start_28"], end_date=dates["yesterday"])],
    )
    device_res = client.run_report(device_req)
    devices = [{"device": r.dimension_values[0].value, "sessions": int(r.metric_values[0].value)} for r in device_res.rows]

    # 채널
    channel_req = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date=dates["start_28"], end_date=dates["yesterday"])],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
    )
    channel_res = client.run_report(channel_req)
    channels = [{"channel": r.dimension_values[0].value, "sessions": int(r.metric_values[0].value)} for r in channel_res.rows]

    return {"yesterday": yesterday_summary, "trend": trend, "summary": summary, "pages": pages, "devices": devices, "channels": channels}


def fetch_gsc(creds, dates):
    service = build("searchconsole", "v1", credentials=creds)

    # 어제 요약
    y_res = service.searchanalytics().query(
        siteUrl=GSC_SITE_URL,
        body={"startDate": dates["yesterday"], "endDate": dates["yesterday"], "dimensions": []}
    ).execute()
    y_row = y_res.get("rows", [{}])[0]
    yesterday_summary = {
        "clicks": int(y_row.get("clicks", 0)),
        "impressions": int(y_row.get("impressions", 0)),
        "ctr": round(y_row.get("ctr", 0) * 100, 2),
        "position": round(y_row.get("position", 0), 1),
    }

    # 28일 요약
    summary_res = service.searchanalytics().query(
        siteUrl=GSC_SITE_URL,
        body={"startDate": dates["start_28"], "endDate": dates["yesterday"], "dimensions": []}
    ).execute()
    s_row = summary_res.get("rows", [{}])[0]
    summary = {
        "clicks": int(s_row.get("clicks", 0)),
        "impressions": int(s_row.get("impressions", 0)),
        "ctr": round(s_row.get("ctr", 0) * 100, 2),
        "position": round(s_row.get("position", 0), 1),
    }

    # 상위 쿼리
    queries_res = service.searchanalytics().query(
        siteUrl=GSC_SITE_URL,
        body={"startDate": dates["start_28"], "endDate": dates["yesterday"], "dimensions": ["query"], "rowLimit": 10}
    ).execute()
    queries = [
        {"query": r["keys"][0], "clicks": int(r.get("clicks", 0)), "impressions": int(r.get("impressions", 0)),
         "ctr": round(r.get("ctr", 0) * 100, 2), "position": round(r.get("position", 0), 1)}
        for r in queries_res.get("rows", [])
    ]

    # 28일 추이
    trend_res = service.searchanalytics().query(
        siteUrl=GSC_SITE_URL,
        body={"startDate": dates["start_28"], "endDate": dates["yesterday"], "dimensions": ["date"]}
    ).execute()
    trend = [
        {"date": r["keys"][0], "clicks": int(r.get("clicks", 0)), "impressions": int(r.get("impressions", 0))}
        for r in trend_res.get("rows", [])
    ]

    # 어제 노출된 콘텐츠 (페이지별)
    yesterday_pages_res = service.searchanalytics().query(
        siteUrl=GSC_SITE_URL,
        body={"startDate": dates["yesterday"], "endDate": dates["yesterday"], "dimensions": ["page"], "rowLimit": 25}
    ).execute()
    yesterday_pages = [
        {
            "page": r["keys"][0],
            "clicks": int(r.get("clicks", 0)),
            "impressions": int(r.get("impressions", 0)),
            "ctr": round(r.get("ctr", 0) * 100, 2),
            "position": round(r.get("position", 0), 1),
        }
        for r in yesterday_pages_res.get("rows", [])
    ]
    yesterday_pages.sort(key=lambda x: x["impressions"], reverse=True)

    return {
        "yesterday": yesterday_summary,
        "summary": summary,
        "queries": queries,
        "trend": trend,
        "yesterday_pages": yesterday_pages,
    }


def fetch_adsense(creds, dates):
    service = build("adsense", "v2", credentials=creds)

    # 계정 목록 가져오기
    accounts = service.accounts().list().execute()
    account_id = accounts["accounts"][0]["name"]

    # 어제 수익
    y_report = service.accounts().reports().generate(
        account=account_id,
        dateRange="CUSTOM",
        startDate_year=int(dates["yesterday"][:4]),
        startDate_month=int(dates["yesterday"][5:7]),
        startDate_day=int(dates["yesterday"][8:10]),
        endDate_year=int(dates["yesterday"][:4]),
        endDate_month=int(dates["yesterday"][5:7]),
        endDate_day=int(dates["yesterday"][8:10]),
        metrics=["ESTIMATED_EARNINGS", "PAGE_VIEWS_RPM", "IMPRESSIONS", "CLICKS", "PAGE_VIEWS_CTR"]
    ).execute()
    y_row = y_report.get("rows", [{}])[0].get("cells", []) if y_report.get("rows") else []
    yesterday_summary = {
        "earnings": round(float(y_row[0].get("value", 0)), 2) if y_row else 0,
        "rpm": round(float(y_row[1].get("value", 0)), 2) if y_row else 0,
        "impressions": int(float(y_row[2].get("value", 0))) if y_row else 0,
        "clicks": int(float(y_row[3].get("value", 0))) if y_row else 0,
        "ctr": round(float(y_row[4].get("value", 0)) * 100, 2) if y_row else 0,
    }

    # 28일 추이
    report = service.accounts().reports().generate(
        account=account_id,
        dateRange="CUSTOM",
        startDate_year=int(dates["start_28"][:4]),
        startDate_month=int(dates["start_28"][5:7]),
        startDate_day=int(dates["start_28"][8:10]),
        endDate_year=int(dates["yesterday"][:4]),
        endDate_month=int(dates["yesterday"][5:7]),
        endDate_day=int(dates["yesterday"][8:10]),
        dimensions=["DATE"],
        metrics=["ESTIMATED_EARNINGS", "PAGE_VIEWS_RPM", "IMPRESSIONS", "CLICKS"]
    ).execute()

    trend = []
    for r in report.get("rows", []):
        cells = r.get("cells", [])
        trend.append({
            "date": cells[0].get("value", "") if cells else "",
            "earnings": round(float(cells[1].get("value", 0)), 4) if len(cells) > 1 else 0,
            "rpm": round(float(cells[2].get("value", 0)), 2) if len(cells) > 2 else 0,
            "impressions": int(float(cells[3].get("value", 0))) if len(cells) > 3 else 0,
            "clicks": int(float(cells[4].get("value", 0))) if len(cells) > 4 else 0,
        })

    # 28일 합계
    total_earnings = sum(r["earnings"] for r in trend)
    total_impressions = sum(r["impressions"] for r in trend)
    total_clicks = sum(r["clicks"] for r in trend)
    avg_rpm = round(total_earnings / total_impressions * 1000, 2) if total_impressions > 0 else 0

    summary = {
        "earnings": round(total_earnings, 2),
        "rpm": avg_rpm,
        "impressions": total_impressions,
        "clicks": total_clicks,
    }

    return {"yesterday": yesterday_summary, "summary": summary, "trend": trend}


def main():
    creds = get_credentials()
    dates = get_dates()
    ga4_data = fetch_ga4(creds, dates)
    gsc_data = fetch_gsc(creds, dates)
    try:
        adsense_data = fetch_adsense(creds, dates)
    except Exception as e:
        print(f"AdSense 오류 (건너뜀): {e}")
        adsense_data = {"yesterday": {}, "summary": {}, "trend": []}

    output = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "yesterday": dates["yesterday"],
        "ga4": ga4_data,
        "gsc": gsc_data,
        "adsense": adsense_data,
    }

    os.makedirs("data", exist_ok=True)
    with open("data/dashboard.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("✅ data/dashboard.json 생성 완료")

if __name__ == "__main__":
    main()
