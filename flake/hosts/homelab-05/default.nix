{ pkgs, ... }:
{
  imports = [
    ./hardware-configuration.nix
    ../../modules/common-base.nix
    ../../modules/disko-single-disk.nix
    ../../modules/k3s-server.nix
    ../../modules/nvidia.nix
    ../../modules/kiosk.nix
  ];

  networking.hostName = "homelab-05";

  homelab.disk.device = "/dev/disk/by-id/nvme-KXG70ZNV1T02_NVMe_KIOXIA_1024GB_42MFC3FQFTC5";

  homelab.k3s = {
    enable = true;
    role = "agent";
    primaryInterface = "enp0s31f6";
    nodeIp = "10.0.30.15";
    serverAddress = "https://10.0.30.11:6443";
    tokenFile = "/persist/secrets/k3s-token";
  };

  services.k3s.extraFlags = [
    "--kubelet-arg=system-reserved=cpu=1,memory=2Gi"
    "--kubelet-arg=kube-reserved=cpu=500m,memory=1Gi"
  ];

  security.rtkit.enable = true;
  services.pipewire = {
    enable = true;
    alsa.enable = true;
    alsa.support32Bit = true;
    pulse.enable = true;
    wireplumber.extraConfig = {
      "10-device-priorities" = {
        "monitor.alsa.rules" = [
          # Always prioritize the HyperX QuadCast USB microphone as default input
          {
            matches = [
              { "node.name" = "~alsa_input.*usb-Kingston_HyperX_QuadCast_S.*"; }
              { "node.name" = "~alsa_input.*QuadCast.*"; }
            ];
            actions = {
              update-props = {
                "priority.driver" = 2500;
                "priority.session" = 2500;
              };
            };
          }
          # Deprioritize onboard PCI audio input
          {
            matches = [
              { "node.name" = "~alsa_input.pci.*"; }
            ];
            actions = {
              update-props = {
                "priority.driver" = 500;
                "priority.session" = 500;
              };
            };
          }
          # Prioritize HDMI soundbar outputs for speaker output
          {
            matches = [
              { "node.name" = "~alsa_output.pci-0000_01_00.1.*"; }
              { "node.name" = "~alsa_output.pci.*pro-output-3.*"; }
              { "node.name" = "~alsa_output.pci.*hdmi.*"; }
            ];
            actions = {
              update-props = {
                "priority.driver" = 2000;
                "priority.session" = 2000;
              };
            };
          }
          # Fallback onboard line-out audio
          {
            matches = [
              { "node.name" = "~alsa_output.pci-0000_00_1f.3.*"; }
            ];
            actions = {
              update-props = {
                "priority.driver" = 1000;
                "priority.session" = 1000;
              };
            };
          }
          # Deprioritize QuadCast headphone jack so output doesn't route to the mic
          {
            matches = [
              { "node.name" = "~alsa_output.*QuadCast.*"; }
            ];
            actions = {
              update-props = {
                "priority.driver" = 500;
                "priority.session" = 500;
              };
            };
          }
        ];
      };
    };
  };

  homelab.kiosk = {
    enable = true;
    url = "http://10.0.40.13:8123/local/jarvis/index.html?v=2026-09-18e";
    drmDevice = "/dev/dri/card1";
    scaleFactor = "1.0";
    disableOutputs = [ "HDMI-A-2" ];
  };

  networking.firewall.extraInputRules = ''
    ip saddr { 10.0.0.0/16, 10.42.0.0/16, 100.64.0.0/10 } tcp dport 6053 accept
    ip saddr { 10.0.0.0/16, 10.42.0.0/16, 100.64.0.0/10 } tcp dport { 8095, 8097, 38801 } accept
    ip saddr { 10.0.0.0/16, 10.42.0.0/16, 100.64.0.0/10 } udp dport 5353 accept
  '';

  boot.kernelParams = [ "video=HDMI-A-2:e" ];

  systemd.services.satellite-alsa-restore = {
    description = "Unmute onboard audio for Jarvis satellite";
    after = [ "sound.target" ];
    wantedBy = [ "multi-user.target" ];
    serviceConfig = {
      Type = "oneshot";
      RemainAfterExit = true;
      Restart = "on-failure";
      RestartSec = "10s";
    };
    path = [ pkgs.alsa-utils ];
    script = ''
      if [ -e /sys/class/drm/card1-HDMI-A-2/status ]; then
        echo on > /sys/class/drm/card1-HDMI-A-2/status || true
      fi
      amixer -c 0 set Master unmute 100%
      amixer -c 0 set Headphone unmute 100%
    '';
  };

  systemd.services.satellite-hdmi-audio-clock = {
    description = "Clock HDMI-A-2 for Jarvis soundbar audio";
    after = [ "cage-tty1.service" ];
    wantedBy = [ "cage-tty1.service" ];
    serviceConfig = {
      Type = "simple";
      User = "kiosk";
      Restart = "always";
      RestartSec = "5s";
    };
    environment = {
      XDG_RUNTIME_DIR = "/run/user/1001";
      WAYLAND_DISPLAY = "wayland-0";
    };
    path = [
      pkgs.wlr-randr
      pkgs.curl
    ];
    script = ''
      for i in $(seq 1 30); do
        curl -s --max-time 5 http://127.0.0.1:9222/json | grep -q '"title": "JARVIS"' && break
        sleep 2
      done
      curl -s --max-time 5 http://127.0.0.1:9222/json | grep -q '"title": "JARVIS"' || exit 1

      while true; do
        if wlr-randr 2>/dev/null | grep -A1 'HDMI-A-2' | grep -q 'Enabled: no'; then
          wlr-randr --output HDMI-A-2 --on --mode 1920x1080@60.000000 || true
        fi
        sleep 2
      done
    '';
  };
}
