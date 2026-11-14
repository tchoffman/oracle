# Identity

Each Pergamon user has a [Nostr](https://github.com/nostr-protocol/nips)
keypair. This is the **account** across every distributed app — classifieds,
social, direct messages, trade receipts, reputation. No passwords, no
server-side login.

## Mental model

- **Private key** (`nsec1...`) — the secret account ID. Signs events.
  Never share. Back it up to offline media.
- **Public key** (`npub1...`) — the identifier others see. Safe to post,
  tattoo on your member card, print on classifieds.
- **NIP-05 name** (`you@yourpergamon.local`) — human-readable handle
  that resolves to a public key via your Pergamon's web UI. Optional but
  useful for peer discovery.

Each Pergamon can hold **multiple identities** — a household typically has
one per adult. The "active" identity is used by default for CLI actions.

## Commands

```bash
pergamon identity list                         # all identities + which is active
pergamon identity create trenton                 # generate new keypair, mark active
pergamon identity create trenton --nip05 trenton@pergamon.local --display "Trenton"
pergamon identity use alice                    # switch active
pergamon identity show                         # active identity info; nsec hidden
pergamon identity show --reveal                # ALSO print the nsec (be careful)
pergamon identity export trenton                 # print nsec backup to stdout
pergamon identity export trenton --path backup.nsec   # or to a file (mode 0600)
pergamon identity import newname backup.nsec   # restore from backup
pergamon identity delete oldname               # prompts for confirmation
```

## Storage

Keys live in `build/identity/` (gitignored):

- `<name>.key`  — hex private key, file mode `0600`
- `<name>.json` — public metadata (npub, display name, nip05, created)
- `active`      — plain-text name of the currently active identity

The private-key files are **not passphrase-encrypted on disk**. The whole
machine is the trust boundary — same as every other thing in `build/`.
If you want keys encrypted at rest, use FileVault (macOS) / LUKS (Linux)
on the box, or keep the private keys on a separate removable drive.

## NIP-05 verification

Pergamon's web UI serves the standard NIP-05 endpoint:

```
GET http://<pergamon-host>:8090/.well-known/nostr.json?name=trenton
→ {"names": {"trenton": "<hex-pubkey>"}}
```

To use it in a Nostr client, set the NIP-05 field in your profile to
`trenton@yourhost.local` (match what you set on `--nip05`). The client
fetches the endpoint and verifies that the name maps to your pubkey.

For this to work over the public internet you'd need a real domain
pointing at your Pergamon. Over LAN or mesh, the `.local` form works as
long as peers can resolve the host (mDNS, `/etc/hosts`, or a mesh
directory — see the comms module).

## Rotating or recovering a key

**Lost your Pergamon machine.** If you backed up your nsec, you're fine:

```bash
pergamon identity import trenton ~/safe/trenton-backup.nsec
```

Same npub, same reputation, keeps working.

**No backup.** Your old identity is gone — nobody controls that key any
more. Generate a new one and publish a signed migration event from the
old key (if you still have access) or ask your peers to update their
contact lists manually.

**Suspected key compromise.** Rotate immediately: create a new identity,
announce the new npub over trusted channels, deprecate the old one.
NIP-26 delegation can help with this transition; not yet implemented
here.

## What's next (not built)

- NIP-26 delegation (so the host site can post on your behalf via a
  short-lived delegation key — foundation for paper-form on-ramps)
- Multi-device sync (same identity, several Pergamons)
- Key hierarchy for family units
- Encrypted-at-rest option (passphrase on the private-key file)
