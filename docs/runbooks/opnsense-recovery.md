# OPNsense Recovery

## Preconditions for a network change

- Verify the Wyse 5070 console is physically reachable.
- Run the GET-only inventory job and retain its encrypted `config.xml.age` artifact.
- Require `assignment_api_available: true` in the inventory artifact.
- Review the OpenTofu refresh-only and desired-state plans.
- Apply one coherent interface change set. Do not combine WAN, management, and every LAN change.

## Lost management connectivity

1. Attach a display and keyboard to the Wyse 5070.
2. Log in to the OPNsense console.
3. Use the console menu to assign interfaces or set the management-interface IPv4 address.
4. Confirm the management address responds locally before retrying remote access.
5. Restore the latest encrypted configuration export only when the intended configuration cannot be repaired from the console.

## Firmware recovery

At the console shell, inspect the installed version and firmware state:

```sh
opnsense-version
configctl firmware status
```

Do not start a second update while firmware reports a running or busy state.
