# PostgreSQL Migration & Heroku Deployment Checklist

## Pre-Deployment Checklist ✅

### ✅ Application Ready for PostgreSQL
- [x] Added `psycopg2-binary==2.9.9` to requirements.txt
- [x] Config.py already supports PostgreSQL with DATABASE_URL
- [x] Production config includes postgres:// to postgresql:// fix
- [x] Connection pooling configured for PostgreSQL
- [x] SQLAlchemy models are PostgreSQL-compatible

### ✅ Heroku Configuration Files Created
- [x] `Procfile` - Defines web process and release command
- [x] `runtime.txt` - Specifies Python 3.12.7
- [x] `.env.example` - Template for environment variables
- [x] `HEROKU_DEPLOYMENT_GUIDE.md` - Complete deployment instructions
- [x] `.gitignore` - Prevents sensitive files from being committed

### ✅ Database Migration Tools
- [x] `migrate_to_postgresql.py` - Script to export SQLite data
- [x] Migration script handles data export and PostgreSQL import

### ✅ Security & Production Settings
- [x] Production config enforces HTTPS cookies
- [x] Environment variable validation in production mode
- [x] Secret key validation
- [x] Database URL validation (no SQLite in production)

## Deployment Steps

### 1. Data Migration (if you have existing data)
```bash
# Export current SQLite data
python migrate_to_postgresql.py
```

### 2. Create Heroku App
```bash
heroku login
heroku create your-app-name
heroku addons:create heroku-postgresql:mini
```

### 3. Set Environment Variables
```bash
# Generate secret key
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')

heroku config:set SECRET_KEY="$SECRET_KEY"
heroku config:set FLASK_ENV=production
heroku config:set DISCORD_CLIENT_ID=your_client_id
heroku config:set DISCORD_CLIENT_SECRET=your_client_secret
heroku config:set DISCORD_REDIRECT_URI=https://your-app-name.herokuapp.com/callback
```

### 4. Update Discord OAuth Settings
- Add production redirect URI to Discord Developer Portal
- Update OAuth URLs to use your Heroku app domain

### 5. Deploy
```bash
git add .
git commit -m "Deploy to Heroku with PostgreSQL"
git push heroku main
```

### 6. Import Data (if applicable)
```bash
heroku pg:psql < migration_data.sql
```

### 7. Verify Deployment
```bash
heroku open
heroku logs --tail
```

## What Changed for PostgreSQL

### Files Modified:
1. **requirements.txt** - Added psycopg2-binary
2. **config.py** - Already had PostgreSQL support

### Files Created:
1. **Procfile** - Heroku process definition
2. **runtime.txt** - Python version specification  
3. **.env.example** - Environment variable template
4. **migrate_to_postgresql.py** - Data migration script
5. **HEROKU_DEPLOYMENT_GUIDE.md** - Detailed deployment guide
6. **.gitignore** - Git ignore rules
7. **DEPLOYMENT_CHECKLIST.md** - This checklist

### Configuration Changes:
- Database URL now uses PostgreSQL instead of SQLite
- Production config validates PostgreSQL connection
- Connection pooling enabled for better performance
- Session settings optimized for production

## Environment Variables Required

| Variable | Purpose | Example |
|----------|---------|---------|
| `SECRET_KEY` | Flask session security | `generated-by-secrets-module` |
| `FLASK_ENV` | Environment mode | `production` |
| `DATABASE_URL` | PostgreSQL connection | Auto-set by Heroku |
| `DISCORD_CLIENT_ID` | OAuth authentication | From Discord Developer Portal |
| `DISCORD_CLIENT_SECRET` | OAuth authentication | From Discord Developer Portal |
| `DISCORD_REDIRECT_URI` | OAuth callback | `https://your-app.herokuapp.com/callback` |

## Cost Estimate

**Monthly Costs:**
- Heroku Basic Dyno: $7
- PostgreSQL Mini: Free (10k rows)
- **Total: $7/month**

For more data or backups:
- PostgreSQL Basic: $9/month (10M rows + backups)
- **Total: $16/month**

## Testing Strategy

1. **Local Testing**: Test with PostgreSQL locally first (optional)
2. **Staging**: Deploy to Heroku and test all features
3. **Data Migration**: Verify data imported correctly
4. **Discord OAuth**: Confirm authentication works with HTTPS
5. **Functionality**: Test betting, user management, ESPN integration

## Rollback Plan

If deployment fails:
1. Keep SQLite version running locally
2. Use `heroku releases:rollback` if needed  
3. Migration data is safely exported in `migration_data.sql`
4. Can redeploy with fixes

## Post-Deployment

- [ ] Test all features on live site
- [ ] Monitor logs for errors
- [ ] Set up regular database backups
- [ ] Consider custom domain setup
- [ ] Monitor performance metrics

✅ **Ready for Heroku Deployment!**