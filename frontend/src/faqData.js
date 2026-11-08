// FAQ content shared by the homepage section (first few) and the /faq page.
// Keep answers true to how the product works today.

export const FAQ_GROUPS = [
  {
    id: 'getting-started',
    title: 'Getting started',
    items: [
      {
        q: 'What does RankSpy AI check?',
        a: 'It reads your page the way a search engine does and runs 30+ on-page checks: title and meta description, headings, content and keyword use, links, images, technical setup and whether Google can index the page. You get a score out of 100 and a plain-English to-do list, starting with the fixes that matter most.',
      },
      {
        q: 'How long does a scan take?',
        a: 'A page scan usually takes 5 to 15 seconds. JS rendering takes longer because it opens the page in a real browser. A competitor comparison takes about a minute, because it scans each competitor and checks real Google positions.',
      },
      {
        q: 'Do I need an account?',
        a: 'No. Paste a page address and, optionally, the keyword you want to rank for. There is nothing to sign up for.',
      },
      {
        q: 'Does it work for any website?',
        a: 'It works for any public web page. If your site is built with JavaScript (React, Wix, Squarespace and similar), switch on JS rendering so we read the page as visitors see it. Some sites block automated checks; we tell you when that happens.',
      },
    ],
  },
  {
    id: 'free-use',
    title: 'Free use and limits',
    items: [
      {
        q: 'Is it free?',
        a: 'Yes. Each visitor gets 3 free page scans and 1 competitor comparison a day. Rescanning a page you already checked today, to see if your fixes worked, is free twice per page.',
      },
      {
        q: 'When do my free scans come back?',
        a: 'Every day at midnight UTC. The scan form shows the exact time in your own time zone.',
      },
      {
        q: 'Why does it say I have used my scans when I have not?',
        a: 'Free scans are counted per internet connection. If you share one (an office, university or some mobile networks), someone else on it may have used them. Try again after the reset, or add your own free keys.',
      },
      {
        q: 'Can I get more scans?',
        a: 'Yes. Add your own free Gemini and Serper API keys in the "Add your own keys" tab for up to 100 scans a day. Your keys are used only for your requests and are never stored.',
      },
    ],
  },
  {
    id: 'scores',
    title: 'Scores and results',
    items: [
      {
        q: 'What is the SEO score?',
        a: 'A score from 0 to 100 for how well the page is set up for its keyword. 70 and above is a strong base, 40 to 69 needs work, and below 40 has serious issues to fix first. It is an estimate from the page itself, not a guarantee of rankings.',
      },
      {
        q: 'How do I improve my score?',
        a: 'Work through the to-do list from the top: fixes are sorted by impact (Fix first, Fix next, Nice to have). The fix-it tools can write a better title and meta description, generate structured data (schema) and check your local SEO details.',
      },
      {
        q: 'Why is my score different from other SEO tools?',
        a: 'Every tool weighs different checks. RankSpy scores on-page factors for your keyword with fixed rules, so the same page always gets the same score. It does not use backlinks or traffic estimates.',
      },
      {
        q: 'Are the Google positions real?',
        a: 'Yes. They come from a live Google search for your keyword in your site\'s country (top 30 results). Google results change through the day, so a position can move a little between checks.',
      },
    ],
  },
  {
    id: 'competitors',
    title: 'Competitor comparison',
    items: [
      {
        q: 'How are my competitors chosen?',
        a: 'AI names your business\'s main rivals in your home market (Woolworths is compared with New World, PAK\'nSAVE and Kmart in New Zealand; Tesco with Sainsbury\'s and Asda in the UK). We keep only sites that are online, then check each one\'s real Google position for your keyword and compare their pages with yours.',
      },
      {
        q: 'Why does a competitor show "Google check" instead of a score?',
        a: 'Some big sites block automated checks. For those we never try to get around the block; instead we show Google\'s own SEO check of their page and whether your keyword is in the title Google shows. That score uses Google\'s scale, not ours.',
      },
      {
        q: 'Which country does it search?',
        a: 'The one your site is for: from the domain (.co.nz, .com.au, .in and so on), or, for .com sites, the business\'s home market. The results page shows which country was searched.',
      },
    ],
  },
  {
    id: 'ai-visibility',
    title: 'AI visibility (GEO)',
    items: [
      {
        q: 'What is AI visibility (GEO)?',
        a: 'GEO checks whether AI search tools like ChatGPT search, Perplexity and Claude can read and quote your page: which AI bots your robots.txt allows, whether you have an llms.txt file, trust signals (E-E-A-T) and how quotable your content is.',
      },
      {
        q: 'Should I block AI bots?',
        a: 'Keep AI search bots allowed if you want to appear in AI answers. AI training bots (like GPTBot) are a separate choice: blocking them keeps your content out of model training without hiding you from AI search.',
      },
    ],
  },
  {
    id: 'privacy',
    title: 'Privacy and data',
    items: [
      {
        q: 'What do you store?',
        a: 'Page addresses and keywords you check (results are cached for up to 24 hours) and your IP address for up to 48 hours to count free scans. There are no accounts, no tracking cookies and no ads. The Privacy Policy lists every service that handles data for us.',
      },
      {
        q: 'Is my API key stored?',
        a: 'No. Keys you paste in are sent with your request, used for it, and never saved.',
      },
    ],
  },
]

// The homepage shows a short list and links to /faq for the rest
export const HOME_FAQ = [
  FAQ_GROUPS[0].items[0],
  FAQ_GROUPS[1].items[0],
  FAQ_GROUPS[2].items[0],
  FAQ_GROUPS[3].items[0],
  FAQ_GROUPS[4].items[0],
  FAQ_GROUPS[1].items[3],
]
