# Nix `''` Heredoc Indentation Stripping

When you embed a script in Nix via `writeTextFile { text = '' ... ''; }` or any other `''`-string heredoc, **Nix strips the minimum indentation across the entire heredoc body from every line**, including blank lines. If your new code adds a line indented one space deeper than the rest, every existing line comes out one space short of what you intended.

## Symptom

The script runs fine from the file you edited, but after `nixos-rebuild switch` the deployed copy in `/nix/store/<hash>/bin/<script>` fails with `IndentationError: unindent does not match any outer indentation level`. The systemd unit restarts the service in a tight loop until you notice.

## Example

`flake/modules/adguard-netbird-appliance.nix` embedded the roku-bridge Python. The original had all `def` lines at 6 spaces of indent and all body lines at 10/14 spaces. Adding one extra space to two functions (`ha_to_plist` and `commanded_state`) shifted the minimum indentation of the heredoc from 6 to 7. Nix then stripped 7 from every line, leaving `def clamp` and `def encrypt_characteristics` correctly at column 0 but `def ha_to_plist` at column 1. Python saw a stray-indent function header and refused to load the module. The bridge died, all three bedroom bulbs stopped responding, and the only symptom in HA was the optimistic UI continuing to lie.

## How to avoid

- Keep every line in the heredoc indented at the same minimum. Match the existing style of the file; do not introduce a "nicer" indent level inside one function block.
- `nixfmt` does not check heredoc body indentation, only the Nix expression around it. The bug only surfaces after a rebuild.
- If you genuinely need a line with less indentation than the rest (rare; usually a top-level docstring or a non-Python block), prefix it with `''$` to opt out of stripping, or escape the leading whitespace explicitly with `\` continuations.

## Quick verification before committing

After editing a Nix-embedded script, before committing:

```bash
# 1. nixfmt catches the Nix expression around the heredoc, not the body.
nixfmt --check flake/modules/<module>.nix

# 2. Read the heredoc with explicit whitespace markers; every non-blank line
#    should share the same minimum indent.
awk '/text = '\''/,/'\'';$/' flake/modules/<module>.nix | cat -A

# 3. After deploy, the runtime check that would have caught it:
ssh <host> "sudo journalctl -u <service> -n 20 --since '1 minute ago'"
```

A 30-second `cat -A` of the heredoc catches the bug every time. The runtime check (`journalctl`) is too late: by then you've already broken production and shipped an outage.

## Past incidents

- 2026-09-12, `12b321a`: Roku-bridge crashed for ~30 minutes after a Nix-side indentation slip. Bridge ran a hot-patched `/var/lib/roku-bridge/bridge.py` via a runtime systemd drop-in while the closure was rebuilt. See `docs/runbooks/roku-bridge-architecture.md` for the deploy path.
