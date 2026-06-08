# yangchangho.com 블로그 대시보드


🔗 **대시보드 URL:** https://changho4.github.io/wp-blog-dashboard
GA4 + Google Search Console 데이터를 GitHub Actions로 매일 자동 수집해서 GitHub Pages로 보여주는 대시보드입니다.

## 구조
```
.
├── index.html                        # 대시보드 UI
├── data/
│   └── dashboard.json                # 자동 생성되는 데이터 파일
├── scripts/
│   └── fetch_data.py                 # GA4/GSC 데이터 수집 스크립트
├── requirements.txt                  # Python 패키지
└── .github/workflows/
    └── update-data.yml               # 매일 오전 10시(KST) 자동 실행
```

## GitHub Secrets 설정
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`
- `GA4_PROPERTY_ID`
- `GSC_SITE_URL`
