# Marketing Skills & MCP Servers Report for Claude Code

> Research date: April 1, 2026
> For brands: **Mount of Olives** | **My Cup Runneth Over** | **Emelia Catherine Cosmeceuticals**

---

## Tier 1 — Must-Install (High Impact, Mature)

### 1. coreyhaines31/marketingskills
- **Type:** Claude Code Skills (32 skills, 52 CLI tools)
- **Stars:** 17,916 | **Last Updated:** March 31, 2026
- **What it does:** Complete marketing skill suite — CRO, copywriting, SEO, analytics, growth engineering, ad creative generation, site architecture, AI SEO, revenue operations, sales enablement, churn prevention. Includes MCP tool integrations for GA4, Stripe, Mailchimp, Google Ads, Zapier, and more.
- **Install:**
  ```bash
  npx skills add coreyhaines31/marketingskills
  ```
  Or for Claude Code specifically:
  ```bash
  /plugin marketplace add coreyhaines31/marketingskills
  /plugin install marketing-skills
  ```
- **Brand fit:**
  - **All three brands** — copywriting, CRO, SEO, and content generation are universal needs
  - **Emelia Catherine Cosmeceuticals** — ad creative and conversion optimization for premium cosmeceutical positioning
  - **Mount of Olives / My Cup Runneth Over** — growth engineering and revenue operations for scaling

---

### 2. indranilbanerjee/digital-marketing-pro
- **Type:** Claude Code Plugin (115 commands, 25 agents, 67 MCP servers, 143 reference files)
- **Stars:** 36 | **Last Updated:** March 31, 2026
- **What it does:** The most comprehensive single marketing plugin. 16 modules covering strategy to execution: Technical SEO, Local SEO, Marketing Automation, Content Engine, Campaign Planning, SEO Audit, Predictive Intelligence, GEO Monitoring, Competitor Monitoring, Creative Intelligence. All commands use `/dm:` prefix. Includes human-in-the-loop approval for external actions.
- **Install:**
  ```bash
  claude plugin marketplace add github:indranilbanerjee/digital-marketing-pro
  claude plugin install digital-marketing-pro@digital-marketing-pro
  ```
- **Brand fit:**
  - **All three brands** — full-stack marketing automation with approval workflows
  - **Mount of Olives** — local SEO module for faith-based niche targeting
  - **Emelia Catherine Cosmeceuticals** — competitor monitoring and creative intelligence for cosmeceutical market positioning

---

### 3. alirezarezvani/claude-skills (Marketing Skill Pod)
- **Type:** Claude Code Skills (220+ skills across 9 domains; marketing pod has 35+ skills)
- **Stars:** Not listed (very active, v2.1.2)  | **Last Updated:** March 2026
- **What it does:** Marketing domain includes 7 pods: Content (8 skills), SEO (5), CRO (6), Channels (6), Growth (4), Intelligence (4), Sales (2). Also includes SEO Optimizer, 15+ content framework templates, social media guidelines, and content calendar.
- **Install:**
  ```bash
  npx ai-agent-skills install alirezarezvani/claude-skills/marketing-skill
  ```
  Or manually:
  ```bash
  git clone https://github.com/alirezarezvani/claude-skills.git
  cd claude-skills && bash scripts/install.sh
  ```
- **Brand fit:**
  - **All three brands** — broad coverage; content calendar and social media guidelines especially useful for multi-brand management

---

### 4. dataforseo/mcp-server-typescript
- **Type:** MCP Server
- **Stars:** 165 | **Last Updated:** March 31, 2026
- **What it does:** Full access to DataForSEO APIs — keyword research, SERP tracking, backlink analysis, competitor research, on-page SEO audits, domain analytics. The most mature SEO data MCP server available.
- **Install (remote — easiest):**
  ```bash
  claude mcp add --header "Authorization: Basic <base64_credentials>" --transport http dfs-mcp https://mcp.dataforseo.com/http
  ```
  Or local via NPM:
  ```bash
  claude mcp add dfs-mcp --env DATAFORSEO_USERNAME=<user> --env DATAFORSEO_PASSWORD=<pass> -- npx -y dataforseo-mcp-server
  ```
- **Requires:** DataForSEO API account (paid, has free trial)
- **Brand fit:**
  - **All three brands** — essential for keyword research, SERP tracking, and competitive analysis
  - **Emelia Catherine Cosmeceuticals** — competitor keyword gaps in the cosmeceutical niche
  - **Mount of Olives** — faith-based and olive oil keyword opportunity analysis

---

### 5. saurabhsharma2u/search-console-mcp
- **Type:** MCP Server
- **Stars:** 77 | **Last Updated:** March 30, 2026
- **What it does:** Connects to Google Search Console, Bing Webmaster Tools, and GA4. Pulls search analytics data, performance reports, and indexing status directly into Claude.
- **Install:**
  ```bash
  claude mcp add search-console -- npx -y search-console-mcp
  ```
- **Requires:** Google/Bing API credentials
- **Brand fit:**
  - **All three brands** — monitor organic search performance, find indexing issues, track keyword rankings

---

## Tier 2 — High Value (Specific Use Cases)

### 6. GeLi2001/shopify-mcp
- **Type:** MCP Server
- **Stars:** 178 | **Last Updated:** March 31, 2026
- **What it does:** Full Shopify Admin API integration — manage products, orders, customers, inventory, collections, and more directly from Claude.
- **Install:**
  ```bash
  claude mcp add shopify-mcp --env SHOPIFY_ACCESS_TOKEN=<token> --env SHOPIFY_STORE_URL=<url> -- npx -y shopify-mcp
  ```
- **Brand fit:**
  - **My Cup Runneth Over** — if using Shopify for drinkware/merchandise
  - **Emelia Catherine Cosmeceuticals** — Shopify store management for DTC cosmeceutical sales
  - **Mount of Olives** — product and inventory management

---

### 7. callobuzz/cob-shopify-mcp
- **Type:** MCP Server (production-grade)
- **Stars:** 9 | **Last Updated:** March 31, 2026
- **What it does:** Production-grade Shopify Admin GraphQL API server with 49+ tools, YAML-extensible, dual auth, Docker-ready. More comprehensive than the basic Shopify MCP above.
- **Install:**
  ```bash
  git clone https://github.com/callobuzz/cob-shopify-mcp.git
  cd cob-shopify-mcp && npm install && npm run build
  claude mcp add cob-shopify -- node /path/to/cob-shopify-mcp/dist/index.js
  ```
- **Brand fit:** Same as #6, but better for production use with multiple Shopify stores

---

### 8. profplum700/etsy-mcp-server
- **Type:** MCP Server
- **Stars:** 9 | **Last Updated:** January 2026
- **What it does:** Etsy API v3 integration — manage listings, upload products, edit variants, pull shop analytics.
- **Install:**
  ```bash
  git clone https://github.com/profplum700/etsy-mcp-server.git
  cd etsy-mcp-server && npm install && npm run build
  claude mcp add etsy -- node /path/to/etsy-mcp-server/dist/index.js
  ```
- **Requires:** Etsy API key
- **Brand fit:**
  - **My Cup Runneth Over** — drinkware/mug listings on Etsy
  - **Mount of Olives** — faith-based product listings on Etsy

---

### 9. georgejeffers/etsy-mcp-server
- **Type:** MCP Server
- **Stars:** 8 | **Last Updated:** March 29, 2026
- **What it does:** Upload listings, edit listings, manage Etsy shop via LLM through MCP. More recently updated than profplum700's version.
- **Install:**
  ```bash
  git clone https://github.com/georgejeffers/etsy-mcp-server.git
  cd etsy-mcp-server && npm install
  claude mcp add etsy-jeffers -- node /path/to/etsy-mcp-server/index.js
  ```
- **Brand fit:** Same as #8

---

### 10. mattcoatsworth/AmazonSeller-mcp-server
- **Type:** MCP Server
- **Stars:** 37 | **Last Updated:** March 27, 2026
- **What it does:** Amazon Seller Central API integration — manage listings, inventory, orders, and reporting for Amazon marketplace sellers.
- **Install:**
  ```bash
  git clone https://github.com/mattcoatsworth/AmazonSeller-mcp-server.git
  cd AmazonSeller-mcp-server && npm install
  claude mcp add amazon-seller -- node /path/to/AmazonSeller-mcp-server/index.js
  ```
- **Requires:** Amazon SP-API credentials
- **Brand fit:**
  - **Mount of Olives** — olive oil products on Amazon
  - **Emelia Catherine Cosmeceuticals** — cosmeceutical product listings on Amazon
  - **My Cup Runneth Over** — drinkware on Amazon

---

### 11. KuudoAI/amazon_ads_mcp
- **Type:** MCP Server
- **Stars:** 32 | **Last Updated:** March 30, 2026
- **What it does:** Amazon Advertising API — manage Sponsored Products, Sponsored Brands, campaign analytics, keyword targeting, and bid optimization.
- **Install:**
  ```bash
  pip install amazon-ads-mcp
  claude mcp add amazon-ads -- python -m amazon_ads_mcp
  ```
- **Requires:** Amazon Ads API credentials
- **Brand fit:**
  - **All three brands** — PPC campaign management on Amazon

---

### 12. AdsMCP/tiktok-ads-mcp-server
- **Type:** MCP Server
- **Stars:** 25 | **Last Updated:** March 29, 2026
- **What it does:** TikTok Marketing API integration — create and manage ad campaigns, audiences, creatives, and pull performance analytics.
- **Install:**
  ```bash
  git clone https://github.com/AdsMCP/tiktok-ads-mcp-server.git
  cd tiktok-ads-mcp-server && pip install -r requirements.txt
  claude mcp add tiktok-ads -- python /path/to/server.py
  ```
- **Requires:** TikTok Ads API access
- **Brand fit:**
  - **Emelia Catherine Cosmeceuticals** — TikTok is critical for beauty/cosmeceutical marketing
  - **My Cup Runneth Over** — trending drinkware/lifestyle content on TikTok

---

### 13. amekala/ads-mcp (Multi-Platform Ads)
- **Type:** MCP Server
- **Stars:** 25 | **Last Updated:** March 31, 2026
- **What it does:** Unified ad campaign management across Google Ads, Meta Ads, LinkedIn Ads, and TikTok Ads. 100+ tools for campaign creation, performance analysis, keyword research, and budget optimization.
- **Install:**
  ```bash
  git clone https://github.com/amekala/ads-mcp.git
  cd ads-mcp && bash install.sh
  claude mcp add ads-mcp -- /path/to/ads-mcp/start.sh
  ```
- **Brand fit:**
  - **All three brands** — single tool for all paid advertising channels

---

### 14. danielsogl/lighthouse-mcp-server
- **Type:** MCP Server
- **Stars:** 52 | **Last Updated:** March 31, 2026
- **What it does:** Google Lighthouse integration — performance, accessibility, SEO, and security audits with 13+ tools. Essential for technical SEO and page speed optimization.
- **Install:**
  ```bash
  claude mcp add lighthouse -- npx -y lighthouse-mcp-server
  ```
- **Brand fit:**
  - **All three brands** — audit and optimize all brand websites for Core Web Vitals and SEO

---

### 15. DojoCodingLabs/remotion-superpowers
- **Type:** Claude Code Plugin (5 MCP servers, 13 commands)
- **Stars:** 12 | **Last Updated:** March 29, 2026
- **What it does:** Full video production studio — AI voiceovers, music, stock footage, image/video generation, TikTok captions, 3D transitions, and AI review loop. Perfect for creating social media video content.
- **Install:**
  ```bash
  git clone https://github.com/DojoCodingLabs/remotion-superpowers.git
  # Follow setup instructions in README
  ```
- **Brand fit:**
  - **Emelia Catherine Cosmeceuticals** — TikTok/Reels product demo videos
  - **My Cup Runneth Over** — lifestyle/unboxing shorts
  - **Mount of Olives** — brand storytelling videos

---

## Tier 3 — Specialized / Niche Tools

### 16. apify/apify-mcp-server
- **Type:** MCP Server
- **Stars:** 986 | **Last Updated:** March 31, 2026
- **What it does:** Access thousands of ready-made scrapers for social media, search engines, e-commerce sites. Extract product data, reviews, competitor pricing.
- **Install:**
  ```bash
  claude mcp add apify --env APIFY_TOKEN=<token> -- npx -y apify-mcp-server
  ```
- **Requires:** Apify account (free tier available)
- **Brand fit:** **All brands** — competitive research, price monitoring, review scraping

---

### 17. mrgoonie/seo-insights-mcp-server
- **Type:** MCP Server
- **Stars:** 29 | **Last Updated:** February 2026
- **What it does:** SEO tools for backlinks, keyword research, and traffic analysis.
- **Install:**
  ```bash
  git clone https://github.com/mrgoonie/seo-insights-mcp-server.git
  cd seo-insights-mcp-server && npm install && npm run build
  claude mcp add seo-insights -- node /path/to/dist/index.js
  ```
- **Brand fit:** **All brands** — backlink and traffic analysis

---

### 18. mattcoatsworth/Klaviyo-MCP-Server
- **Type:** MCP Server
- **Stars:** 6 | **Last Updated:** March 27, 2026
- **What it does:** Klaviyo email marketing API — manage lists, segments, campaigns, flows, and templates.
- **Install:**
  ```bash
  git clone https://github.com/mattcoatsworth/Klaviyo-MCP-Server.git
  cd Klaviyo-MCP-Server && npm install
  claude mcp add klaviyo -- node /path/to/index.js
  ```
- **Requires:** Klaviyo API key
- **Brand fit:**
  - **Emelia Catherine Cosmeceuticals** — email flows for skincare routines, product launches
  - **All brands** — email marketing automation

---

### 19. damientilman/mailchimp-mcp-server
- **Type:** MCP Server
- **Stars:** 4 | **Last Updated:** March 26, 2026
- **What it does:** Full Mailchimp control — 53 tools for audiences, campaigns, automations, and more.
- **Install:**
  ```bash
  pip install mailchimp-mcp-server
  claude mcp add mailchimp -- python -m mailchimp_mcp_server
  ```
- **Requires:** Mailchimp API key
- **Brand fit:** **All brands** — newsletter and email marketing automation

---

### 20. lofder/dsers-mcp-product
- **Type:** MCP Server
- **Stars:** 22 | **Last Updated:** March 29, 2026
- **What it does:** Automate DSers product import, bulk edit variants, push to Shopify/Wix/WooCommerce. Supports AliExpress, Alibaba, 1688 sourcing.
- **Install:**
  ```bash
  git clone https://github.com/lofder/dsers-mcp-product.git
  cd dsers-mcp-product && npm install
  claude mcp add dsers -- node /path/to/index.js
  ```
- **Brand fit:**
  - **My Cup Runneth Over** — dropshipping/product sourcing for drinkware
  - **Mount of Olives** — product sourcing from international suppliers

---

### 21. metricool/mcp-metricool
- **Type:** MCP Server
- **Stars:** 31 | **Last Updated:** March 23, 2026
- **What it does:** Social media metrics and campaign data from Metricool — cross-platform analytics for Instagram, TikTok, Twitter, Facebook, YouTube.
- **Install:**
  ```bash
  pip install mcp-metricool
  claude mcp add metricool -- python -m mcp_metricool
  ```
- **Requires:** Metricool API token
- **Brand fit:** **All brands** — unified social media analytics dashboard

---

### 22. local-falcon/mcp
- **Type:** MCP Server
- **Stars:** 16 | **Last Updated:** March 30, 2026
- **What it does:** Local SEO — geo-grid rank tracking, campaign management, competitor analysis via Local Falcon's platform.
- **Install:**
  ```bash
  claude mcp add local-falcon -- npx -y @local-falcon/mcp
  ```
- **Requires:** Local Falcon API key
- **Brand fit:**
  - **Mount of Olives** — local SEO for brick-and-mortar or local distribution
  - **Emelia Catherine Cosmeceuticals** — local visibility for retail locations

---

### 23. metehan777/alsoasked-mcp
- **Type:** MCP Server
- **Stars:** 14 | **Last Updated:** March 28, 2026
- **What it does:** AlsoAsked integration — discover People Also Ask questions for any keyword. Excellent for AEO (Answer Engine Optimization) and FAQ schema content.
- **Install:**
  ```bash
  claude mcp add alsoasked -- npx -y alsoasked-mcp
  ```
- **Requires:** AlsoAsked API key
- **Brand fit:**
  - **All brands** — AEO optimization, FAQ content generation, schema markup planning

---

### 24. supadata-ai/mcp
- **Type:** MCP Server
- **Stars:** 41 | **Last Updated:** March 30, 2026
- **What it does:** Video & web scraping — YouTube transcripts, TikTok data extraction, web content scraping. Great for competitor video research and content repurposing.
- **Install:**
  ```bash
  claude mcp add supadata -- npx -y @supadata/mcp
  ```
- **Brand fit:**
  - **Emelia Catherine Cosmeceuticals** — scrape competitor TikTok/YouTube beauty content for strategy
  - **All brands** — content research and repurposing

---

### 25. XPOZpublic/xpoz-mcp
- **Type:** MCP Server
- **Stars:** 7 | **Last Updated:** March 31, 2026
- **What it does:** Search Twitter, Instagram, Reddit & TikTok from AI agents. 1.5B+ posts indexed. Social listening and trend analysis.
- **Install:**
  ```bash
  claude mcp add xpoz -- npx -y xpoz-mcp
  ```
- **Brand fit:** **All brands** — social listening, trend spotting, brand mention monitoring

---

## Brand-Specific Recommendations

### Mount of Olives (Faith-based / Olive Oil Products)
| Priority | Tool | Why |
|----------|------|-----|
| 1 | marketingskills | Copywriting, SEO, CRO for niche market |
| 2 | digital-marketing-pro | Local SEO module, content engine |
| 3 | DataForSEO MCP | Keyword research for faith-based niche |
| 4 | Etsy MCP | Manage Etsy listings for artisanal products |
| 5 | Amazon Seller MCP | Amazon marketplace management |
| 6 | AlsoAsked MCP | AEO — "People Also Ask" for faith/wellness queries |
| 7 | Local Falcon MCP | Local SEO tracking |

### My Cup Runneth Over (Drinkware / Lifestyle)
| Priority | Tool | Why |
|----------|------|-----|
| 1 | marketingskills | CRO for e-commerce, ad creative generation |
| 2 | Shopify MCP | Store management |
| 3 | Etsy MCP | Etsy shop management |
| 4 | TikTok Ads MCP | Viral drinkware marketing on TikTok |
| 5 | Remotion Superpowers | Product video creation for social |
| 6 | Amazon Seller MCP | Amazon product listings |
| 7 | Apify MCP | Competitor pricing and review scraping |

### Emelia Catherine Cosmeceuticals (Premium Beauty/Skincare)
| Priority | Tool | Why |
|----------|------|-----|
| 1 | digital-marketing-pro | Full marketing stack with competitor intelligence |
| 2 | marketingskills | Ad creative, CRO, copywriting |
| 3 | TikTok Ads MCP | Beauty/skincare is massive on TikTok |
| 4 | Shopify MCP | DTC e-commerce management |
| 5 | Klaviyo MCP | Email flows for skincare routines |
| 6 | DataForSEO MCP | Cosmeceutical keyword gaps |
| 7 | Lighthouse MCP | Technical SEO for brand website |
| 8 | Supadata MCP | Scrape competitor beauty content |

---

## Quick Reference: All Install Commands

```bash
# === TIER 1: MUST INSTALL ===

# Marketing Skills (Claude Code Skills)
npx skills add coreyhaines31/marketingskills

# Digital Marketing Pro (Claude Code Plugin)
claude plugin marketplace add github:indranilbanerjee/digital-marketing-pro
claude plugin install digital-marketing-pro@digital-marketing-pro

# Claude Skills - Marketing Pod
npx ai-agent-skills install alirezarezvani/claude-skills/marketing-skill

# DataForSEO MCP (remote)
claude mcp add --header "Authorization: Basic <base64_creds>" --transport http dfs-mcp https://mcp.dataforseo.com/http

# Search Console MCP
claude mcp add search-console -- npx -y search-console-mcp

# === TIER 2: HIGH VALUE ===

# Shopify MCP
claude mcp add shopify-mcp --env SHOPIFY_ACCESS_TOKEN=<token> --env SHOPIFY_STORE_URL=<url> -- npx -y shopify-mcp

# Lighthouse MCP
claude mcp add lighthouse -- npx -y lighthouse-mcp-server

# Multi-Platform Ads MCP
git clone https://github.com/amekala/ads-mcp.git

# TikTok Ads MCP
git clone https://github.com/AdsMCP/tiktok-ads-mcp-server.git

# Amazon Seller MCP
git clone https://github.com/mattcoatsworth/AmazonSeller-mcp-server.git

# Amazon Ads MCP
pip install amazon-ads-mcp

# Etsy MCP
git clone https://github.com/georgejeffers/etsy-mcp-server.git

# Apify MCP (web scraping)
claude mcp add apify --env APIFY_TOKEN=<token> -- npx -y apify-mcp-server

# === TIER 3: SPECIALIZED ===

# Klaviyo (email marketing)
git clone https://github.com/mattcoatsworth/Klaviyo-MCP-Server.git

# Mailchimp (email marketing)
pip install mailchimp-mcp-server

# Metricool (social analytics)
pip install mcp-metricool

# AlsoAsked (AEO/PAA)
claude mcp add alsoasked -- npx -y alsoasked-mcp

# Local Falcon (local SEO)
claude mcp add local-falcon -- npx -y @local-falcon/mcp

# Supadata (video/web scraping)
claude mcp add supadata -- npx -y @supadata/mcp

# XPOZ (social listening)
claude mcp add xpoz -- npx -y xpoz-mcp

# Remotion Superpowers (video production)
git clone https://github.com/DojoCodingLabs/remotion-superpowers.git
```

---

## Sources

- [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills)
- [indranilbanerjee/digital-marketing-pro](https://github.com/indranilbanerjee/digital-marketing-pro)
- [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills)
- [dataforseo/mcp-server-typescript](https://github.com/dataforseo/mcp-server-typescript)
- [saurabhsharma2u/search-console-mcp](https://github.com/saurabhsharma2u/search-console-mcp)
- [GeLi2001/shopify-mcp](https://github.com/GeLi2001/shopify-mcp)
- [callobuzz/cob-shopify-mcp](https://github.com/callobuzz/cob-shopify-mcp)
- [profplum700/etsy-mcp-server](https://github.com/profplum700/etsy-mcp-server)
- [georgejeffers/etsy-mcp-server](https://github.com/georgejeffers/etsy-mcp-server)
- [mattcoatsworth/AmazonSeller-mcp-server](https://github.com/mattcoatsworth/AmazonSeller-mcp-server)
- [KuudoAI/amazon_ads_mcp](https://github.com/KuudoAI/amazon_ads_mcp)
- [AdsMCP/tiktok-ads-mcp-server](https://github.com/AdsMCP/tiktok-ads-mcp-server)
- [amekala/ads-mcp](https://github.com/amekala/ads-mcp)
- [danielsogl/lighthouse-mcp-server](https://github.com/danielsogl/lighthouse-mcp-server)
- [DojoCodingLabs/remotion-superpowers](https://github.com/DojoCodingLabs/remotion-superpowers)
- [apify/apify-mcp-server](https://github.com/apify/apify-mcp-server)
- [mrgoonie/seo-insights-mcp-server](https://github.com/mrgoonie/seo-insights-mcp-server)
- [mattcoatsworth/Klaviyo-MCP-Server](https://github.com/mattcoatsworth/Klaviyo-MCP-Server)
- [damientilman/mailchimp-mcp-server](https://github.com/damientilman/mailchimp-mcp-server)
- [lofder/dsers-mcp-product](https://github.com/lofder/dsers-mcp-product)
- [metricool/mcp-metricool](https://github.com/metricool/mcp-metricool)
- [local-falcon/mcp](https://github.com/local-falcon/mcp)
- [metehan777/alsoasked-mcp](https://github.com/metehan777/alsoasked-mcp)
- [supadata-ai/mcp](https://github.com/supadata-ai/mcp)
- [XPOZpublic/xpoz-mcp](https://github.com/XPOZpublic/xpoz-mcp)
- [jshorwitz/awesome-agentic-advertising](https://github.com/jshorwitz/awesome-agentic-advertising)
- [DataForSEO Install Guide](https://dataforseo.com/help-center/3-ways-to-install-dataforseo-mcp-with-claude-code)
