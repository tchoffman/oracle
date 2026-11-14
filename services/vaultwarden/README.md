# Vaultwarden

Bitwarden-compatible password vault, LAN-only. Works with every standard
Bitwarden client (phone apps, browser extensions, CLI).

## Starting

```bash
# Generate an admin token first (one-time)
export VW_ADMIN_TOKEN="$(openssl rand -base64 48)"
echo "$VW_ADMIN_TOKEN"  # save this — it's the /admin password

pergamon services up vaultwarden
```

Then: `http://<pergamon-ip>:8089/`

## First-time setup

1. Hit `/admin` and paste the token — invite yourself + family members
   via email (or just create accounts by setting `SIGNUPS_ALLOWED=true`
   temporarily in the compose file, creating accounts, then flipping it
   back).
2. Point phone/browser Bitwarden clients at `http://<pergamon-ip>:8089`
   (Settings → Self-hosted server).
3. First login creates your vault.

## Important caveats

- **LAN only.** HTTPS is NOT configured — don't expose this to the internet
  without putting a reverse proxy in front. Over LAN this is fine; over the
  open internet, use `tailscale` or a proper TLS front.
- **Back it up.** Losing `build/services/vaultwarden/db.sqlite3` means losing
  every password. Snapshot regularly to offline media.

## Storage

Everything's in `../../build/services/vaultwarden/`. One SQLite file + a
few attachment folders.
