<div align="center">

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=700&size=32&pause=1000&color=B02025&center=true&vCenter=true&width=600&lines=FunLab+SEO+Dashboard;AI-Powered+SEO+Intelligence;Outrank+Your+Competitors" alt="Typing SVG" />

<br/>

[![Live App](https://img.shields.io/badge/🚀%20Live%20App-suryaseodashboard.streamlit.app-B02025?style=for-the-badge&logoColor=white)](https://suryaseodashboard.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Gemini AI](https://img.shields.io/badge/Gemini%20AI-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://aistudio.google.com)
[![License](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

<br/>

> **Paste a URL. Pick a keyword. Get a full competitive SEO intelligence report in minutes — powered by Google data and Gemini AI.**

<br/>

<img width="90%" src="https://raw.githubusercontent.com/Suuuryaa/seo-analysis-venue-dashboard/main/assets/demo.png" alt="Dashboard Preview" onerror="this.style.display='none'" />

</div>

---

## ✨ What It Does

FunLab SEO Dashboard gives any business owner or marketer a **complete SEO picture** — no agency required. Enter your website URL and a target keyword, and the dashboard:

1. **Scrapes and scores your page** against 15+ SEO signals
2. **Finds your real competitors** using Google SERP + Gemini AI
3. **Benchmarks you side-by-side** against each competitor
4. **Generates an AI executive report** with specific actions to close the gap

---

## 🗂 Feature Overview

<table>
<tr>
<td width="50%">

### 🔍 SEO Analysis
- Title, meta description & H1 extraction
- Keyword density & word count scoring
- Internal & external link analysis
- Image ALT tag coverage
- HTTPS & Schema markup detection
- Google PageSpeed integration

</td>
<td width="50%">

### 🥇 Competitor Intelligence
- Gemini AI identifies real direct competitors from URL context
- Full SERP scraping via Serper API
- Filters out directories, forums, social media automatically
- Side-by-side SEO score benchmarking
- Gap analysis vs best competitor

</td>
</tr>
<tr>
<td width="50%">

### 📊 Benchmarking & Scoring
- SEO score (0–100) across all venues
- Score band classification (Weak / Fair / Good / Strong)
- Word count, keyword count, link count comparison
- Interactive bar chart leaderboard

</td>
<td width="50%">

### 🤖 AI Executive Summary
- Full written report by Gemini AI
- Strengths, weaknesses, keyword analysis
- Technical SEO issues explained plainly
- 5-point priority action plan
- Written for non-technical business owners

</td>
</tr>
<tr>
<td width="50%">

### 🌍 GEO Score
- E-E-A-T signal analysis
- Structured data detection
- Geographic relevance signals
- Local SEO indicators

</td>
<td width="50%">

### 🔑 Keyword Opportunities
- Missing keywords vs competitors
- High-frequency competitor terms
- Keyword placement analysis
- Content gap identification

</td>
</tr>
</table>

---

## 🖥 Dashboard Tabs

| Tab | What You See |
|-----|-------------|
| **Overview** | SEO score, score band, keyword placement, leaderboard chart |
| **Technical SEO** | Pass/fail tiles for HTTPS, schema, alt text, PageSpeed |
| **Content Analysis** | Word count, keyword density, internal links breakdown |
| **GEO Score** | E-E-A-T signals, crawler accessibility, structured data |
| **Recommendations** | Prioritised action list with impact explanations |
| **AI Report** | Full written executive summary by Gemini AI |

---

## ⚙️ Tech Stack

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-3F4F75?style=flat-square&logo=plotly&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Gemini%20AI-4285F4?style=flat-square&logo=google&logoColor=white)
![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup4-43853D?style=flat-square&logo=python&logoColor=white)
![Redis](https://img.shields.io/badge/Upstash%20Redis-DC382D?style=flat-square&logo=redis&logoColor=white)

</div>

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit + custom HTML/CSS |
| AI | Google Gemini (REST API, auto model discovery) |
| Search Data | Serper API (Google SERP) |
| Performance | Google PageSpeed Insights API |
| Scraping | BeautifulSoup4, Scrapling, lxml |
| Rate Limiting | Upstash Redis (global shared pool) |
| Uptime | GitHub Actions cron (every 30 min) |

---

## 🚀 Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/Suuuryaa/seo-analysis-venue-dashboard.git
cd seo-analysis-venue-dashboard

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API keys
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit secrets.toml with your keys

# 5. Run
streamlit run app.py
```

---

## 🔑 Required API Keys

| Key | Where to Get | Required? |
|-----|-------------|-----------|
| `GEMINI_API_KEY` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | ✅ Yes |
| `SERPER_API_KEY` | [serper.dev](https://serper.dev) | ✅ Yes |
| `PAGESPEED_API_KEY` | [Google Cloud Console](https://console.cloud.google.com) | Optional |
| `ADMIN_PASSWORD` | Set your own | Optional |
| `UPSTASH_REDIS_REST_URL` | [upstash.com](https://upstash.com) | Optional |
| `UPSTASH_REDIS_REST_TOKEN` | [upstash.com](https://upstash.com) | Optional |

---

## 🌐 Deploy to Streamlit Cloud

1. Fork this repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo → set `app.py` as main file
4. Add your API keys in **App settings → Secrets**
5. Deploy ✅

---

<div align="center">

**Built with ❤️ by [Suuuryaa](https://github.com/Suuuryaa)**

[![Live Demo](https://img.shields.io/badge/Try%20It%20Live-B02025?style=for-the-badge&logo=streamlit&logoColor=white)](https://suryaseodashboard.streamlit.app)

</div>
