# Radicale (CalDAV + CardDAV)

Family calendar and contacts, LAN-only.

## Starting

```bash
pergamon services up radicale
```

Then: `http://<pergamon-ip>:5232/`

## First-time auth setup

Radicale defaults to **anonymous** (no password). For a household you probably
want at least basic auth:

```bash
# On a machine with htpasswd available (brew install httpd on mac)
mkdir -p ~/github/pergamon/build/services/radicale/config
htpasswd -B -c ~/github/pergamon/build/services/radicale/config/users trenton
htpasswd -B    ~/github/pergamon/build/services/radicale/config/users partner
```

Then edit `build/services/radicale/config/config`:

```ini
[auth]
type = htpasswd
htpasswd_filename = /config/users
htpasswd_encryption = bcrypt
```

Restart: `pergamon services restart radicale`.

## Phone / client setup

- **iOS**: Settings → Accounts → Add → Other → Add CalDAV → server
  `<pergamon-ip>:5232`, user, pass. Same flow for CardDAV.
- **Android**: DAVx⁵ app → account URL same as above.
- **macOS**: System Settings → Internet Accounts → Add Other → CalDAV.

## Data

Everything lives in `../../build/services/radicale/data`. Back this up to
sneakernet media periodically — losing it means losing your calendars.
