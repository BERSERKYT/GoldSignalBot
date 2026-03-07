# 🚀 GoldSignalBot Deployment Guide

Follow these steps to move your trading bot and dashboard from your local machine to the cloud.

---

## 1. Frontend: Dashboard (Vercel)

1. **Push your code to GitHub**: Create a repository and push your `GoldSignalBot` folder.
2. **Connect to Vercel**: 
   - Go to [vercel.com](https://vercel.com) and import your repository.
   - Select the `dashboard` folder as the **Root Directory**.
3. **Configure Framework**: Vercel should auto-detect **Vite**.
4. **Environment Variables**: Add these in the "Environment Variables" section of your Vercel project:
   - `VITE_SUPABASE_URL`: Your Supabase Project URL.
   - `VITE_SUPABASE_ANON_KEY`: Your Supabase Anon Key.
5. **Deploy**: Click "Deploy". Your dashboard is now live!

---

## 2. Backend: Trading Bot (Railway.app)

Railway is recommended for its "Background Worker" support which is perfect for Python bots.

1. **Create a New Project**: On [railway.app](https://railway.app), click "New Project" -> "Deploy from GitHub".
2. **Settings**:
   - Railway will detect the `requirements.txt` and install dependencies.
   - **Start Command**: `python main.py`
3. **Environment Variables**: Add these in Railway's "Variables" tab:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `FINNHUB_KEY`
   - `TIMEFRAME`: (e.g., `4h`)
   - `SCAN_INTERVAL_MINS`: (e.g., `60`)
4. **Deploy**: Railway will build and start your bot 24/7.

---

## 3. Alternative Backend: VPS (DigitalOcean/Linode)

If you prefer a standard server:

1. **Connect via SSH**.
2. **Clone the Repo**: `git clone <your-repo-url>`
3. **Setup Python**: `pip install -r requirements.txt`
4. **Configure Env**: Create a `.env` file with your credentials.
5. **Run in Background**: Use `pm2` or `nohup`:
   ```bash
   nohup python main.py &
   ```

---

## ✅ Post-Deployment Checklist
- [ ] Dashboard is accessible via `.vercel.app` URL.
- [ ] Active signals update in real-time on the live site.
- [ ] Bot logs (in Railway/VPS) show successful scan cycles.
