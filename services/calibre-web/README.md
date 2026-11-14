# Calibre-Web

Web UI for a Calibre ebook library. Handles Send-to-Kindle over local WiFi
and reads ePub/PDF/mobi/azw3 from phones and browsers.

## Starting

```bash
pergamon services up calibre-web
```

Then: `http://<pergamon-ip>:8083/`

## First-time setup

1. Create (or copy in) a Calibre library at `build/services/calibre-web/books`.
   If you don't have one yet: install Calibre locally, create an empty library,
   copy its folder here.
2. Open the web UI. Default login is `admin / admin123` — change immediately.
3. Point the "Calibre Database Location" at `/books`.
4. Add your books via the UI, or drop `.epub`/`.mobi` files in `/books` and
   click "Add new" to import.

## Send-to-Kindle

Configure under Admin → Config → Feature → **Email server**. Use your
household's email relay (e.g., Gmail with an app password) and the Kindle's
`@kindle.com` address.

## Storage

Library + metadata DB live in `../../build/services/calibre-web/`. Big —
depends on the library. Back up alongside your Calibre metadata.
