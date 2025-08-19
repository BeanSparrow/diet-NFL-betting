# Heroku Deployment Guide

This guide walks you through deploying the Diet NFL Betting Service to Heroku.

## Prerequisites

1. **Heroku Account**: Sign up at [heroku.com](https://heroku.com)
2. **Heroku CLI**: Install from [devcenter.heroku.com/articles/heroku-cli](https://devcenter.heroku.com/articles/heroku-cli)
3. **Git**: Make sure your project is in a git repository
4. **Discord Application**: Set up at [discord.com/developers/applications](https://discord.com/developers/applications)

## Step 1: Prepare Your Data Migration (Optional)

If you have existing data in your SQLite database, export it first:

```bash
python migrate_to_postgresql.py
```

This creates a `migration_data.sql` file with your existing data.

## Step 2: Create Heroku Application

```bash
# Login to Heroku
heroku login

# Create a new Heroku app (replace 'your-app-name' with desired name)
heroku create your-app-name

# Add PostgreSQL database
heroku addons:create heroku-postgresql:mini
```

## Step 3: Configure Environment Variables

Set the required environment variables on Heroku:

```bash
# Generate a strong secret key
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')

# Set Flask environment variables
heroku config:set SECRET_KEY="$SECRET_KEY"
heroku config:set FLASK_ENV=production

# Set Discord OAuth variables (get these from Discord Developer Portal)
heroku config:set DISCORD_CLIENT_ID=your_actual_discord_client_id
heroku config:set DISCORD_CLIENT_SECRET=your_actual_discord_client_secret
heroku config:set DISCORD_REDIRECT_URI=https://your-app-name.herokuapp.com/callback

# Optional: Set logging level
heroku config:set LOG_LEVEL=INFO
```

## Step 4: Update Discord Application Settings

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Select your application
3. Go to OAuth2 → General
4. Add redirect URI: `https://your-app-name.herokuapp.com/callback`
5. Save changes

## Step 5: Deploy to Heroku

```bash
# Make sure you're in the project directory and it's a git repo
git add .
git commit -m "Prepare for Heroku deployment"

# Deploy to Heroku
git push heroku main
```

The deployment will:
- Install dependencies from `requirements.txt`
- Run database migrations automatically (`flask db upgrade`)
- Start the web server with Gunicorn

## Step 6: Import Existing Data (If You Have Any)

If you exported data in Step 1:

```bash
# Connect to PostgreSQL and import data
heroku pg:psql < migration_data.sql
```

## Step 7: Verify Deployment

```bash
# Open your app in browser
heroku open

# Check logs if there are issues
heroku logs --tail

# Check database status
heroku pg:info
```

## Environment Variables Reference

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask secret key for sessions | ✅ Yes |
| `DATABASE_URL` | PostgreSQL connection URL | Auto-set by Heroku |
| `DISCORD_CLIENT_ID` | Discord OAuth client ID | ✅ Yes |
| `DISCORD_CLIENT_SECRET` | Discord OAuth client secret | ✅ Yes |
| `DISCORD_REDIRECT_URI` | OAuth callback URL | ✅ Yes |
| `FLASK_ENV` | Set to 'production' | ✅ Yes |
| `LOG_LEVEL` | Logging level (INFO, WARNING, ERROR) | Optional |

## Troubleshooting

### Common Issues

**1. Application Error (H10)**
- Check logs: `heroku logs --tail`
- Usually missing environment variables

**2. Database Connection Issues**
- Verify PostgreSQL add-on: `heroku addons`
- Check DATABASE_URL: `heroku config:get DATABASE_URL`

**3. Discord OAuth Not Working**
- Verify redirect URI matches exactly
- Check HTTPS is being used
- Confirm CLIENT_ID and CLIENT_SECRET are set

**4. Static Files Not Loading**
- Heroku serves static files automatically
- Check `app/static/` directory structure

### Useful Heroku Commands

```bash
# View logs
heroku logs --tail

# Run one-off commands
heroku run python migrate_to_postgresql.py

# Access database
heroku pg:psql

# Restart app
heroku restart

# Check dyno status
heroku ps

# Scale dynos
heroku ps:scale web=1
```

## Cost Estimation

**Heroku Free Tier (Deprecated - now requires payment):**
- Basic Dyno: ~$7/month
- PostgreSQL Mini: Free up to 10k rows

**Recommended Setup:**
- Basic Dyno: $7/month
- PostgreSQL Mini: Free (upgrade to Basic $9/month for backups)

**Total: $7-16/month** for a production-ready deployment.

## Security Notes

✅ **Implemented:**
- HTTPS enforced in production
- Secure session cookies
- Environment variable protection
- PostgreSQL with connection pooling

⚠️ **Additional Recommendations:**
- Regular security updates
- Monitor logs for suspicious activity
- Consider adding rate limiting for public APIs
- Regular database backups (included with paid PostgreSQL tiers)

## Next Steps After Deployment

1. **Test all functionality** on the live site
2. **Set up monitoring** with Heroku metrics
3. **Configure custom domain** (optional)
4. **Set up automated backups**
5. **Monitor performance** and scale as needed

## Support

If you encounter issues:
1. Check the logs: `heroku logs --tail`
2. Review Heroku documentation
3. Check Discord Developer Portal settings
4. Verify all environment variables are set correctly