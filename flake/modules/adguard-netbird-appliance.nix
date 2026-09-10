{ lib, pkgs, ... }:
let
  rokuBridgePython = pkgs.python3.withPackages (ps: [
    ps.pyyaml
    ps.paho-mqtt
    ps.pycryptodome
  ]);
  # Canonical source: roku-bulb-local/scripts/bridge.py. Keep in sync when it changes.
  rokuBridgeDaemon = pkgs.writeTextFile {
    name = "roku-bridge";
    executable = true;
    destination = "/bin/roku-bridge";
    text = ''
      import argparse
      import json
      import sys
      import time
      import urllib.request

      import yaml

      TEMP_MIN_K = 1800
      TEMP_MAX_K = 6500
      MIRED_MIN = round(1_000_000 / TEMP_MAX_K)
      MIRED_MAX = round(1_000_000 / TEMP_MIN_K)


      def clamp(v, lo, hi):
          return max(lo, min(hi, v))


      def ha_to_plist(cmd):
          plist = []
          state = (cmd.get("state") or "").upper()
          if state == "OFF":
              return [{"pid": "P3", "pvalue": "0"}]
          if state == "ON":
              plist.append({"pid": "P3", "pvalue": "1"})
          if "color_temp" in cmd and cmd["color_temp"] is not None:
              kelvin = round(1_000_000 / int(cmd["color_temp"]))
              plist.append({"pid": "P1502", "pvalue": str(clamp(kelvin, TEMP_MIN_K, TEMP_MAX_K))})
          elif cmd.get("rgb_color"):
              r, g, b = (clamp(int(x), 0, 255) for x in cmd["rgb_color"][:3])
              plist.append({"pid": "P1507", "pvalue": f"{r:02X}{g:02X}{b:02X}"})
          if "brightness" in cmd and cmd["brightness"] is not None:
              pct = clamp(round(int(cmd["brightness"]) * 100 / 255), 1, 100)
              plist.append({"pid": "P1501", "pvalue": str(pct)})
          return plist


      def encrypt_characteristics(enr, mac, plist):
          from Crypto.Cipher import AES
          from Crypto.Util.Padding import pad
          from base64 import b64encode

          inner = json.dumps(
              {"mac": mac, "index": "0", "ts": str(int(time.time() * 1000)), "plist": plist},
              separators=(",", ":"),
          )
          key = enr.encode("utf-8")
          return b64encode(AES.new(key, AES.MODE_CBC, key).encrypt(pad(inner.encode(), 16))).decode()


      def send_local(ip, mac, enr, plist):
          body = json.dumps(
              {
                  "request": "set_status",
                  "isSendQueue": 0,
                  "characteristics": encrypt_characteristics(enr, mac, plist),
              }
          ).encode()
          req = urllib.request.Request(
              f"http://{ip}:88/device_request", data=body, headers={"Content-Type": "application/json"}
          )
          with urllib.request.urlopen(req, timeout=5) as resp:
              resp.read()


      def discovery_payload(mac, name, prefix):
          slug = mac.replace(":", "").upper()
          return {
              "name": name,
              "unique_id": f"roku_{slug}",
              "object_id": f"roku_{slug.lower()}",
              "command_topic": f"{prefix}/light/{slug}/set",
              "state_topic": f"{prefix}/light/{slug}/state",
              "schema": "json",
              "optimistic": True,
              "brightness": True,
              "brightness_scale": 255,
              "color_temp": True,
              "min_mireds": MIRED_MIN,
              "max_mireds": MIRED_MAX,
              "rgb": True,
              "device": {"identifiers": [f"roku_{slug}"], "name": name, "model": "BC1000X", "manufacturer": "Roku"},
          }


      def run(config_path, prefix, mqtt_host, mqtt_port, user, password):
          import paho.mqtt.client as mqtt

          with open(config_path, encoding="utf-8") as f:
              bulbs = {b["mac"].replace(":", "").upper(): b for b in yaml.safe_load(f)["bulbs"]}

          client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
          if user:
              client.username_pw_set(user, password or None)

          def on_connect(c, _u, _f, rc, _p=None):
              for slug in bulbs:
                  c.subscribe(f"{prefix}/light/{slug}/set")
                  disc = discovery_payload(slug, bulbs[slug]["name"], prefix)
                  c.publish(f"homeassistant/light/roku_{slug}/config", json.dumps(disc), retain=True)
                  print(f"discovery + subscribe: {bulbs[slug]['name']} ({slug})", flush=True)

          def on_message(c, _u, msg):
              try:
                  slug = msg.topic.split("/")[-2].upper()
                  bulb = bulbs[slug]
                  cmd = json.loads(msg.payload.decode())
                  plist = ha_to_plist(cmd)
                  if not plist:
                      return
                  send_local(bulb["ip"], slug, bulb["enr"], plist)
                  state = {"state": (cmd.get("state") or "ON").upper()}
                  for k in ("brightness", "color_temp", "rgb_color"):
                      if cmd.get(k) is not None:
                          state[k] = cmd[k]
                  c.publish(f"{prefix}/light/{slug}/state", json.dumps(state), retain=True)
                  print(f"{slug} <- {plist}", flush=True)
              except Exception as e:
                  print(f"error on {msg.topic}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)

          client.on_connect = on_connect
          client.on_message = on_message
          client.connect(mqtt_host, mqtt_port, keepalive=30)
          client.loop_forever()
          return 0


      def main(argv=None):
          import os

          p = argparse.ArgumentParser()
          p.add_argument("--config", required=True)
          p.add_argument("--prefix", default="roku")
          p.add_argument("--mqtt-host", default=os.environ.get("MQTT_HOST", "127.0.0.1"))
          p.add_argument("--mqtt-port", type=int, default=int(os.environ.get("MQTT_PORT", "1883")))
          p.add_argument("--mqtt-user", default=os.environ.get("MQTT_USER", ""))
          p.add_argument("--mqtt-pass", default=os.environ.get("MQTT_PASS", ""))
          a = p.parse_args(argv)
          return run(a.config, a.prefix, a.mqtt_host, a.mqtt_port, a.mqtt_user, a.mqtt_pass)


      if __name__ == "__main__":
          sys.exit(main())
    '';
  };
in
{
  boot = {
    initrd.systemd.enable = true;
    loader = {
      efi.canTouchEfiVariables = true;
      systemd-boot.enable = true;
    };
  };

  hardware.enableRedistributableFirmware = true;
  time.timeZone = "America/Chicago";

  networking = {
    useDHCP = false;
    useNetworkd = true;
    nftables.enable = true;
    firewall = {
      enable = true;
      allowedUDPPorts = [ 51820 ];
      extraInputRules = ''
        ip saddr 10.0.10.0/24 tcp dport { 22, 3000 } accept
        ip saddr 10.0.10.0/24 tcp dport 53 accept
        ip saddr 10.0.10.0/24 udp dport 53 accept
        ip saddr 10.0.30.20 tcp dport 22 accept
        ip saddr 10.0.30.0/24 tcp dport 53 accept
        ip saddr 10.0.30.0/24 udp dport 53 accept
        ip saddr { 10.0.30.11, 10.0.30.12, 10.0.30.13 } tcp dport 1883 accept
        iifname "wt0" tcp dport { 22, 53, 3000 } accept
        iifname "wt0" udp dport 53 accept
      '';
    };
  };

  systemd.network = {
    enable = true;
    netdevs."20-netbird-vlan".netdevConfig = {
      Kind = "vlan";
      Name = "netbird-vlan";
    };
    netdevs."20-netbird-vlan".vlanConfig.Id = 60;
    networks = {
      "30-infrastructure" = {
        matchConfig.Name = "enp1s0";
        networkConfig = {
          Address = "10.0.30.10/24";
          DNS = "10.0.30.1";
          Gateway = "10.0.30.1";
          VLAN = "netbird-vlan";
        };
        linkConfig.RequiredForOnline = "routable";
      };
      "60-netbird-policy" = {
        matchConfig.Name = "netbird-vlan";
        networkConfig.Address = "10.0.60.2/24";
      };
    };
  };

  services.openssh = {
    enable = true;
    openFirewall = false;
    hostKeys = [
      {
        path = "/persist/etc/ssh/ssh_host_ed25519_key";
        type = "ed25519";
      }
      {
        bits = 4096;
        path = "/persist/etc/ssh/ssh_host_rsa_key";
        type = "rsa";
      }
    ];
    settings = {
      KbdInteractiveAuthentication = false;
      PasswordAuthentication = false;
      PermitRootLogin = "no";
    };
  };

  users = {
    mutableUsers = false;
    users.rupan = {
      isNormalUser = true;
      extraGroups = [
        "netbird"
        "wheel"
      ];
      openssh.authorizedKeys.keys = [
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILW7MVmIGzW4Eq1NJm4+gsGwQ+iL44bIfyAa/wdQ1srQ"
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFTXsL6q+O1d29vTd3TtK2F0MYPggS5KSHryvlIFBS1K"
        "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFWt07ttKX2X+E5CbwL4To1AuwuwuIaKWUePIrAwGrK0 homelab-nas-deploy"
      ];
    };
  };
  security.sudo.wheelNeedsPassword = false;

  services.adguardhome = {
    enable = true;
    host = "10.0.30.10";
    port = 3000;
    mutableSettings = false;
    settings = {
      users = [
        {
          name = "admin";
          password = "$2b$10$EY4fb1ANVYrI8ud2FQnJFOrnx5coVM3wwvZau1SOKoKNKdb9snryi";
        }
      ];
      dns = {
        bind_hosts = [ "10.0.30.10" ];
        port = 53;
        bootstrap_dns = [
          "9.9.9.9"
          "149.112.112.112"
        ];
        upstream_dns = [
          "[/homelab/]10.0.30.1"
          "https://dns.quad9.net/dns-query"
        ];
        fallback_dns = [ "1.1.1.1" ];
        protection_enabled = true;
      };
      dhcp.enabled = false;
      filtering = {
        enabled = true;
        filtering_enabled = true;
        filters_update_interval = 24;
        rewrites = [
          {
            domain = "registry.rupan.dev";
            answer = "10.0.30.20";
            enabled = true;
          }
        ];
      };
      filters = [
        {
          enabled = true;
          id = 1;
          name = "AdGuard DNS filter";
          url = "https://adguardteam.github.io/HostlistsRegistry/assets/filter_1.txt";
        }
        {
          enabled = true;
          id = 2;
          name = "OISD Big";
          url = "https://big.oisd.nl";
        }
        {
          enabled = true;
          id = 3;
          name = "AdGuard Mobile Ads filter";
          url = "https://adguardteam.github.io/HostlistsRegistry/assets/filter_11.txt";
        }
      ];
    };
  };

  services.netbird = {
    useRoutingFeatures = "server";
    clients.default = {
      port = 51820;
      name = "netbird";
      interface = "wt0";
      hardened = true;
      autoStart = true;
      login.enable = false;
    };
  };

  services.mosquitto = {
    enable = true;
    listeners = [
      {
        address = "10.0.30.10";
        port = 1883;
        users = {
          "home-assistant" = {
            passwordFile = "/persist/secrets/mosquitto-home-assistant-password";
            acl = [
              "readwrite homeassistant/#"
              "readwrite zigbee2mqtt/#"
              "readwrite roku/#"
            ];
          };
          zigbee2mqtt = {
            passwordFile = "/persist/secrets/mosquitto-zigbee2mqtt-password";
            acl = [
              "readwrite homeassistant/#"
              "readwrite zigbee2mqtt/#"
            ];
          };
          roku-bridge = {
            passwordFile = "/persist/secrets/mosquitto-roku-bridge-password";
            acl = [
              "readwrite homeassistant/#"
              "readwrite roku/#"
            ];
          };
        };
      }
    ];
  };

  services.zigbee2mqtt = {
    enable = true;
    settings = {
      version = 5;
      homeassistant.enabled = true;
      permit_join = false;
      mqtt = {
        server = "mqtt://10.0.30.10:1883";
        user = "!secret.yaml mqtt_user";
        password = "!secret.yaml mqtt_password";
      };
      serial = {
        adapter = "ember";
        port = "/dev/serial/by-id/usb-SONOFF_SONOFF_Dongle_Lite_MG21_048030cb64a2ef11b809926661ce3355-if00-port0";
      };
      advanced = {
        channel = 25;
        network_key = "!secret.yaml network_key";
      };
    };
  };

  systemd.services.mosquitto.unitConfig.ConditionPathExists = [
    "/persist/secrets/mosquitto-home-assistant-password"
    "/persist/secrets/mosquitto-zigbee2mqtt-password"
    "/persist/secrets/mosquitto-roku-bridge-password"
  ];

  systemd.services.zigbee2mqtt-secrets = {
    before = [ "zigbee2mqtt.service" ];
    requiredBy = [ "zigbee2mqtt.service" ];
    unitConfig.ConditionPathExists = "/persist/secrets/zigbee2mqtt-secret.yaml";
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      ${pkgs.coreutils}/bin/install -m 0600 -o zigbee2mqtt -g zigbee2mqtt \
        /persist/secrets/zigbee2mqtt-secret.yaml /var/lib/zigbee2mqtt/secret.yaml
    '';
  };

  users.users.roku-bridge = {
    isSystemUser = true;
    group = "roku-bridge";
    description = "Roku bulb MQTT bridge";
  };
  users.groups.roku-bridge = { };

  systemd.services.roku-bridge-secrets = {
    before = [ "roku-bridge.service" ];
    requiredBy = [ "roku-bridge.service" ];
    unitConfig.ConditionPathExists = [
      "/persist/secrets/roku-bridge-bulbs.yaml"
      "/persist/secrets/mosquitto-roku-bridge-password"
    ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
    };
    script = ''
      ${pkgs.coreutils}/bin/install -d -m 0700 -o roku-bridge -g roku-bridge /var/lib/roku-bridge
      ${pkgs.coreutils}/bin/install -m 0600 -o roku-bridge -g roku-bridge \
        /persist/secrets/roku-bridge-bulbs.yaml /var/lib/roku-bridge/bulbs.yaml
      {
        echo "MQTT_HOST=10.0.30.10"
        echo "MQTT_PORT=1883"
        echo "MQTT_USER=roku-bridge"
        ${pkgs.coreutils}/bin/printf 'MQTT_PASS='
        ${pkgs.coreutils}/bin/cat /persist/secrets/mosquitto-roku-bridge-password
      } > /var/lib/roku-bridge/mqtt.env
      ${pkgs.coreutils}/bin/chown roku-bridge:roku-bridge /var/lib/roku-bridge/mqtt.env
      ${pkgs.coreutils}/bin/chmod 0600 /var/lib/roku-bridge/mqtt.env
    '';
  };

  systemd.services.roku-bridge = {
    after = [
      "network-online.target"
      "mosquitto.service"
    ];
    wants = [ "network-online.target" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      User = "roku-bridge";
      EnvironmentFile = "/var/lib/roku-bridge/mqtt.env";
      ExecStart = "${rokuBridgePython}/bin/python3 -u ${rokuBridgeDaemon}/bin/roku-bridge --config /var/lib/roku-bridge/bulbs.yaml";
      Restart = "always";
      RestartSec = "5s";
      NoNewPrivileges = true;
      PrivateTmp = true;
    };
  };

  systemd.services = {
    adguardhome = {
      after = [ "network-online.target" ];
      wants = [ "network-online.target" ];
      serviceConfig.StateDirectoryMode = "0700";
    };
    netbird = {
      after = [ "network-online.target" ];
      wants = [ "network-online.target" ];
    };
  };

  systemd.tmpfiles.rules = [
    "d /var/lib/private 0700 root root -"
    "d /persist/etc/ssh 0700 root root -"
    "d /persist/secrets 0700 root root -"
    "d /persist/var/lib/private 0700 root root -"
    "d /persist/var/lib/private/AdGuardHome 0700 nobody nogroup -"
  ];

  environment.persistence."/persist" = {
    hideMounts = true;
    directories = [
      "/var/lib/netbird"
      "/var/lib/nixos"
      "/var/lib/zigbee2mqtt"
      "/var/lib/private/AdGuardHome"
      "/var/lib/systemd"
    ];
    files = [ "/etc/machine-id" ];
  };

  environment.systemPackages = with pkgs; [
    btrfs-progs
    cryptsetup
    curl
    ethtool
    tcpdump
  ];

  nix = {
    gc = {
      automatic = true;
      dates = "weekly";
      options = "--delete-older-than 30d";
    };
    settings = {
      auto-optimise-store = true;
      experimental-features = [
        "nix-command"
        "flakes"
      ];
      extra-substituters = [ "http://10.0.30.20:8080/homelab" ];
      extra-trusted-public-keys = [ "homelab:J+OVQOCG2sNT2KoVbWGPikoWcIbBanHnY2NOcMF3vwk=" ];
    };
  };

  zramSwap = {
    enable = true;
    memoryPercent = 25;
  };
}
