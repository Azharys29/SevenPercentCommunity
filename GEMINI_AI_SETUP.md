# Gemini AI integration — setup

## What is deployed
- Frontend settings: `ai-settings.html`
- Shared UI/cache: `ai-assistant.js`
- Supabase Edge Function: `spc-gemini-analysis`
- Default behaviour: all menus remain in Existing mode until individually enabled in AI Integration Settings.
- Automatic analysis runs only for opted-in menus. The browser cache reuses results when the page snapshot is unchanged.

## Required one-time setup
1. Create a Gemini API key in Google AI Studio: https://aistudio.google.com/apikey
2. Open Supabase Dashboard for project `njghchwtcyoieymkodzj`.
3. Go to Edge Functions → Secrets and add `GEMINI_API_KEY` with the API key value. Never commit the key to GitHub or paste it into frontend code.
4. Optional: add `GEMINI_MODEL` with value `gemini-2.5-flash`. This is the default if omitted.
5. The AI endpoint requires a valid Supabase Auth user session. Sign in through the existing Supabase-authenticated flow before requesting AI. If a public page has no session, AI remains unavailable and the existing analysis still works.
6. Open https://azharys29.github.io/SevenPercentCommunity/ai-settings.html, enable only the menus you want to use, and leave the rest unchecked.

## Security and limitations
- The Gemini key is read only by the Edge Function environment; it is not stored in this repository.
- The endpoint restricts browser Origin to the GitHub Pages site, validates the bearer token with Supabase Auth, restricts the menu allowlist, limits input size, and applies a best-effort per-instance rate limit of 8 requests per 10 minutes per user.
- The in-memory rate limit is best-effort across serverless instances, not a global quota system.
- Results are cached in the user's browser local storage; clearing browser storage clears this cache.
- Gemini interprets the visible page snapshot only. It does not independently fetch current news or validate live market data.
- Gemini free-tier limits and model availability can change. When quota/backend is unavailable, use the existing non-AI tools.
