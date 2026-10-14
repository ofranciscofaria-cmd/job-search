Hey Claude, I'm in a hiring process at Coverflex for a Marketing & GTM Ops Specialist role, and the next step is a take-home case study (attached, Coverflex_Growth_Ops_Case_Study.docx). Read it first. Part 1 is building a small AI chatbot in n8n that answers prospects' questions about Coverflex using RAG on content scraped from coverflex.com. I want us to build that part together now. They say to spend about an hour and that they care more about how I think than about polish, so I want every decision to be mine and easy to explain on the call.

Context and constraints:
- You're connected to my n8n through the MCP, so you can create and edit the workflow directly. It's my personal n8n account, not my employer's.
- I don't have OpenAI or Anthropic API keys and I don't want to use any company accounts. I have a free Google Gemini API key, so use Gemini for anything that needs a model. Free tiers only, budget is €0.
- I'll create any accounts or keys we need myself; tell me exactly what to set up and with which settings.

How I'd like to work:
- Before each decision, ask me. Give me 2-3 options with the trade-offs in plain words and tell me which one you'd pick and why, then wait for my answer. Max 2-3 questions at a time.
- Go step by step, roughly: how we interpret the brief, which pages of coverflex.com to scrape and how, how to clean the content, how to chunk it, which embedding model, which vector database, how the chatbot retrieves and answers (prompt, memory, model), and how we test it.
- After each step, test that it works before moving on, and show me what came out (a sample of scraped text, a few chunks, retrieval results for a test question).
- Explain new concepts briefly when they come up. I know n8n, Clay and HubSpot well, but I haven't built a RAG system before.
- Add sticky notes in the workflow that explain each part and why we chose it, so Pedro can follow the logic.
- Keep a short decision log as we go (decision, options considered, why), so I can walk Pedro through it.

At the end I need:
- The workflow exported as .json.
- The public production chat URL, working, for Pedro to test.
- A set of 5-8 test questions in Portuguese and English with what a good answer looks like, including one the bot should NOT be able to answer (to show it doesn't invent things).
- A short list of what we'd improve if this went to production.

Start by reading the brief and asking me your first questions.
