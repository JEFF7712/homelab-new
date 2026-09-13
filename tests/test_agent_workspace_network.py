from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from tests.test_agent_workspaces import enabled_workspace, test_manifest


class WorkspaceNetworkModuleTests(unittest.TestCase):
    def test_evaluated_policy_is_interface_bound_and_fail_closed(self) -> None:
        if shutil.which("nix") is None:
            self.skipTest("nix is unavailable")
        root = pathlib.Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            manifest = pathlib.Path(directory) / "workspaces.json"
            manifest.write_text(
                json.dumps(test_manifest([enabled_workspace()])),
                encoding="utf-8",
            )
            expression = f"""
              let
                f = builtins.getFlake {json.dumps(str(root / "flake"))};
                evaluated = f.inputs.nixpkgs.lib.nixosSystem {{
                  system = "x86_64-linux";
                  modules = [
                    {root / "flake/modules/agent-workspace-network.nix"}
                    {{
                      system.stateVersion = "26.05";
                      networking.hostName = "homelab-01";
                      networking.useNetworkd = true;
                      services.agent-workspace-network = {{
                        enable = true;
                        manifestFile = {manifest};
                      }};
                    }}
                  ];
                }};
              in {{
                rules = evaluated.config.networking.nftables.tables.agent-workspaces.content;
                bridge = evaluated.config.systemd.network.netdevs."40-rupan-dev".netdevConfig;
                address = evaluated.config.systemd.network.networks."40-rupan-dev".address;
                requires = evaluated.config.systemd.services.libvirtd.requires;
                preStop = evaluated.config.systemd.services.nftables.preStop;
              }}
            """
            result = subprocess.run(
                ["nix", "eval", "--impure", "--json", "--expr", expression],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        rules = value["rules"]
        self.assertEqual(value["bridge"], {"Kind": "bridge", "Name": "aw-rupan-br"})
        self.assertEqual(value["address"], ["192.0.2.1/30"])
        self.assertIn("nftables.service", value["requires"])
        self.assertIn("virsh destroy", value["preStop"])
        self.assertIn("agent-rupan-dev", value["preStop"])
        self.assertIn("ip link set dev", value["preStop"])
        self.assertIn("aw-rupan-tap", value["preStop"])
        self.assertLess(
            value["preStop"].index("ip link set dev"),
            value["preStop"].index("virsh destroy"),
        )
        self.assertIn('iifname "aw-rupan-br" ip saddr != 192.0.2.2 counter drop', rules)
        self.assertIn(
            'iifname "aw-rupan-br" ether saddr != 02:00:00:00:00:01 counter drop',
            rules,
        )
        self.assertIn('iifname "aw-rupan-br" ip6 saddr ::/0 counter drop', rules)
        self.assertIn("ip daddr 198.51.100.10 tcp dport 443", rules)
        self.assertIn("10.0.0.0/8", rules)
        self.assertIn('oifname "aw-rupan-br" counter drop', rules)
        self.assertIn("tcp dport { 22, 443 } ct state new accept", rules)
        mac_anti_spoof = rules.index(
            'iifname "aw-rupan-br" ether saddr != 02:00:00:00:00:01'
        )
        anti_spoof = rules.index('iifname "aw-rupan-br" ip saddr != 192.0.2.2')
        established = rules.index(
            'iifname "aw-rupan-br" ct state established,related accept'
        )
        new_egress = rules.index(
            'iifname "aw-rupan-br" oifname "eno1" ct state new accept'
        )
        self.assertLess(mac_anti_spoof, anti_spoof)
        self.assertLess(anti_spoof, established)
        self.assertLess(established, new_egress)
        self.assertLess(
            rules.index("ip daddr 198.51.100.10 tcp dport 443"),
            rules.index("ip daddr { 0.0.0.0/8"),
        )

    def test_storage_group_grants_qemu_traversal_without_libvirt_membership(
        self,
    ) -> None:
        if shutil.which("nix") is None:
            self.skipTest("nix is unavailable")
        root = pathlib.Path(__file__).resolve().parents[1]
        expression = f"""
          let
            f = builtins.getFlake {json.dumps(str(root / "flake"))};
            evaluated = f.inputs.nixpkgs.lib.nixosSystem {{
              system = "x86_64-linux";
              modules = [
                {root / "flake/modules/agent-workspaces.nix"}
                {{
                  system.stateVersion = "26.05";
                  services.agent-workspaces.enable = true;
                }}
              ];
            }};
          in {{
            groups = evaluated.config.users.users.qemu-libvirtd.extraGroups;
            tmpfiles = evaluated.config.systemd.tmpfiles.rules;
          }}
        """
        result = subprocess.run(
            ["nix", "eval", "--impure", "--json", "--expr", expression],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertIn("agent-workspace-storage", value["groups"])
        self.assertNotIn("libvirtd", value["groups"])
        self.assertIn(
            "d /persist/agent-workspaces 0710 root agent-workspace-storage - -",
            value["tmpfiles"],
        )


if __name__ == "__main__":
    unittest.main()
