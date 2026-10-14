# Coverflex Growth Ops case study, Part 2 (Francisco Faria)

## 1. Building a unified company database (PT, ES, IT, micro-businesses included)

**Base: registry data, not LinkedIn.** LinkedIn only covers companies that are online, mostly the bigger ones. Every company, even a one-person café, exists in the official registries.
- **Infobel PRO** as the backbone: it aggregates official registries and directories across Europe, including Portugal, Spain and Italy, with micro-businesses, addresses, activity codes and often phone numbers. Available via API.
- **Country sources to fill gaps:** Portugal: registo comercial data (eInforma, Racius). Spain: BORME, the daily Registro Mercantil gazette (Informa, Axesor). Italy: Registro Imprese (InfoCamere, Cerved/Atoka).
- **Google Maps** for micro-businesses: phone, category, opening status, reviews. Many have no website but are on Maps.
- **LinkedIn** as one enrichment source among others, not the base.

**Unifying it**
- One master table keyed on **country + tax ID** (NIF, CIF, Partita IVA). Dedupe on tax ID first, then fuzzy match on name + address for sources without it. Activity codes (CAE, CNAE, ATECO) mapped to one industry list, size bands normalised.
- **Clay as the enrichment layer**, with a waterfall per field, as I do at Bizzy: domain, headcount, decision makers, emails (Prospeo, verified with ZeroBounce), phones. Each field keeps its source and a confidence score.
- Full TAM stored in a table or warehouse; **only ICP-fit accounts synced to HubSpot** with n8n, so the CRM stays clean.
- Refresh: full refresh monthly; new incorporations daily (they are also a signal).

**Micro-businesses not active on the web**
- They are in Infobel and the registries (existence, activity, address, legal representative), and usually on Google Maps (phone).
- Reach them through channels that already serve them: **accountants** (one accountant handles dozens of micro-companies, and Coverflex already integrates with Primavera and PHC), business associations and chambers of commerce.
- A "reachability" field (email, phone, none) decides the channel for each account.
- GDPR: sole traders' data is personal data, so legitimate interest assessment, clear opt-out, source kept for every record.

## 2. Scaling outbound

### LinkedIn (about 20 messages per profile per day)
- **Email first, LinkedIn second.** Email carries the volume. LinkedIn slots go only to **warm accounts** (engaged, replied, visited the site) or **high ICP fit**. With that filter, 20 a day per profile is enough.
- **More senders, not more per sender:** BDRs, AEs and local market people each send within safe limits, after warming up their accounts, through Lemlist's LinkedIn steps (or a multi-account tool like HeyReach), with random delays.
- **Orchestration:** Clay builds and enriches the lists, Lemlist runs the multichannel sequences, n8n keeps HubSpot in sync (for example, when an opportunity is created every contact at that company leaves their sequences, which the native integration doesn't do). Claude agents, run as routines on GitHub, decide who deserves a LinkedIn touch and draft the personalisation; a reply bot triages answers and creates tasks for sales.
- **Keeping accounts safe:** high acceptance rate through good targeting, withdraw invites older than about 3 weeks, no scraping extensions, human-like pacing.
- **Alternative engagement tactics** (they don't use the invite limit):
  - Warm up before connecting: profile visit, follow, a genuine comment on their posts.
  - Connect without a note, message after they accept; voice notes for warm accounts.
  - InMail to open profiles.
  - LinkedIn ads on the TAM list and retargeting of people who engage (at Bizzy I feed LinkedIn ad engagement into HubSpot with Fibbler and use it as a signal).
  - Content from founders and employees, so the name is known before the message arrives.
  - Webinars and events as a reason to reach out (at Bizzy I organised webinars with about 500 attendees).
  - A phone call from the new BDR team for the warmest accounts.

### WhatsApp
**Rules first:** business-initiated WhatsApp needs opt-in on the official API, and cold messages to personal numbers risk complaints and the number being banned. So I'd use it for warm and opted-in contacts, and carefully for public business numbers of micro-businesses (the number listed on Google Maps), one to one, after a legal check per country.

1. **Finding the decision maker and the number:** micro-businesses: the owner or legal representative (registry) and the business number (Infobel, Google Maps, website). Bigger companies: HR or Finance lead found in Clay, mobile number through Clay's phone waterfall (providers with good EU coverage), then validated. Lemlist enrichment as a backup. Claude orchestrates and checks the result.
2. **Personalised messages:** Claude writes each message from everything we know: research on the company, on the person, the signal that triggered it, and **similar companies we already talked to** (from HubSpot and Lemlist history), for example "other hotels in the Algarve use Coverflex for…". Short, in the local language, asking permission first. A person reviews a sample before scaling.
3. **Tools and process:** WhatsApp Business Platform through HubSpot's integration or a provider (Twilio, 360dialog); n8n orchestrates; replies land in the HubSpot inbox with a task for the BDR; a reply bot sorts interested, not now and opt-out; opt-outs are applied immediately. Separate number, start small, watch Meta's quality rating.
4. **Alternative tactics:** click-to-WhatsApp ads (the prospect starts the conversation), WhatsApp follow-up after a phone call, QR codes at events.

## 3. Outbound buying signals

**1. Hiring in HR, People or Finance (or a hiring surge)**
- How: job boards and careers pages, via Clay, Apify and Claude scraping (at Bizzy I built my own hiring-signal agent because no tool did exactly what we needed). Trigger when a company opens an HR/People/Finance role or several roles in a month.
- Angle: competing for talent, flexible compensation, and the job-offer tool where candidates see their net salary. I'd **A/B test mentioning the signal vs not mentioning it**: sometimes the signal works better just for prioritising the lead than in the message itself.

**2. Champion moved / new HR or Finance leader**
- How: a Claude routine on GitHub that tracks job changes of Coverflex's champions (HR and Finance contacts of current clients), like the one I run at Bizzy for about 2,000 won-deal champions, plus new HR/Finance leaders joining ICP companies. Clay for enrichment, Lemlist for the sequence, AI filter for fake moves (acquisitions, internal moves).
- Angle: "Congrats on the new role. You used and vouched for Coverflex at X, happy to help you set it up at Y." For new leaders: they usually review benefits and payroll tools in their first 90 days.

**3. High-intent website visits**
- How: companies visiting pricing, the meal-card savings simulator or the job-offer page, identified with HubSpot plus a reverse-IP tool, and known contacts' activity.
- Angle: help, not surprise: "happy to run the numbers for a team of your size".

**4. Pay Transparency Directive exposure**
- How: companies above the reporting threshold (100+ employees) from Infobel/registry headcount bands, plus job ads published without a salary range (scraped like signal 1).
- Angle: a compliance deadline. Coverflex's pay transparency product (gap analysis and reports) and job offers with pay ranges.

**5. Funding round or fast headcount growth**
- How: funding news (Crunchbase, Dealroom, local press) and headcount growth over 3-6 months, both through Clay.
- Angle: a growing team and new budget: benefits that scale with the company and help retention.

**Selection: why these five.** I scored each signal on strength of intent (does it point to a buying moment?), freshness (can we act within days?), reach (enough volume across PT, ES and IT), ease of capture (cost and reliability) and fit with a Coverflex product (each maps to one: meal and benefits, job offers, pay transparency). New incorporations nearly made the list: huge reach for micro-businesses, but weak intent, better worked through accountants.

**Ranking**
1. Champion moved / new HR or Finance leader
2. High-intent website visits
3. Hiring in HR/People/Finance
4. Pay transparency exposure
5. Funding or growth

**Pilot first: champion moved / new HR or Finance leader.** Strongest intent, enough volume across three countries when new leaders are included, cheap to capture, and I've already built it.

**Validation**
- **Metric:** meetings booked per contacted account. Positive reply rate as the early read, SQLs to confirm.
- **Baseline:** the same ICP segment in the current cold sequences, same channels, same period.
- **Time window:** 8 weeks of sending, plus about 4 weeks to see meetings turn into SQLs.
- **Sample:** about 300 contacted accounts in the pilot and 300 in the baseline. That's enough to tell a 3% from an 8% positive reply rate with reasonable confidence. Meetings alone would need much more volume, so replies are the early signal and meetings/SQLs the confirmation.
- **Decision:** scale if the meeting rate is at least 2x the baseline and the cost per SQL is not higher. Drop or rework (message, titles) if it's below 1.3x after the full sample. In between: one more iteration on the message, then decide.
