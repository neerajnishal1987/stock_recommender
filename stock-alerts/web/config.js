// StockAlerts — Supabase config for static hosting (Vercel/Netlify/GitHub Pages).
// When served via the local Flask server (localhost), this is ignored and the
// local /api/* proxy is used instead.
//
// IMPORTANT: the anon key is safe to expose in the browser (read-only via RLS).
// The service_role key must NEVER be put here — it stays in the backend/.env only.
const STOCKALERTS_SUPABASE_URL = "https://mrzweniyoaajgdgzxhsg.supabase.co";
const STOCKALERTS_SUPABASE_ANON_KEY = "sb_publishable_MKLfo0mGJswMYZpzeTsl_A_Mw0Z7E6i";